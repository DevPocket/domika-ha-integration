"""Config flow for Domika integration."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    LOGGER
)

DOMIKA_SCHEMA = vol.Schema(
    {
    }
)


class DomikaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Domika."""

    VERSION = 0.1

    async def async_step_user(
            self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        return self.async_create_entry(title="Domika info", data={})

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class UnknownAuth(HomeAssistantError):
    """Error to indicate there is an uncaught auth error."""
