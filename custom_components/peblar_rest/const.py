"""Constants for the Peblar REST integration."""

import logging
from datetime import timedelta
from typing import Final

from ._peblar import ChargeLimiter, CPState

DOMAIN: Final = "peblar_rest"
DEFAULT_SCAN_INTERVAL: Final = 10
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300
VERSION_SCAN_INTERVAL: Final = timedelta(hours=2)
CONFIG_SCAN_INTERVAL: Final = timedelta(minutes=5)
LOGGER = logging.getLogger(__package__)

CHARGE_LIMITER_STATES = {
    ChargeLimiter.CHARGING_CABLE: "charging_cable",
    ChargeLimiter.CURRENT_LIMITER: "current_limiter",
    ChargeLimiter.DYNAMIC_LOAD_BALANCING: "dynamic_load_balancing",
    ChargeLimiter.EXTERNAL_POWER_LIMIT: "external_power_limit",
    ChargeLimiter.GROUP_LOAD_BALANCING: "group_load_balancing",
    ChargeLimiter.HARDWARE_LIMITATION: "hardware_limitation",
    ChargeLimiter.HIGH_TEMPERATURE: "high_temperature",
    ChargeLimiter.HOUSEHOLD_POWER_LIMIT: "household_power_limit",
    ChargeLimiter.INSTALLATION_LIMIT: "installation_limit",
    ChargeLimiter.INTERNAL_POWER_LIMIT: "internal_power_limit",
    ChargeLimiter.LOCAL_MODBUS_API: "local_modbus_api",
    ChargeLimiter.LOCAL_REST_API: "local_rest_api",
    ChargeLimiter.LOCAL_SCHEDULED_CHARGING: "local_scheduled_charging",
    ChargeLimiter.OCPP_SMART_CHARGING: "ocpp_smart_charging",
    ChargeLimiter.OVERCURRENT_PROTECTION: "overcurrent_protection",
    ChargeLimiter.PHASE_IMBALANCE: "phase_imbalance",
    ChargeLimiter.POWER_FACTOR: "power_factor",
    ChargeLimiter.RESERVED: "reserved",
    ChargeLimiter.SOLAR_CHARGING: "solar_charging",
}

CP_STATES = {
    CPState.CHARGING_SUSPENDED: "suspended",
    CPState.CHARGING_VENTILATION: "charging",
    CPState.CHARGING: "charging",
    CPState.ERROR: "error",
    CPState.FAULT: "fault",
    CPState.INVALID: "invalid",
    CPState.NO_EV_CONNECTED: "no_ev_connected",
    CPState.UNKNOWN: None,
}
