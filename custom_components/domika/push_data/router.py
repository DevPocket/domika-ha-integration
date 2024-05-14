# vim: set fileencoding=utf-8
"""
Push data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
import uuid
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant

from ..const import MAIN_LOGGER_NAME
from ..database.core import AsyncSessionFactory
from .service import delete

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


@websocket_command(
    {
        vol.Required('type'): 'domika/confirm_event',
        vol.Required('app_session_id'): str,
        vol.Required('event_ids'): [vol.Coerce(uuid.UUID)],
    },
)
@async_response
async def websocket_domika_confirm_events(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika confirm event request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "confirm_event", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "confirm_event", data: %s', msg)

    event_ids = cast(list[uuid.UUID], msg.get('event_ids'))
    app_session_id = msg.get('app_session_id')

    if event_ids and app_session_id:
        async with AsyncSessionFactory() as session:
            await delete(session, event_ids)

    connection.send_result(msg_id, {})
