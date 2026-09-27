"""Config flow for Peblar REST."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from aiohttp import CookieJar
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from peblar import (
    AccessMode,
    Peblar,
    PeblarAuthenticationError,
    PeblarConnectionError,
    PeblarError,
    PeblarUnsupportedFirmwareVersionError,
)

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


async def _validate_input(hass: Any, data: Mapping[str, Any]) -> str:
    """Validate credentials and return the charger serial number."""
    session = async_create_clientsession(
        hass,
        cookie_jar=CookieJar(unsafe=True),
    )
    peblar = Peblar(
        host=data[CONF_HOST],
        session=session,
    )
    await peblar.login(password=data[CONF_PASSWORD])
    info = await peblar.system_information()
    api = await peblar.rest_api(enable=True, access_mode=AccessMode.READ_WRITE)
    api.session = session
    await api.system()
    return info.product_serial_number


class PeblarRestConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Peblar REST config flow."""

    VERSION = 1
    _discovery_info: zeroconf.ZeroconfServiceInfo

    @staticmethod
    def async_get_options_flow(config_entry: Any) -> OptionsFlow:
        """Create the options flow."""
        return PeblarRestOptionsFlow()

    async def _async_validate(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ) -> str | None:
        try:
            return await _validate_input(self.hass, user_input)
        except PeblarAuthenticationError:
            errors[CONF_PASSWORD] = "invalid_auth"
        except PeblarConnectionError:
            errors[CONF_HOST] = "cannot_connect"
        except PeblarUnsupportedFirmwareVersionError:
            errors["base"] = "unsupported_firmware"
        except PeblarError:
            errors["base"] = "api_unavailable"
        except Exception:
            LOGGER.exception("Unexpected error validating a Peblar charger")
            errors["base"] = "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if serial := await self._async_validate(user_input, errors):
                await self.async_set_unique_id(serial, raise_on_progress=False)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: user_input[CONF_HOST]}
                )
                return self.async_create_entry(
                    title=f"Peblar {serial}", data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(user_input),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        serial = discovery_info.properties.get("sn")
        if not serial:
            return self.async_abort(reason="no_serial_number")
        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.host})
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered charger."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_HOST: self._discovery_info.host,
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            if await self._async_validate(data, errors):
                return self.async_create_entry(
                    title=f"Peblar {self.unique_id}", data=data
                )
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            description_placeholders={"host": self._discovery_info.host},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace an invalid password."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {
                CONF_HOST: entry.data[CONF_HOST],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            if await self._async_validate(data, errors):
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the charger host or password."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            if serial := await self._async_validate(user_input, errors):
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_mismatch(reason="different_device")
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_connection_schema(user_input or entry.data),
            errors=errors,
        )


class PeblarRestOptionsFlow(OptionsFlow):
    """Configure Peblar REST polling."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "scan_interval",
                        default=self.config_entry.options.get(
                            "scan_interval", DEFAULT_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )


def _connection_schema(data: Mapping[str, Any] | None) -> vol.Schema:
    """Build a connection form without ever pre-filling a password."""
    data = data or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=data.get(CONF_HOST, "")): TextSelector(
                TextSelectorConfig(autocomplete="off")
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
    )
