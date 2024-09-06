# vim: set fileencoding=utf-8
"""
Critical sensor.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
from typing import Any, Optional

import voluptuous as vol
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import websocket_command
from homeassistant.core import HomeAssistant, callback

from .enums import NotificationType
from .service import get

LOGGER = logging.getLogger(__name__)


@websocket_command(
    {
        vol.Required("type"): "domika/critical_sensors",
    },
)
@callback
def websocket_domika_critical_sensors(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
):
    """Handle domika critical sensors request."""
    msg_id: Optional[int] = msg.get("id")
    if msg_id is None:
        LOGGER.error('Got websocket message "critical_sensors", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "critical_sensors", data: %s', msg)

    sensors_data = get(hass, NotificationType.ANY)
    result = sensors_data.to_dict()

    connection.send_result(msg_id, result)
    LOGGER.debug("critical_sensors msg_id=%s data=%s", msg_id, result)
