from __future__ import annotations

from . HA_Pusher import pusher as push
from . HA_Pusher import confirm_events

import voluptuous as vol
import orjson

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback, EventOrigin
from .functions import *
import requests

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
EVENT_CONFIRMER: confirm_events.EventConfirmer = confirm_events.EventConfirmer()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/update_app_session",
        vol.Optional("app_session_id"): str,
    }
)
@callback
def websocket_domika_update_app_session_id(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "update_app_session", data: {msg}')
    pusher = push.Pusher("")
    app_session_id = pusher.update_app_session_id(
        msg.get("app_session_id")
    )
    connection.send_result(
        msg.get("id"), {"app_session_id": app_session_id}
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/update_push_token",
        vol.Optional("app_session_id"): str,
        vol.Required("push_token_hex"): str,
        vol.Required("platform"): str,
        vol.Required("environment"): str,
    }
)
@callback
def websocket_domika_update_push_token(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "update_push_token", data: {msg}')
    pusher = push.Pusher("")
    app_session_id = msg.get("app_session_id")
    # This method involves http request. We need to assume it may take quite some time.
    # Do we need to make it async with callback somehow?
    res = pusher.update_push_notification_token(
        app_session_id,
        msg.get("push_token_hex"),
        msg.get("platform"),
        msg.get("environment")
    )
    connection.send_result(
        msg.get("id"), {"result": res}
    )
    pusher.close_connection()

    if res == 1:
        dict_attributes = {"push_activation_success": True}
    elif res == 2:
        dict_attributes = None
    elif res == 0:
        dict_attributes = {"push_activation_success": False}
    elif res == -1:
        dict_attributes = {"invalid_app_session_id": True}

    if dict_attributes:
        LOGGER.debug(f"""### domika_state_changed_{app_session_id}, {dict_attributes} """)
        hass.bus.async_fire(f"domika_state_changed_{app_session_id}", dict_attributes)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/remove_app_session",
        vol.Required("app_session_id"): str,
    }
)
@callback
def websocket_domika_delete_push_token(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "remove_app_session", data: {msg}')
    pusher = push.Pusher("")
    pusher.remove_app_session_id(
        msg.get("app_session_id")
    )
    connection.send_result(
        msg.get("id"), {}
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/update_push_session",
        vol.Required("original_transaction_id"): str,
        vol.Required("token"): str,
        vol.Required("platform"): str,
        vol.Required("environment"): str,
    }
)
@callback
def websocket_domika_update_push_session(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "update_push_session", data: {msg}')

    original_transaction_id = msg.get("original_transaction_id")
    token = msg.get("token")
    platform = msg.get("platform")
    environment = msg.get("environment")

    if original_transaction_id and token and platform and environment:
        r = requests.post('https://domika.app/update_push_session',
                          json={"original_transaction_id": original_transaction_id, "token": token, "platform": platform, "environment": environment})
        LOGGER.log_debug(f"update_push_session result: {r.text}, {r.status_code}")

        connection.send_result(
            msg.get("id"), {"result": 1, "text": "ok"}
        )
    else:
        connection.send_result(
            msg.get("id"), {"result": 0, "text": "one of the parameters is missing"}
        )



@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/verify_push_session",
        vol.Required("app_session_id"): str,
        vol.Required("verification_key"): str,
    }
)
@callback
def websocket_domika_verify_push_session(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "verify_push_session", data: {msg}')
    app_session_id = msg.get("app_session_id")
    verification_key = msg.get("verification_key")

    if app_session_id and verification_key:
        pusher = push.Pusher("")
        old_push_session_id = pusher.get_push_session(app_session_id)
        r = requests.post('https://domika.app/verify_push_session',
                          json={"verification_key": verification_key, "old_push_session_id": old_push_session_id})
        LOGGER.log_debug(f"verify_push_session result: {r.text}, {r.status_code}")
        push_session_id = r.text
        if push_session_id:
            pusher.save_push_session(app_session_id, push_session_id)
            connection.send_result( msg.get("id"), {"result": 1, "text": "ok"} )
        else:
            connection.send_result( msg.get("id"), {"result": 0, "text": "verification failed"} )
        pusher.close_connection()
    else:
        connection.send_result( msg.get("id"), {"result": 0, "text": "one of the parameters is missing"} )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/remove_push_session",
        vol.Required("app_session_id"): str,
    }
)
@callback
def websocket_domika_remove_push_session(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "remove_push_session", data: {msg}')
    app_session_id = msg.get("app_session_id")

    if app_session_id:
        pusher = push.Pusher("")
        push_session_id = pusher.get_push_session(app_session_id)
        pusher.save_push_session(app_session_id, "")
        pusher.close_connection()
        if push_session_id:
            r = requests.post('https://domika.app/remove_push_session',
                              json={"push_session_id": push_session_id})
            LOGGER.log_debug(f"remove_push_session result: {r.text}, {r.status_code}")
            connection.send_result( msg.get("id"), {"result": 1, "text": "ok"} )
        else:
            connection.send_result(msg.get("id"), {"result": 0, "text": f"push_session_id not found for app_session_id: {app_session_id}"})
    else:
        connection.send_result( msg.get("id"), {"result": 0, "text": "missing app_session_id"} )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/resubscribe",
        vol.Required("app_session_id"): str,
        vol.Required("subscriptions"): dict[str, set],
    }
)
@callback
def websocket_domika_resubscribe(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "resubscribe", data: {msg}')
    app_session_id = msg.get("app_session_id")

    res_list = []
    if app_session_id:
        for entity_id in msg.get("subscriptions"):
            state = hass.states.get(entity_id)
            if state:
                dict_attributes = {}
                state_bytes = orjson.dumps(state.as_compressed_state, default=json_encoder_domika, option=orjson.OPT_NON_STR_KEYS)
                compressed_state = orjson.loads(state_bytes)
                # LOGGER.debug(f"### state: {compressed_state}")
                make_dictionary(compressed_state, "", dict_attributes)
                [dict_attributes.pop(k, None) for k in ["c", "lc", "lu"]]
                time_updated = max(state.last_changed, state.last_updated)
                res_list.append({"entity_id": entity_id, "time_updated": time_updated, "attributes": dict_attributes})
            else:
                LOGGER.error(f"websocket_domika_resubscribe requesting state of unknown entity: {entity_id}")

    # LOGGER.debug(f"### websocket_domika_resubscribe: {app_session_id}, {res_list} ")

    connection.send_result(
        msg.get("id"), {"entities": res_list}
    )

    pusher = push.Pusher("")
    pusher.resubscribe(
        app_session_id,
        msg.get("subscriptions")
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/resubscribe_push",
        vol.Required("app_session_id"): str,
        vol.Required("subscriptions"): dict[str, set],
    }
)
@callback
def websocket_domika_resubscribe_push(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    LOGGER.debug(f'Got websocket message "resubscribe_push", data: {msg}')
    app_session_id = msg.get("app_session_id")

    connection.send_result(
        msg.get("id"), {}
    )

    pusher = push.Pusher("")
    pusher.resubscribe_push(
        app_session_id,
        msg.get("subscriptions")
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/confirm_event",
        vol.Required("app_session_id"): str,
        vol.Required("context_id"): str
    }
)
@callback
def websocket_domika_confirm_event(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "confirm_event", data: {msg}')
    EVENT_CONFIRMER.add_confirmation(msg.get("app_session_id"), msg.get("context_id"))
    connection.send_result(
        msg.get("id"), {}
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/critical_sensors"
    }
)
@callback
def websocket_domika_critical_sensors(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "critical_sensors", data: {msg}')
    pusher = push.Pusher("")
    sensors_data = get_critical_sensors(hass)
    connection.send_result(
        msg.get("id"), sensors_data
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/websocket_domika_save_dashboards",
        vol.Required("dashboards"): str,
    }
)
@callback
def websocket_domika_save_dashboards(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "save_dashboards", data: {msg}')
    pusher = push.Pusher("")
    sensors_data = pusher.save_dashboards(connection.user.id, msg.get("dashboards"))
    connection.send_result(
        msg.get("id"), {}
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/websocket_domika_get_dashboards",
    }
)
@callback
def websocket_domika_get_dashboards(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "get_dashboards", data: {msg}')
    pusher = push.Pusher("")
    dashboards = pusher.get_dashboards(connection.user.id)
    connection.send_result(
        msg.get("id"), dashboards
    )
    pusher.close_connection()