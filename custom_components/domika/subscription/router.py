# vim: set fileencoding=utf-8
"""
Subscription data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
import uuid
from typing import Any, cast

import domika_ha_framework.database.core as database_core
import domika_ha_framework.subscription.flow as subscription_flow
import voluptuous as vol
from domika_ha_framework.errors import DomikaFrameworkBaseError
from domika_ha_framework.utils import flatten_json
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)


@websocket_command(
    {
        vol.Required("type"): "domika/resubscribe",
        vol.Required("app_session_id"): vol.Coerce(uuid.UUID),
        vol.Required("subscriptions"): dict[str, set],
    },
)
@async_response
async def websocket_domika_resubscribe(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika resubscribe request."""
    msg_id = cast(int, msg.get("id"))
    if not msg_id:
        LOGGER.error('Got websocket message "resubscribe", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "resubscribe", data: %s', msg)
    app_session_id = cast(uuid.UUID, msg.get("app_session_id"))

    res_list = []
    subscriptions = cast(dict[str, dict[str, int]], msg.get("subscriptions"))
    for entity_id in subscriptions:
        state = hass.states.get(entity_id)
        if state:
            time_updated = max(state.last_changed, state.last_updated)
            res_list.append(
                {
                    "entity_id": entity_id,
                    "time_updated": time_updated,
                    "attributes": flatten_json(
                        state.as_compressed_state,
                        exclude={"c", "lc", "lu"},
                    ),
                },
            )
        else:
            LOGGER.error(
                "websocket_domika_resubscribe requesting state of unknown entity: %s",
                entity_id,
            )
    connection.send_result(msg_id, {"entities": res_list})

    try:
        async with database_core.get_session() as session:
            await subscription_flow.resubscribe(session, app_session_id, subscriptions)
    except DomikaFrameworkBaseError as e:
        LOGGER.error('Can\'t resubscribe "%s". Framework error. %s', subscriptions, e)
    except Exception as e:
        LOGGER.exception('Can\'t resubscribe "%s". Unhandled error. %s', subscriptions, e)
