"""Diagnostics for Peblar REST."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import PeblarConfigEntry

TO_REDACT = {
    "host",
    "password",
    "BopHomeWizardAddress",
    "BopSourceParameters",
    "CustomerId",
    "CustomCustomerId",
    "EthMacAddr",
    "Hostname",
    "MainboardSn",
    "ProductSn",
    "SeccOcppUri",
    "SolarChargingSourceParameters",
    "UserDefinedHouseholdPowerLimitSourceParameters",
    "WlanApMacAddr",
    "WlanStaMacAddr",
    "bop_home_wizard_address",
    "bop_source_parameters",
    "customer_id",
    "custom_customer_id",
    "ethernet_mac_address",
    "hostname",
    "mainboard_serial_number",
    "product_serial_number",
    "secc_ocpp_uri",
    "solar_charging_source_parameters",
    "user_defined_household_power_limit_source_parameters",
    "wlan_ap_mac_address",
    "wlan_mac_address",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PeblarConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics."""
    runtime = entry.runtime_data
    data = {
        "config_entry": dict(entry.data),
        "system_information": runtime.system_information.to_dict(),
        "user_configuration": runtime.configuration_coordinator.data.to_dict(),
        "ev_interface": runtime.data_coordinator.data.ev.to_dict(),
        "meter": runtime.data_coordinator.data.meter.to_dict(),
        "system": runtime.data_coordinator.data.system.to_dict(),
        "versions": {
            "current": runtime.version_coordinator.data.current.to_dict(),
            "available": runtime.version_coordinator.data.available.to_dict(),
        },
    }
    return async_redact_data(data, TO_REDACT)
