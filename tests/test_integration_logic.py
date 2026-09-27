"""Focused integration behavior tests."""

from __future__ import annotations

from types import SimpleNamespace

from peblar import PeblarSetUserConfiguration, SmartChargingMode

from custom_components.peblar_rest.const import (
    DEFAULT_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from custom_components.peblar_rest.select import _smart_charging_options


def test_custom_solar_is_available_for_firmware_110_configuration() -> None:
    """Expose Custom Solar only when its firmware fields are present."""
    config = SimpleNamespace(
        scheduled_charging_allowed=True,
        solar_charging_allowed=True,
        solar_charging_custom_power_target=0,
    )

    assert _smart_charging_options(config) == [
        "default",
        "fast_solar",
        "smart_solar",
        "pure_solar",
        "custom_solar",
        "scheduled",
    ]


def test_custom_solar_is_hidden_on_older_firmware() -> None:
    """Do not offer a mode unsupported by the charger."""
    config = SimpleNamespace(
        scheduled_charging_allowed=False,
        solar_charging_allowed=True,
        solar_charging_custom_power_target=None,
    )

    assert "custom_solar" not in _smart_charging_options(config)


def test_python_peblar_210_serializes_custom_solar_settings() -> None:
    """The pinned client must encode firmware 1.10 fields correctly."""
    payload = PeblarSetUserConfiguration(
        smart_charging=SmartChargingMode.CUSTOM_SOLAR,
        solar_charging_custom_power_target=-500,
        solar_charging_custom_power_threshold=1400,
        solar_charging_custom_always_charge=True,
    ).to_dict()

    assert payload["SolarChargingMode"] == "CustomSolar"
    assert payload["SolarChargingCustomPowerTarget"] == -500
    assert payload["SolarChargingCustomPowerThreshold"] == 1400
    assert payload["SolarChargingCustomAlwaysCharge"] is True


def test_polling_defaults_respect_documented_rate_limit() -> None:
    """Keep configurable polling at or below one cycle per five seconds."""
    assert MIN_SCAN_INTERVAL == 5
    assert MIN_SCAN_INTERVAL <= DEFAULT_SCAN_INTERVAL <= MAX_SCAN_INTERVAL
