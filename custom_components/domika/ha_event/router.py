# vim: set fileencoding=utf-8
"""
Homeassistant event.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
import uuid
from typing import Any, Optional, cast

import domika_ha_framework.database.core as database_core
import domika_ha_framework.push_data.service as push_data_service
import voluptuous as vol
from domika_ha_framework.errors import DomikaFrameworkBaseError
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)


@websocket_command(
    {
        vol.Required("type"): "domika/confirm_event",
        vol.Required("app_session_id"): vol.Coerce(uuid.UUID),
        vol.Required("event_ids"): [vol.Coerce(uuid.UUID)],
    },
)
@async_response
async def websocket_domika_confirm_events(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika confirm event request."""
    msg_id: Optional[int] = msg.get("id")
    if msg_id is None:
        LOGGER.error('Got websocket message "confirm_event", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "confirm_event", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {"result": "accepted"})
    LOGGER.debug("confirm_event msg_id=%s data=%s", msg_id, {"result": "accepted"})

    event_ids = cast(list[uuid.UUID], msg.get("event_ids"))
    app_session_id = msg.get("app_session_id")

    if event_ids and app_session_id:
        try:
            async with database_core.get_session() as session:
                await push_data_service.delete(session, event_ids, app_session_id)
        except DomikaFrameworkBaseError as e:
            LOGGER.error('Can\'t confirm events "%s". Framework error. %s', event_ids, e)
        except Exception as e:
            LOGGER.exception('Can\'t confirm events "%s". Unhandled error. %s', event_ids, e)
