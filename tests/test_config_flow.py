"""Config flow error-reporting and discovery tests."""

from __future__ import annotations

import asyncio
from ipaddress import ip_address
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD

from custom_components.peblar_rest import config_flow
from custom_components.peblar_rest._peblar import (
    PeblarAuthenticationError,
    PeblarConnectionError,
)


def _flow() -> config_flow.PeblarRestConfigFlow:
    flow = config_flow.PeblarRestConfigFlow()
    flow.hass = SimpleNamespace()
    flow.flow_id = "test"
    flow.handler = config_flow.DOMAIN
    flow.context = {"source": "zeroconf"}
    flow._discovery_info = SimpleNamespace(host="192.168.2.138")
    flow._discovered_host = "192.168.2.138"
    return flow


@pytest.mark.parametrize(
    ("error", "field", "key"),
    [
        (PeblarConnectionError("boom"), "base", "cannot_connect"),
        (PeblarAuthenticationError("bad"), CONF_PASSWORD, "invalid_auth"),
    ],
)
def test_discovery_confirm_shows_errors_on_visible_fields(error, field, key) -> None:
    """Password-only forms must not hide errors on a missing host field."""
    flow = _flow()
    with patch.object(config_flow, "_validate_input", AsyncMock(side_effect=error)):
        result = asyncio.run(
            flow.async_step_zeroconf_confirm({CONF_PASSWORD: "secret"})
        )
    assert result["step_id"] == "zeroconf_confirm"
    assert result["errors"] == {field: key}
    assert set(result["errors"]) <= {"base"} | {
        str(marker) for marker in result["data_schema"].schema
    }


def test_manual_form_keeps_connection_error_on_host() -> None:
    """The manual form has a host field, so the error belongs there."""
    errors: dict[str, str] = {}
    flow = _flow()
    with patch.object(
        config_flow,
        "_validate_input",
        AsyncMock(side_effect=PeblarConnectionError("boom")),
    ):
        asyncio.run(flow._async_validate({CONF_HOST: "h", CONF_PASSWORD: "p"}, errors))
    assert errors == {CONF_HOST: "cannot_connect"}


def test_discovery_prefers_ipv4_address() -> None:
    """An advertised IPv6 address must not be chosen over reachable IPv4."""
    info = SimpleNamespace(
        host="fd00::1234",
        ip_addresses=[
            ip_address("fd00::1234"),
            ip_address("169.254.1.2"),
            ip_address("192.168.2.138"),
        ],
    )
    assert config_flow._preferred_host(info) == "192.168.2.138"


def test_discovery_falls_back_to_reported_host() -> None:
    """Use Home Assistant's choice when no IPv4 address is advertised."""
    info = SimpleNamespace(host="fd00::1234", ip_addresses=[ip_address("fd00::1234")])
    assert config_flow._preferred_host(info) == "fd00::1234"
