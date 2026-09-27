"""Select controls for Peblar REST."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from peblar import (
    LedBrightness,
    Peblar,
    PeblarUserConfiguration,
    SmartChargingMode,
    SoundVolume,
)

from .coordinator import PeblarConfigEntry
from .entity import PeblarRestEntity
from .helpers import handle_peblar_errors

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PeblarSelectDescription(SelectEntityDescription):
    """Describe a Peblar select."""

    current_fn: Callable[[PeblarUserConfiguration], str | None]
    select_fn: Callable[[Peblar, str], Awaitable[Any]]
    options_fn: Callable[[PeblarUserConfiguration], list[str]] | None = None
    has_fn: Callable[[PeblarConfigEntry], bool] = lambda _: True


def _smart_charging_options(config: PeblarUserConfiguration) -> list[str]:
    options = ["default"]
    if config.solar_charging_allowed:
        options.extend(["fast_solar", "smart_solar", "pure_solar"])
        if config.solar_charging_custom_power_target is not None:
            options.append("custom_solar")
    if config.scheduled_charging_allowed:
        options.append("scheduled")
    return options


SELECTS = (
    PeblarSelectDescription(
        key="smart_charging",
        translation_key="smart_charging",
        entity_category=EntityCategory.CONFIG,
        current_fn=lambda config: (
            config.smart_charging.value if config.smart_charging else None
        ),
        options_fn=_smart_charging_options,
        select_fn=lambda peblar, option: peblar.smart_charging(
            SmartChargingMode(option)
        ),
    ),
    PeblarSelectDescription(
        key="buzzer_volume",
        translation_key="buzzer_volume",
        entity_category=EntityCategory.CONFIG,
        options=["off", "low", "low_medium", "medium", "high"],
        current_fn=lambda config: config.buzzer_volume.name.lower(),
        select_fn=lambda peblar, option: peblar.set_buzzer_volume(
            volume=SoundVolume[option.upper()]
        ),
        has_fn=lambda entry: entry.runtime_data.system_information.hardware_has_buzzer,
    ),
    PeblarSelectDescription(
        key="led_brightness",
        translation_key="led_brightness",
        entity_category=EntityCategory.CONFIG,
        options=["automatic", "off", "dim", "medium", "bright"],
        current_fn=lambda config: (
            config.led_brightness.name.lower() if config.led_brightness else None
        ),
        select_fn=lambda peblar, option: peblar.set_led_brightness(
            brightness=LedBrightness[option.upper()]
        ),
        has_fn=lambda entry: entry.runtime_data.system_information.hardware_has_led,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PeblarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Peblar REST selects."""
    async_add_entities(
        PeblarSelect(entry, entry.runtime_data.configuration_coordinator, description)
        for description in SELECTS
        if description.has_fn(entry)
    )


class PeblarSelect(PeblarRestEntity, SelectEntity):
    """Representation of a Peblar select."""

    entity_description: PeblarSelectDescription

    @property
    def options(self) -> list[str]:
        """Return currently supported options."""
        if self.entity_description.options_fn:
            return self.entity_description.options_fn(self.coordinator.data)
        return list(self.entity_description.options or [])

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        return self.entity_description.current_fn(self.coordinator.data)

    @handle_peblar_errors
    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        await self.entity_description.select_fn(self.coordinator.peblar, option)
        await self.coordinator.async_request_refresh()
