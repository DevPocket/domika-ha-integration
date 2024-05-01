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
        vol.Required("type"): "domika/update_install_id",
        vol.Optional("install_id"): str,
    }
)
@callback
def websocket_domika_update_install_id(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "update_install_id", data: {msg}')
    pusher = push.Pusher("")
    install_id = pusher.update_install_id(
        msg.get("install_id"),
        connection.user.id,
    )
    connection.send_result(
        msg.get("id"), {"install_id": install_id}
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/update_push_token",
        vol.Optional("install_id"): str,
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
    install_id = msg.get("install_id")
    # This method involves http request. We need to assume it may take quite some time.
    # Do we need to make it async with callback somehow?
    res = pusher.update_push_notification_token(
        install_id,
        connection.user.id,
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
    else:
        dict_attributes = {"push_activation_success": False}
    LOGGER.debug(
        f"""### domika_state_changed_{install_id}, {dict_attributes} """)
    hass.bus.async_fire(f"domika_state_changed_{install_id}", dict_attributes)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/delete_push_token",
        vol.Required("install_id"): str,
    }
)
@callback
def websocket_domika_delete_push_token(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "delete_push_token", data: {msg}')
    pusher = push.Pusher("")
    pusher.remove_install_id(
        msg.get("install_id")
    )
    connection.send_result(
        msg.get("id"), {}
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/resubscribe",
        vol.Required("install_id"): str,
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
    install_id = msg.get("install_id")

    res_list = []
    if install_id:
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

    # LOGGER.debug(f"### websocket_domika_resubscribe: {install_id}, {res_list} ")

    connection.send_result(
        msg.get("id"), {"entities": res_list}
    )

    pusher = push.Pusher("")
    pusher.resubscribe(
        install_id,
        msg.get("subscriptions")
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/resubscribe_push",
        vol.Required("install_id"): str,
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
    install_id = msg.get("install_id")

    connection.send_result(
        msg.get("id"), {}
    )

    pusher = push.Pusher("")
    pusher.resubscribe_push(
        install_id,
        msg.get("subscriptions")
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/confirm_event",
        vol.Required("install_id"): str,
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
    EVENT_CONFIRMER.add_confirmation(msg.get("install_id"), msg.get("context_id"))
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