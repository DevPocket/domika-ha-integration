from __future__ import annotations

from . HA_Pusher.const import *
from . HA_Pusher import pusher as push

import voluptuous as vol
import orjson

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback, EventOrigin
from .functions import *
import requests

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/update_app_session",
        vol.Optional("app_session_id"): str,
    }
)
@callback
def websocket_domika_update_app_session(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "update_app_session", data: {msg}')
    pusher = push.Pusher("")
    app_session_id = pusher.update_app_session_id(
        msg.get("app_session_id"),
        connection.user.id
    )
    connection.send_result(
        msg.get("id"), {"app_session_id": app_session_id}
    )
    pusher.close_connection()


def job_update_push_notification_token(app_session_id, user_id, push_token_hex, platform, environment, hass):
    pusher = push.Pusher("")
    res = pusher.update_push_notification_token(
        app_session_id,
        user_id,
        push_token_hex,
        platform,
        environment
    )
    pusher.close_connection()
    return res


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/update_push_token",
        vol.Optional("app_session_id"): str,
        vol.Required("push_token_hex"): str,
        vol.Required("platform"): str,
        vol.Required("environment"): str,
    }
)
# @callback
@websocket_api.async_response
async def websocket_domika_update_push_token(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "update_push_token", data: {msg}')
    connection.send_result(
        msg.get("id"), {"result": "accepted"}
    )

    app_session_id = msg.get("app_session_id")
    user_id = connection.user.id
    push_token_hex = msg.get("push_token_hex")
    platform = msg.get("platform")
    environment = msg.get("environment")

    res = await hass.async_add_executor_job(job_update_push_notification_token, app_session_id, user_id, push_token_hex, platform, environment, hass)

    dict_attributes = {"d.type": "push_activation"}
    if res:
        dict_attributes["push_activation_success"] = True
    else:
        dict_attributes["push_activation_success"] = False

    if dict_attributes:
        LOGGER.debug(f"""### domika_{app_session_id}, {dict_attributes} """)
        hass.bus.async_fire_internal(f"domika_{app_session_id}", dict_attributes)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/remove_app_session",
        vol.Required("app_session_id"): str,
    }
)
# @callback
@websocket_api.async_response
async def websocket_domika_remove_app_session(
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
    pusher.close_connection()
    connection.send_result(
        msg.get("id"), await remove_push_session(hass, msg.get("app_session_id"))
    )



@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/update_push_session",
        vol.Required("original_transaction_id"): str,
        vol.Required("push_token_hex"): str,
        vol.Required("platform"): str,
        vol.Required("environment"): str,
    }
)
# @callback
@websocket_api.async_response
async def websocket_domika_update_push_session(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "update_push_session", data: {msg}')
    connection.send_result(
        msg.get("id"), {"result": "accepted"}
    )

    original_transaction_id = msg.get("original_transaction_id")
    token = msg.get("push_token_hex")
    platform = msg.get("platform")
    environment = msg.get("environment")

    if original_transaction_id and token and platform and environment:
        if MICHAELs_PUSH_SERVER:
            url = BASE_URL + "update_push_session"
            json_payload = {"original_transaction_id": original_transaction_id,
                            "token": token,
                            "platform": platform,
                            "environment": environment}
        else:
            url = BASE_URL + "push_session/create"
            json_payload = {"original_transaction_id": original_transaction_id,
                            "push_token": token,
                            "platform": platform,
                            "environment": environment}

        r = await hass.async_add_executor_job(make_post_request, url, json_payload)
        LOGGER.debug(f"update_push_session result: {r.text}, {r.status_code}")



@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/verify_push_session",
        vol.Required("app_session_id"): str,
        vol.Required("verification_key"): str,
    }
)
# @callback
@websocket_api.async_response
async def websocket_domika_verify_push_session(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "verify_push_session", data: {msg}')
    connection.send_result(
        msg.get("id"), {"result": "accepted"}
    )

    app_session_id = msg.get("app_session_id")
    verification_key = msg.get("verification_key")

    if app_session_id and verification_key:
        pusher = push.Pusher("")
        old_push_session_id = pusher.get_push_session(app_session_id)

        if MICHAELs_PUSH_SERVER:
            url = BASE_URL + "verify_push_session"
            json_payload = {"verification_key": verification_key, "old_push_session_id": old_push_session_id}
        else:
            url = BASE_URL + "push_session/verify"
            json_payload = {"verification_key": verification_key}

        r = await hass.async_add_executor_job(make_post_request, url, json_payload)
        LOGGER.debug(f"verify_push_session result: {r.text}, {r.status_code}")
        if MICHAELs_PUSH_SERVER:
            push_session_id = r.text
        else:
            res_dict = dict(json.loads(r.text))
            push_session_id = res_dict.get("push_session_id")

        LOGGER.debug(f"verify_push_session push_session_id: {push_session_id}, code: {r.status_code}")
        if r.status_code == 201 and push_session_id:
            LOGGER.debug(f"verify_push_session saving push_session")
            pusher.save_push_session(app_session_id, push_session_id)
        pusher.close_connection()


async def remove_push_session(hass, app_session_id):
    if app_session_id:
        pusher = push.Pusher("")
        push_session_id = pusher.get_push_session(app_session_id)
        pusher.save_push_session(app_session_id, "")
        pusher.close_connection()
        if push_session_id:
            if MICHAELs_PUSH_SERVER:
                url = BASE_URL + "remove_push_session"
                payload = {"push_session_id": push_session_id}
                add_headers = {}
            else:
                # TODO: Put the right URL
                url = BASE_URL + "remove_push_session"
                payload = {}
                add_headers = {"x-session-id": push_session_id}

            r = await hass.async_add_executor_job(make_delete_request, url, payload, add_headers)
            LOGGER.debug(f"remove_push_session result: {r.text}, {r.status_code}")

@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/remove_push_session",
        vol.Required("app_session_id"): str,
    }
)
# @callback
@websocket_api.async_response
async def websocket_domika_remove_push_session(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "remove_push_session", data: {msg}')
    connection.send_result(
        msg.get("id"), {"status": "accepted"}
    )

    app_session_id = msg.get("app_session_id")
    await remove_push_session(hass, app_session_id)


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
    connection.send_result(
        msg.get("id"), {"result": "accepted"}
    )

    app_session_id = msg.get("app_session_id")
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
        vol.Required("event_ids"): list[str]
    }
)
@callback
def websocket_domika_confirm_events(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "confirm_event", data: {msg}')
    connection.send_result(
        msg.get("id"), {"result": "accepted"}
    )

    event_ids = msg.get("event_ids")
    app_session_id = msg.get("app_session_id")
    if event_ids and app_session_id:
        pusher = push.Pusher("")
        pusher.confirm_events(app_session_id, event_ids)



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
        vol.Required("type"): "domika/update_dashboards",
        vol.Required("dashboards"): str,
        vol.Required("hash"): str,
    }
)
@callback
def websocket_domika_update_dashboards(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "update_dashboards", user: {connection.user.id}, data: {msg}')
    connection.send_result(
        msg.get("id"), {"result": "accepted"}
    )

    pusher = push.Pusher("")
    dash_hash = msg.get("hash")
    dashboards = msg.get("dashboards")
    pusher.save_dashboards(connection.user.id, dashboards, dash_hash)
    app_session_ids = pusher.app_session_ids_for_user_id(connection.user.id)
    pusher.close_connection()
    for app_session_id in app_session_ids:
        LOGGER.debug(f"""### domika_{app_session_id}, dashboard_update """)
        hass.bus.async_fire_internal(f"domika_{app_session_id}", {"d.type": "dashboard_update", "hash": dash_hash})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/get_dashboards",
    }
)
@callback
def websocket_domika_get_dashboards(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "get_dashboards", user: {connection.user.id}, data: {msg}')
    pusher = push.Pusher("")
    dashboards_dict = pusher.get_dashboards(connection.user.id)
    connection.send_result(
        msg.get("id"), dashboards_dict
    )
    pusher.close_connection()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "domika/entity_list",
        vol.Required("domains"): list,
    }
)
@websocket_api.async_response
async def websocket_domika_entity_list(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
) -> None:
    """Handle domika request."""
    LOGGER.debug(f'Got websocket message "entity_list", user: {connection.user.id}')
    domains = msg.get("domains")
    connection.send_result(
        msg.get("id"), await get_entity_list(hass, domains)
    )
