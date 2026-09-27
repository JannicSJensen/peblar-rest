"""Binary sensors for Peblar REST."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PeblarConfigEntry, PeblarData
from .entity import PeblarRestEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PeblarBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Peblar binary sensor."""

    is_on_fn: Callable[[PeblarData], bool]
    has_fn: Callable[[PeblarConfigEntry], bool] = lambda _: True


BINARY_SENSORS = (
    PeblarBinarySensorDescription(
        key="active_errors",
        translation_key="active_errors",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.system.active_error_codes),
    ),
    PeblarBinarySensorDescription(
        key="active_warnings",
        translation_key="active_warnings",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(data.system.active_warning_codes),
    ),
    PeblarBinarySensorDescription(
        key="socket_lock",
        translation_key="socket_lock",
        device_class=BinarySensorDeviceClass.LOCK,
        has_fn=lambda entry: entry.runtime_data.system_information.hardware_has_socket,
        is_on_fn=lambda data: not bool(data.ev.lock_state),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Peblar REST binary sensors."""
    async_add_entities(
        PeblarBinarySensor(entry, entry.runtime_data.data_coordinator, description)
        for description in BINARY_SENSORS
        if description.has_fn(entry)
    )


class PeblarBinarySensor(PeblarRestEntity, BinarySensorEntity):
    """Representation of a Peblar REST binary sensor."""

    entity_description: PeblarBinarySensorDescription

    @property
    def is_on(self) -> bool:
        """Return the binary state."""
        return self.entity_description.is_on_fn(self.coordinator.data)
