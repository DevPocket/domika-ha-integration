from __future__ import annotations

from . HA_Pusher import pusher as push
from . HA_Pusher import confirm_events

import voluptuous as vol
import orjson

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback, EventOrigin
from .functions import *

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
EVENT_CONFIRMER: confirm_events.EventConfirmer = confirm_events.EventConfirmer()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "jester/update_push_token",
        vol.Optional("install_id"): str,
        vol.Required("push_token_hex"): str,
        vol.Required("platform"): str,
        vol.Required("environment"): str,
    }
)
@callback
def websocket_jester_update_push_token(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle jester request."""
    LOGGER.debug(f'Got websocket message "update_push_token", data: {msg}')
    pusher = push.Pusher("")
    install_id = pusher.update_push_notification_token(
        msg.get("install_id"),
        connection.user.id,
        msg.get("push_token_hex"),
        msg.get("platform"),
        msg.get("environment")
    )
    connection.send_result(
        msg.get("id"), {"install_id": install_id}
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "jester/delete_push_token",
        vol.Required("install_id"): str,
    }
)
@callback
def websocket_jester_delete_push_token(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle jester request."""
    LOGGER.debug(f'Got websocket message "delete_push_token", data: {msg}')
    pusher = push.Pusher("")
    pusher.remove_push_notification_token(
        msg.get("install_id")
    )
    connection.send_result(
        msg.get("id"), {}
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "jester/resubscribe",
        vol.Required("install_id"): str,
        vol.Required("subscriptions"): dict[str, set],
    }
)
@callback
def websocket_jester_resubscribe(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle jester request."""
    LOGGER.debug(f'Got websocket message "resubscribe", data: {msg}')
    install_id = msg.get("install_id")

    connection.send_result(
        msg.get("id"), {}
    )

    if install_id:
        for entity_id in msg.get("subscriptions"):
            state = hass.states.get(entity_id)
            state_bytes = orjson.dumps(state.as_compressed_state, default=json_encoder_jester, option=orjson.OPT_NON_STR_KEYS)
            compressed_state = orjson.loads(state_bytes)
            # LOGGER.debug(f"### state: {compressed_state}")
            dict_attributes = {}
            make_dictionary(compressed_state, "", dict_attributes)
            [dict_attributes.pop(k, None) for k in ["c", "lc", "lu"]]
            dict_attributes["entity_id"] = entity_id
            time_updated = max(state.last_changed, state.last_updated)
            # LOGGER.debug(f"""### websocket_jester_resubscribe {install_id}, {dict_attributes}, {EventOrigin.local}, {state.context}, {time_updated} """)
            hass.bus.async_fire(
                f"jester_state_changed_{install_id}",
                dict_attributes,
                EventOrigin.local,
                state.context,
                time_updated.timestamp()
            )

    pusher = push.Pusher("")
    pusher.resubscribe(
        install_id,
        msg.get("subscriptions")
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "jester/confirm_event",
        vol.Required("install_id"): str,
        vol.Required("context_id"): str
    }
)
@callback
def websocket_jester_confirm_event(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle jester request."""
    LOGGER.debug(f'Got websocket message "confirm_event", data: {msg}')
    EVENT_CONFIRMER.add_confirmation(msg.get("install_id"), msg.get("context_id"))
    connection.send_result(
        msg.get("id"), {}
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "jester/critical_sensors"
    }
)
@callback
def websocket_jester_critical_sensors(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle jester request."""
    LOGGER.debug(f'Got websocket message "critical_sensors", data: {msg}')
    pusher = push.Pusher("")
    sensors_data = get_critical_sensors(hass)
    connection.send_result(
        msg.get("id"), sensors_data
    )
    pusher.close_connection()
