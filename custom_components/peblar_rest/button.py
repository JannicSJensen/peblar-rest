"""Buttons for Peblar REST."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from peblar import Peblar

from .coordinator import PeblarConfigEntry
from .entity import PeblarRestEntity
from .helpers import handle_peblar_errors

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PeblarButtonDescription(ButtonEntityDescription):
    """Describe a Peblar button."""

    press_fn: Callable[[Peblar], Awaitable[Any]]
    has_fn: Callable[[PeblarConfigEntry], bool] = lambda _: True


BUTTONS = (
    PeblarButtonDescription(
        key="identify",
        device_class=ButtonDeviceClass.IDENTIFY,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        press_fn=lambda peblar: peblar.identify(),
    ),
    PeblarButtonDescription(
        key="restart",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        press_fn=lambda peblar: peblar.reboot(),
    ),
    PeblarButtonDescription(
        key="socket_unlock",
        translation_key="socket_unlock",
        press_fn=lambda peblar: peblar.socket_unlock(),
        has_fn=lambda entry: entry.runtime_data.system_information.hardware_has_socket,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Peblar REST buttons."""
    async_add_entities(
        PeblarButton(entry, entry.runtime_data.configuration_coordinator, description)
        for description in BUTTONS
        if description.has_fn(entry)
    )


class PeblarButton(PeblarRestEntity, ButtonEntity):
    """Representation of a Peblar button."""

    entity_description: PeblarButtonDescription

    @handle_peblar_errors
    async def async_press(self) -> None:
        """Press the button."""
        await self.entity_description.press_fn(self.coordinator.peblar)
