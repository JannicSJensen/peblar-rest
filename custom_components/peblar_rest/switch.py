"""Switch controls for Peblar REST."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from peblar import PeblarSetUserConfiguration, PeblarUserConfiguration

from .coordinator import (
    PeblarConfigEntry,
    PeblarConfigurationCoordinator,
    PeblarData,
    PeblarDataUpdateCoordinator,
)
from .entity import PeblarRestEntity
from .helpers import handle_peblar_errors

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PeblarDataSwitchDescription(SwitchEntityDescription):
    """Describe a switch backed by the local REST API."""

    is_on_fn: Callable[[PeblarData], bool]
    set_fn: Callable[[PeblarDataUpdateCoordinator, bool], Awaitable[Any]]
    has_fn: Callable[[PeblarConfigEntry], bool] = lambda _: True


@dataclass(frozen=True, kw_only=True)
class PeblarConfigSwitchDescription(SwitchEntityDescription):
    """Describe a switch backed by charger configuration."""

    is_on_fn: Callable[[PeblarUserConfiguration], bool]
    set_fn: Callable[[PeblarConfigurationCoordinator, bool], Awaitable[Any]]
    has_fn: Callable[[PeblarConfigEntry], bool] = lambda _: True


async def _set_charge(coordinator: PeblarDataUpdateCoordinator, on: bool) -> Any:
    limit = coordinator.config_entry.runtime_data.last_charge_limit * 1000 if on else 0
    return await coordinator.api.ev_interface(charge_current_limit=limit)


async def _set_socket_lock(
    coordinator: PeblarConfigurationCoordinator, on: bool
) -> None:
    await coordinator.peblar.socket_lock(locked=on)


async def _set_custom_solar_always_charge(
    coordinator: PeblarConfigurationCoordinator, on: bool
) -> None:
    await coordinator.peblar.update_user_configuration(
        PeblarSetUserConfiguration(solar_charging_custom_always_charge=on)
    )


DATA_SWITCHES = (
    PeblarDataSwitchDescription(
        key="charge",
        translation_key="charge",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda data: data.ev.charge_current_limit >= 6000,
        set_fn=_set_charge,
    ),
    PeblarDataSwitchDescription(
        key="force_single_phase",
        translation_key="force_single_phase",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda data: data.ev.force_single_phase,
        set_fn=lambda coordinator, on: coordinator.api.ev_interface(
            force_single_phase=on
        ),
        has_fn=lambda entry: (
            entry.runtime_data.data_coordinator.data.system.force_single_phase_allowed
        ),
    ),
)

CONFIG_SWITCHES = (
    PeblarConfigSwitchDescription(
        key="socket_lock",
        translation_key="socket_lock",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda config: config.user_keep_socket_locked,
        set_fn=_set_socket_lock,
        has_fn=lambda entry: entry.runtime_data.system_information.hardware_has_socket,
    ),
    PeblarConfigSwitchDescription(
        key="custom_solar_always_charge",
        translation_key="custom_solar_always_charge",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda config: bool(config.solar_charging_custom_always_charge),
        set_fn=_set_custom_solar_always_charge,
        has_fn=lambda entry: (
            entry.runtime_data.configuration_coordinator.data.solar_charging_custom_always_charge
            is not None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Peblar REST switches."""
    async_add_entities(
        [
            *(
                PeblarDataSwitch(
                    entry, entry.runtime_data.data_coordinator, description
                )
                for description in DATA_SWITCHES
                if description.has_fn(entry)
            ),
            *(
                PeblarConfigSwitch(
                    entry,
                    entry.runtime_data.configuration_coordinator,
                    description,
                )
                for description in CONFIG_SWITCHES
                if description.has_fn(entry)
            ),
        ]
    )


class PeblarDataSwitch(PeblarRestEntity, SwitchEntity):
    """Switch backed by the local REST API."""

    entity_description: PeblarDataSwitchDescription

    @property
    def is_on(self) -> bool:
        """Return whether the switch is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)

    @handle_peblar_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self.entity_description.set_fn(self.coordinator, True)
        await self.coordinator.async_request_refresh()

    @handle_peblar_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self.entity_description.set_fn(self.coordinator, False)
        await self.coordinator.async_request_refresh()


class PeblarConfigSwitch(PeblarRestEntity, SwitchEntity):
    """Switch backed by charger configuration."""

    entity_description: PeblarConfigSwitchDescription

    @property
    def is_on(self) -> bool:
        """Return whether the switch is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)

    @handle_peblar_errors
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self.entity_description.set_fn(self.coordinator, True)
        await self.coordinator.async_request_refresh()

    @handle_peblar_errors
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self.entity_description.set_fn(self.coordinator, False)
        await self.coordinator.async_request_refresh()
