"""Sensors for Peblar REST."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import CHARGE_LIMITER_STATES, CP_STATES
from .coordinator import PeblarConfigEntry, PeblarData
from .entity import PeblarRestEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PeblarSensorDescription(SensorEntityDescription):
    """Describe a Peblar sensor."""

    value_fn: Callable[[PeblarData], Any]
    has_fn: Callable[[PeblarConfigEntry], bool] = lambda _: True


SENSORS: tuple[PeblarSensorDescription, ...] = (
    PeblarSensorDescription(
        key="cp_state",
        translation_key="cp_state",
        device_class=SensorDeviceClass.ENUM,
        options=[state for state in CP_STATES.values() if state is not None],
        value_fn=lambda data: CP_STATES[data.ev.cp_state],
    ),
    PeblarSensorDescription(
        key="charge_current_limit_source",
        translation_key="charge_current_limit_source",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=list(CHARGE_LIMITER_STATES.values()),
        value_fn=lambda data: CHARGE_LIMITER_STATES[
            data.ev.charge_current_limit_source
        ],
    ),
    PeblarSensorDescription(
        key="charge_current_limit_actual",
        translation_key="charge_current_limit_actual",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.ev.charge_current_limit_actual,
    ),
    PeblarSensorDescription(
        key="energy_session",
        translation_key="energy_session",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.meter.energy_session,
    ),
    PeblarSensorDescription(
        key="energy_total",
        translation_key="energy_total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.meter.energy_total,
    ),
    PeblarSensorDescription(
        key="power_total",
        translation_key="power_total",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.meter.power_total,
    ),
    *tuple(
        PeblarSensorDescription(
            key=f"current_phase_{phase}",
            translation_key=f"current_phase_{phase}",
            device_class=SensorDeviceClass.CURRENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
            suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            suggested_display_precision=1,
            state_class=SensorStateClass.MEASUREMENT,
            has_fn=lambda entry, phase=phase: (
                entry.runtime_data.configuration_coordinator.data.connected_phases
                >= phase
            ),
            value_fn=lambda data, phase=phase: getattr(
                data.meter, f"current_phase_{phase}"
            ),
        )
        for phase in range(1, 4)
    ),
    *tuple(
        PeblarSensorDescription(
            key=f"power_phase_{phase}",
            translation_key=f"power_phase_{phase}",
            device_class=SensorDeviceClass.POWER,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            has_fn=lambda entry, phase=phase: (
                entry.runtime_data.configuration_coordinator.data.connected_phases
                >= phase
            ),
            value_fn=lambda data, phase=phase: getattr(
                data.meter, f"power_phase_{phase}"
            ),
        )
        for phase in range(1, 4)
    ),
    *tuple(
        PeblarSensorDescription(
            key=f"voltage_phase_{phase}",
            translation_key=f"voltage_phase_{phase}",
            device_class=SensorDeviceClass.VOLTAGE,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            state_class=SensorStateClass.MEASUREMENT,
            has_fn=lambda entry, phase=phase: (
                entry.runtime_data.configuration_coordinator.data.connected_phases
                >= phase
            ),
            value_fn=lambda data, phase=phase: getattr(
                data.meter, f"voltage_phase_{phase}"
            ),
        )
        for phase in range(1, 4)
    ),
    PeblarSensorDescription(
        key="wlan_signal_strength",
        translation_key="wlan_signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        has_fn=lambda entry: (
            entry.runtime_data.data_coordinator.data.system.wlan_signal_strength
            is not None
        ),
        value_fn=lambda data: data.system.wlan_signal_strength,
    ),
    PeblarSensorDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: (
            utcnow().replace(microsecond=0) - timedelta(seconds=data.system.uptime)
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Peblar REST sensors."""
    async_add_entities(
        PeblarSensor(entry, entry.runtime_data.data_coordinator, description)
        for description in SENSORS
        if description.has_fn(entry)
    )


class PeblarSensor(PeblarRestEntity, SensorEntity):
    """Representation of a Peblar REST sensor."""

    entity_description: PeblarSensorDescription

    @property
    def native_value(self) -> datetime | int | str | None:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator.data)
