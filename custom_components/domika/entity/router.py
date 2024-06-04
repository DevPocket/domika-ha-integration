# vim: set fileencoding=utf-8
"""
Entity.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import websocket_command
from homeassistant.core import HomeAssistant, callback

from .service import get
from ..const import MAIN_LOGGER_NAME

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


@websocket_command(
    {
        vol.Required("type"): "domika/entity_list",
        vol.Required("domains"): list,
    }
)
@callback
def websocket_domika_entity_list(
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika entity_list request."""
    msg_id = msg.get("id")
    LOGGER.debug(f'Got websocket message "entity_list", data: %s', msg)

    domains_list = msg.get("domains")
    entities = get(hass, domains_list)
    result = entities.to_dict()

    connection.send_result(msg_id, result)
    LOGGER.debug('entity_list msg_id=%s data=%s', msg_id, result)
