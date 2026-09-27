"""Helpers for Peblar REST entities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from ._peblar import PeblarAuthenticationError, PeblarConnectionError, PeblarError
from .const import DOMAIN


def handle_peblar_errors[FuncT: Callable[..., Awaitable[Any]]](
    func: FuncT,
) -> FuncT:
    """Translate client exceptions raised by entity actions."""

    @wraps(func)
    async def handler(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await func(self, *args, **kwargs)
        except PeblarAuthenticationError as err:
            self.hass.config_entries.async_schedule_reload(
                self.coordinator.config_entry.entry_id
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="authentication_error",
            ) from err
        except PeblarConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="communication_error",
                translation_placeholders={"error": str(err)},
            ) from err
        except PeblarError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err

    return handler  # type: ignore[return-value]
