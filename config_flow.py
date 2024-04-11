"""Config flow for Jester integration."""
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

JESTER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): str
    }
)


async def _validate_input(
        hass: HomeAssistant, data: Mapping[str, Any]
) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    token = data[CONF_TOKEN]

    LOGGER.debug(f">>> test: {token}")

    if not token:
        raise CannotConnect("Can't do anything! Help!")
    else:
        # Return info that you want to store in the config entry.
        return {CONF_TOKEN: token}



class JesterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jester."""

    VERSION = 0.1

    async def _async_validate_input(
            self, user_input: Mapping[str, Any]
    ) -> tuple[dict[str, str] | None, dict[str, str]]:
        """Validate form input."""
        errors = {}
        info = None

        try:
            info = await _validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        return info, errors

    async def async_step_user(
            self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            info, errors = await self._async_validate_input(user_input)
            if info:
                await self.async_set_unique_id(user_input[CONF_TOKEN])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Jester info", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=JESTER_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class UnknownAuth(HomeAssistantError):
    """Error to indicate there is an uncaught auth error."""
