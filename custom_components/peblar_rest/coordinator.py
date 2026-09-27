"""Data coordinators for Peblar REST."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ._peblar import (
    Peblar,
    PeblarApi,
    PeblarAuthenticationError,
    PeblarConnectionError,
    PeblarError,
    PeblarEVInterface,
    PeblarMeter,
    PeblarSystem,
    PeblarSystemInformation,
    PeblarUserConfiguration,
    PeblarVersions,
)
from .const import CONFIG_SCAN_INTERVAL, DOMAIN, LOGGER, VERSION_SCAN_INTERVAL


@dataclass(slots=True)
class PeblarData:
    """Frequently changing charger data."""

    ev: PeblarEVInterface
    meter: PeblarMeter
    system: PeblarSystem


@dataclass(slots=True)
class PeblarVersionData:
    """Installed and available charger packages."""

    current: PeblarVersions
    available: PeblarVersions


@dataclass(slots=True)
class PeblarRuntimeData:
    """Runtime data for a Peblar REST config entry."""

    peblar: Peblar
    api: PeblarApi
    system_information: PeblarSystemInformation
    data_coordinator: PeblarDataUpdateCoordinator
    configuration_coordinator: PeblarConfigurationCoordinator
    version_coordinator: PeblarVersionCoordinator
    last_charge_limit: int = 6


PeblarConfigEntry = ConfigEntry[PeblarRuntimeData]


class PeblarCoordinator(DataUpdateCoordinator[Any]):
    """Base coordinator with consistent client error translation."""

    async def _async_handle_update(self) -> Any:
        raise NotImplementedError

    async def _async_update_data(self) -> Any:
        try:
            return await self._async_handle_update()
        except PeblarAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="authentication_error",
            ) from err
        except PeblarConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="communication_error",
                translation_placeholders={"error": str(err)},
            ) from err
        except PeblarError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err


class PeblarDataUpdateCoordinator(PeblarCoordinator):
    """Poll the documented local REST resources."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PeblarConfigEntry,
        api: PeblarApi,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"Peblar REST {entry.title}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_handle_update(self) -> PeblarData:
        ev, meter, system = await asyncio.gather(
            self.api.ev_interface(),
            self.api.meter(),
            self.api.system(),
        )
        return PeblarData(ev=ev, meter=meter, system=system)


class PeblarConfigurationCoordinator(PeblarCoordinator):
    """Poll user configuration through the charger web API."""

    def __init__(
        self, hass: HomeAssistant, entry: PeblarConfigEntry, peblar: Peblar
    ) -> None:
        """Initialize the coordinator."""
        self.peblar = peblar
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"Peblar REST {entry.title} configuration",
            update_interval=CONFIG_SCAN_INTERVAL,
        )

    async def _async_handle_update(self) -> PeblarUserConfiguration:
        return await self.peblar.user_configuration()


class PeblarVersionCoordinator(PeblarCoordinator):
    """Poll installed and available package versions."""

    install_in_progress = False

    def __init__(
        self, hass: HomeAssistant, entry: PeblarConfigEntry, peblar: Peblar
    ) -> None:
        """Initialize the coordinator."""
        self.peblar = peblar
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"Peblar REST {entry.title} versions",
            update_interval=VERSION_SCAN_INTERVAL,
        )

    async def _async_handle_update(self) -> PeblarVersionData:
        current, available = await asyncio.gather(
            self.peblar.current_versions(),
            self.peblar.available_versions(),
        )
        return PeblarVersionData(current=current, available=available)
