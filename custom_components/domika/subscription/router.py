# vim: set fileencoding=utf-8
"""
Subscription data.

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
from ..utils import flatten_json
from .flow import resubscribe, resubscribe_push

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


@websocket_command(
    {
        vol.Required('type'): 'domika/resubscribe',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
        vol.Required('subscriptions'): dict[str, set],
    },
)
@async_response
async def websocket_domika_resubscribe(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika resubscribe request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "resubscribe", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "resubscribe", data: %s', msg)
    app_session_id = cast(uuid.UUID, msg.get('app_session_id'))

    res_list = []

    subscriptions = cast(dict[str, set], msg.get('subscriptions'))  # Required in command schema.
    for entity_id in subscriptions:
        state = hass.states.get(entity_id)
        if state:
            time_updated = max(state.last_changed, state.last_updated)
            res_list.append(
                {
                    'entity_id': entity_id,
                    'time_updated': time_updated,
                    'attributes': flatten_json(
                        state.as_compressed_state,
                        exclude={'c', 'lc', 'lu'},
                    ),
                },
            )
        else:
            LOGGER.error(
                'websocket_domika_resubscribe requesting state of unknown entity: %s',
                entity_id,
            )

    async with AsyncSessionFactory() as session:
        await resubscribe(session, app_session_id, subscriptions)

    connection.send_result(msg_id, {'entities': res_list})


@websocket_command(
    {
        vol.Required('type'): 'domika/resubscribe_push',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
        vol.Required('subscriptions'): dict[str, set],
    },
)
@async_response
async def websocket_domika_resubscribe_push(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika resubscribe push request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "resubscribe_push", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "resubscribe_push", data: %s', msg)

    app_session_id = cast(uuid.UUID, msg.get('app_session_id'))

    async with AsyncSessionFactory() as session:
        await resubscribe_push(
            session,
            app_session_id,
            cast(dict[str, set], msg.get('subscriptions')),
        )

    connection.send_result(msg_id, {})
