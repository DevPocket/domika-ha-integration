"""Config flow for Domika integration."""

import voluptuous as vol
from typing import Any
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

DOMIKA_SCHEMA = vol.Schema({
})


class DomikaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Domika."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(self, _user_input: dict[str, str] | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        return self.async_create_entry(title=DOMAIN, data={})

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entity_selector = selector.selector(
            {
                "entity": {
                    "domain": "binary_sensor",
                    "multiple": True
                }
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        schema="smoke_select_all",
                        default=self.config_entry.options.get("smoke_select_all")
                    ): bool,
                    vol.Optional(
                        schema="moisture_select_all",
                        default=self.config_entry.options.get("moisture_select_all")
                    ): bool,
                    vol.Optional(
                        schema="co_select_all",
                        default=self.config_entry.options.get("co_select_all")
                    ): bool,
                    vol.Optional(
                        schema="gas_select_all",
                        default=self.config_entry.options.get("gas_select_all")
                    ): bool,
                    # vol.Optional("moisture_select_all", default=False): bool,
                    # vol.Optional("co_select_all", default=False): bool,
                    # vol.Optional("gas_select_all", default=False): bool,
                    vol.Optional(
                        schema="critical_included_entity_ids",
                        default=self.config_entry.options.get("critical_included_entity_ids")
                    ): entity_selector,
                }
            ),
        )