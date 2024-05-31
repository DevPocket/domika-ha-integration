"""Config flow for Domika integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

DOMIKA_SCHEMA = vol.Schema({})


class DomikaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Domika."""

    VERSION = 0
    MINOR_VERSION = 1

    async def async_step_user(self, _user_input: dict[str, str] | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        return self.async_create_entry(title=DOMAIN, data={})
