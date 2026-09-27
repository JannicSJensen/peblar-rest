"""Update entities for Peblar REST."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from peblar import PackageType, PeblarConnectionError, PeblarError

from .const import DOMAIN, LOGGER
from .coordinator import PeblarConfigEntry, PeblarVersionData
from .entity import PeblarRestEntity
from .helpers import handle_peblar_errors

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PeblarUpdateDescription(UpdateEntityDescription):
    """Describe a Peblar package update."""

    package_type: PackageType
    installed_fn: Callable[[PeblarVersionData], str | None]
    latest_fn: Callable[[PeblarVersionData], str | None]


UPDATES = (
    PeblarUpdateDescription(
        key="firmware",
        device_class=UpdateDeviceClass.FIRMWARE,
        package_type=PackageType.FIRMWARE,
        installed_fn=lambda data: data.current.firmware,
        latest_fn=lambda data: data.available.firmware,
    ),
    PeblarUpdateDescription(
        key="customization",
        translation_key="customization",
        package_type=PackageType.CUSTOMIZATION,
        installed_fn=lambda data: data.current.customization,
        latest_fn=lambda data: data.available.customization,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Peblar REST updates."""
    async_add_entities(
        PeblarUpdate(entry, entry.runtime_data.version_coordinator, description)
        for description in UPDATES
        if description.latest_fn(entry.runtime_data.version_coordinator.data)
        is not None
    )


class PeblarUpdate(PeblarRestEntity, UpdateEntity):
    """Representation of a Peblar package update."""

    entity_description: PeblarUpdateDescription
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS
    )

    @property
    def installed_version(self) -> str | None:
        """Return the installed package version."""
        return self.entity_description.installed_fn(self.coordinator.data)

    @property
    def latest_version(self) -> str | None:
        """Return the available package version."""
        return self.entity_description.latest_fn(self.coordinator.data)

    @property
    def in_progress(self) -> bool:
        """Return whether this charger is installing a package."""
        return self.coordinator.install_in_progress

    @handle_peblar_errors
    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install the package offered by the charger."""
        if self.coordinator.install_in_progress:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="update_in_progress",
            )
        if self.entity_description.package_type is PackageType.FIRMWARE:
            data = PeblarVersionData(
                current=await self.coordinator.peblar.current_versions(),
                available=await self.coordinator.peblar.available_versions(
                    use_cache=False
                ),
            )
            self.coordinator.async_set_updated_data(data)
            if (
                data.available.customization is not None
                and data.available.customization != data.current.customization
            ):
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="customization_update_first",
                )
        await self.coordinator.peblar.update(
            package_type=self.entity_description.package_type
        )
        self.coordinator.install_in_progress = True
        self.coordinator.async_update_listeners()
        self.coordinator.config_entry.async_create_background_task(
            self.hass,
            self._async_refresh_after_reboot(),
            name=f"Watch {self.entity_id} update",
        )

    async def _async_refresh_after_reboot(self) -> None:
        """Wait for the charger to go offline and return after an update."""
        loop = asyncio.get_running_loop()
        start_deadline = loop.time() + 3 * 60 * 60
        deadline = start_deadline
        offline_since: float | None = None
        try:
            while loop.time() < deadline:
                await asyncio.sleep(10)
                try:
                    await self.coordinator.config_entry.runtime_data.api.system()
                except PeblarConnectionError:
                    if offline_since is None:
                        offline_since = loop.time()
                        deadline = offline_since + 10 * 60
                    continue
                except PeblarError:
                    LOGGER.exception("Update status check failed")
                    return

                if offline_since is None:
                    continue
                if loop.time() - offline_since < 30:
                    offline_since = None
                    deadline = start_deadline
                    continue

                await self.coordinator.async_request_refresh()
                return

            LOGGER.warning("Timed out waiting for Peblar charger update and reboot")
        finally:
            self.coordinator.install_in_progress = False
            self.coordinator.async_update_listeners()
