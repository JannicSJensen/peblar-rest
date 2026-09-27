"""Home Assistant integration for Peblar chargers over local REST."""

from __future__ import annotations

import asyncio

from aiohttp import CookieJar
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from peblar import (
    AccessMode,
    Peblar,
    PeblarAuthenticationError,
    PeblarConnectionError,
    PeblarError,
    PeblarUnsupportedFirmwareVersionError,
)

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import (
    PeblarConfigEntry,
    PeblarConfigurationCoordinator,
    PeblarDataUpdateCoordinator,
    PeblarRuntimeData,
    PeblarVersionCoordinator,
)

PLATFORMS = (
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
)


async def async_setup_entry(hass: HomeAssistant, entry: PeblarConfigEntry) -> bool:
    """Set up a Peblar REST config entry."""
    session = async_create_clientsession(hass, cookie_jar=CookieJar(unsafe=True))
    peblar = Peblar(host=entry.data[CONF_HOST], session=session)

    try:
        await peblar.login(password=entry.data[CONF_PASSWORD])
        system_information = await peblar.system_information()
        api = await peblar.rest_api(enable=True, access_mode=AccessMode.READ_WRITE)
        api.session = session
    except PeblarAuthenticationError as err:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="authentication_error",
        ) from err
    except PeblarUnsupportedFirmwareVersionError as err:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="unsupported_firmware",
            translation_placeholders={"error": str(err)},
        ) from err
    except PeblarConnectionError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="communication_error",
            translation_placeholders={"error": str(err)},
        ) from err
    except PeblarError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="unknown_error",
            translation_placeholders={"error": str(err)},
        ) from err

    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    data_coordinator = PeblarDataUpdateCoordinator(hass, entry, api, scan_interval)
    configuration_coordinator = PeblarConfigurationCoordinator(hass, entry, peblar)
    version_coordinator = PeblarVersionCoordinator(hass, entry, peblar)

    await asyncio.gather(
        data_coordinator.async_config_entry_first_refresh(),
        configuration_coordinator.async_config_entry_first_refresh(),
        version_coordinator.async_config_entry_first_refresh(),
    )

    entry.runtime_data = PeblarRuntimeData(
        peblar=peblar,
        api=api,
        system_information=system_information,
        data_coordinator=data_coordinator,
        configuration_coordinator=configuration_coordinator,
        version_coordinator=version_coordinator,
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: PeblarConfigEntry) -> None:
    """Reload after options or connection settings change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PeblarConfigEntry) -> bool:
    """Unload a Peblar REST config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
