"""Config flow for Domika integration."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import *

DOMIKA_SCHEMA = vol.Schema(
    {
    }
)


class DomikaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Domika."""

    VERSION = 0.1

    # async def async_step_user(
    #         self, user_input: dict[str, str] | None = None
    # ) -> FlowResult:
    #     """Handle the initial step."""
    #     errors: dict[str, str] = {}
    #     return self.async_create_entry(title="Domika info", data={})


    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        return self.async_create_entry(title=DEFAULT_NAME, data={})

    # return self.async_show_form(step_id="user")
