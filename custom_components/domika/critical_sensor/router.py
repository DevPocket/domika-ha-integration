# vim: set fileencoding=utf-8
"""
Critical sensors.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import websocket_command
from homeassistant.core import HomeAssistant, callback

from ..const import MAIN_LOGGER_NAME
from .service import get

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


@websocket_command(
    {
        vol.Required('type'): 'domika/critical_sensors',
    },
)
@callback
def websocket_domika_critical_sensors(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
):
    """Handle domika critical sensors request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "critical_sensors", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "critical_sensors", data: %s', msg)
    sensors_data = get(hass)
    connection.send_result(msg_id, sensors_data.to_dict())
