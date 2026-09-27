"""Base entity for Peblar REST."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_HOST
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .coordinator import PeblarConfigEntry


class PeblarRestEntity(CoordinatorEntity[DataUpdateCoordinator[Any]]):
    """Common Peblar REST entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: PeblarConfigEntry,
        coordinator: DataUpdateCoordinator[Any],
        description: EntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        info = entry.runtime_data.system_information
        self._attr_unique_id = f"{info.product_serial_number}_{description.key}"
        connections = {
            (dr.CONNECTION_NETWORK_MAC, address)
            for address in (info.ethernet_mac_address, info.wlan_mac_address)
            if address
        }
        self._attr_device_info = DeviceInfo(
            configuration_url=f"http://{entry.data[CONF_HOST]}",
            connections=connections,
            identifiers={(DOMAIN, info.product_serial_number)},
            manufacturer=info.product_vendor_name,
            model=info.product_model_name,
            model_id=info.product_number,
            name=f"Peblar {info.product_serial_number}",
            serial_number=info.product_serial_number,
            sw_version=info.firmware_version,
        )
