"""Number controls for Peblar REST."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    RestoreNumber,
)
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ._peblar import PeblarSetUserConfiguration, PeblarUserConfiguration
from .coordinator import (
    PeblarConfigEntry,
    PeblarConfigurationCoordinator,
    PeblarDataUpdateCoordinator,
)
from .entity import PeblarRestEntity
from .helpers import handle_peblar_errors

PARALLEL_UPDATES = 1


async def _set_custom_solar_target(
    coordinator: PeblarConfigurationCoordinator, value: int
) -> None:
    await coordinator.peblar.update_user_configuration(
        PeblarSetUserConfiguration(solar_charging_custom_power_target=value)
    )


async def _set_custom_solar_threshold(
    coordinator: PeblarConfigurationCoordinator, value: int
) -> None:
    await coordinator.peblar.update_user_configuration(
        PeblarSetUserConfiguration(solar_charging_custom_power_threshold=value)
    )


@dataclass(frozen=True, kw_only=True)
class PeblarConfigNumberDescription(NumberEntityDescription):
    """Describe a number backed by user configuration."""

    value_fn: Callable[[PeblarUserConfiguration], int | None]
    set_fn: Callable[[PeblarConfigurationCoordinator, int], Awaitable[None]]
    has_fn: Callable[[PeblarUserConfiguration], bool]


CONFIG_NUMBERS = (
    PeblarConfigNumberDescription(
        key="custom_solar_power_target",
        translation_key="custom_solar_power_target",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-25000,
        native_max_value=25000,
        native_step=100,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda config: config.solar_charging_custom_power_target,
        set_fn=_set_custom_solar_target,
        has_fn=lambda config: config.solar_charging_custom_power_target is not None,
    ),
    PeblarConfigNumberDescription(
        key="custom_solar_power_threshold",
        translation_key="custom_solar_power_threshold",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=25000,
        native_step=100,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda config: config.solar_charging_custom_power_threshold,
        set_fn=_set_custom_solar_threshold,
        has_fn=lambda config: config.solar_charging_custom_power_threshold is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Peblar REST numbers."""
    async_add_entities(
        [
            PeblarChargeLimitNumber(entry, entry.runtime_data.data_coordinator),
            *(
                PeblarConfigNumber(
                    entry,
                    entry.runtime_data.configuration_coordinator,
                    description,
                )
                for description in CONFIG_NUMBERS
                if description.has_fn(entry.runtime_data.configuration_coordinator.data)
            ),
        ]
    )


class PeblarChargeLimitNumber(PeblarRestEntity, RestoreNumber):
    """Control the local REST API current limit."""

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 6
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_translation_key = "charge_current_limit"

    def __init__(
        self, entry: PeblarConfigEntry, coordinator: PeblarDataUpdateCoordinator
    ) -> None:
        """Initialize the control."""
        super().__init__(
            entry, coordinator, NumberEntityDescription(key="charge_current_limit")
        )
        config = entry.runtime_data.configuration_coordinator.data
        self._attr_native_max_value = min(
            entry.runtime_data.system_information.hardware_max_current,
            config.current_control_fixed_charge_current_limit,
        )

    @property
    def native_value(self) -> int:
        """Return the requested limit in amperes."""
        value = round(self.coordinator.data.ev.charge_current_limit / 1000)
        if value >= 6:
            self.coordinator.config_entry.runtime_data.last_charge_limit = value
        return max(value, self.coordinator.config_entry.runtime_data.last_charge_limit)

    async def async_added_to_hass(self) -> None:
        """Restore the last valid charge limit."""
        if (
            (last_state := await self.async_get_last_state())
            and (last_number_data := await self.async_get_last_number_data())
            and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
            and last_number_data.native_value
        ):
            self.coordinator.config_entry.runtime_data.last_charge_limit = int(
                last_number_data.native_value
            )
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Remember active limits without replacing them with the paused value."""
        value = round(self.coordinator.data.ev.charge_current_limit / 1000)
        if value >= 6:
            self._attr_native_value = value
            self.coordinator.config_entry.runtime_data.last_charge_limit = value
        elif self._attr_native_value is None:
            self._attr_native_value = (
                self.coordinator.config_entry.runtime_data.last_charge_limit
            )
        super()._handle_coordinator_update()

    @handle_peblar_errors
    async def async_set_native_value(self, value: float) -> None:
        """Set the charge limit."""
        amps = int(value)
        self.coordinator.config_entry.runtime_data.last_charge_limit = amps
        self._attr_native_value = amps
        if self.coordinator.data.ev.charge_current_limit >= 6000:
            await self.coordinator.api.ev_interface(charge_current_limit=amps * 1000)
            await self.coordinator.async_request_refresh()
        else:
            self.async_write_ha_state()


class PeblarConfigNumber(PeblarRestEntity, NumberEntity):
    """Control a numeric charger configuration setting."""

    entity_description: PeblarConfigNumberDescription

    @property
    def native_value(self) -> int | None:
        """Return the configured value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @handle_peblar_errors
    async def async_set_native_value(self, value: float) -> None:
        """Set the configured value."""
        await self.entity_description.set_fn(self.coordinator, int(value))
        await self.coordinator.async_request_refresh()
