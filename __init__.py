"""The Domika integration."""
from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from uuid import uuid4

from aiohttp import web
from homeassistant.components.api import APIDomainServicesView, APIServicesView
from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import event

from .websocket_commands import *
from .functions import *

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
HASS: HomeAssistant

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def send_pushes_regularly(time):
        await hass.async_add_executor_job(generate_push_notifications_ios, hass)

    async def generate_push_notifications_ios(hass):
        pusher = push.Pusher("")
        pusher.generate_push_notifications_ios()
        pusher.close_connection()


    hass.http.register_view(DomikaAPIDomainServicesView)
    hass.http.register_view(DomikaAPIPushStatesWithDelay)

    # Set up the Domika WebSocket commands
    websocket_api.async_register_command(hass, websocket_domika_update_app_session)
    websocket_api.async_register_command(hass, websocket_domika_update_push_token)
    websocket_api.async_register_command(hass, websocket_domika_remove_app_session)
    websocket_api.async_register_command(hass, websocket_domika_update_push_session)
    websocket_api.async_register_command(hass, websocket_domika_verify_push_session)
    websocket_api.async_register_command(hass, websocket_domika_remove_push_session)
    websocket_api.async_register_command(hass, websocket_domika_resubscribe)
    websocket_api.async_register_command(hass, websocket_domika_resubscribe_push)
    websocket_api.async_register_command(hass, websocket_domika_confirm_events)
    websocket_api.async_register_command(hass, websocket_domika_critical_sensors)
    websocket_api.async_register_command(hass, websocket_domika_update_dashboards)
    websocket_api.async_register_command(hass, websocket_domika_get_dashboards)
    websocket_api.async_register_command(hass, websocket_domika_critical_sensors)
    event.async_track_time_interval(hass, send_pushes_regularly, UPDATE_INTERVAL, cancel_on_shutdown=True)
    # Set up the Domika Event Listener
    hass.bus.async_listen("state_changed", forward_event)
    global HASS
    HASS = hass

    return True


def get_states_for_system_widgets(push_attributes: list):
    res_list = []
    for entity_data in push_attributes:
        entity_id = entity_data["entity_id"]
        attributes_list = entity_data["attributes"]
        state = HASS.states.get(entity_id)
        if state:
            dict_attributes = {}
            state_bytes = orjson.dumps(
                state.as_compressed_state,
                default=json_encoder_domika,
                option=orjson.OPT_NON_STR_KEYS)
            compressed_state = orjson.loads(state_bytes)
            make_dictionary(compressed_state, "", dict_attributes)
            filtered_dict = {k: v for (k, v) in dict_attributes.items() if k in attributes_list}
            time_updated = max(state.last_changed, state.last_updated).timestamp()
            res_list.append({"entity_id": entity_id, "time_updated": time_updated, "attributes": filtered_dict})
        else:
            LOGGER.error(f"get_states_for_system_widgets is requesting state of unknown entity: {entity_id}")
    return res_list


class DomikaAPIDomainServicesView(APIDomainServicesView):
    """View to handle Status requests."""

    url = "/domika/services/{domain}/{service}"
    name = "domika:domain-services"

    async def post(
        self, request: web.Request, domain: str, service: str
    ) -> web.Response:
        """Retrieve if API is running."""
        LOGGER.debug(f"DomikaAPIDomainServicesView")
        response = await super().post(request, domain, service)

        app_session_id = request.headers.get("X-App-Session-Id")
        LOGGER.debug(f"app_session_id: {app_session_id}")

        await asyncio.sleep(0.5)

        pusher = push.Pusher("")
        push_attributes = pusher.push_attributes_for_app_session_id(app_session_id)
        res_list = get_states_for_system_widgets(push_attributes)

        LOGGER.debug(f"entities data: {res_list}")
        data = json.dumps({ "entities": res_list })
        LOGGER.debug(f"DomikaAPIDomainServicesView data: {data}")
        response.body = data
        return response


class DomikaAPIPushStatesWithDelay(HomeAssistantView):

    url = "/domika/push_states_with_delay"
    name = "domika:push-states-with-delay"

    async def post(
        self, request: web.Request
    ) -> web.Response:
        LOGGER.debug(f"DomikaAPIPushStatesWithDelay")

        request_dict = await request.json()
        LOGGER.debug(f"request_dict: {request_dict}")

        app_session_id = request_dict.get("app_session_id")
        delay = int(request_dict.get("delay"))
        LOGGER.debug(f"app_session_id: {app_session_id}")

        if app_session_id:
            await asyncio.sleep(delay)

            pusher = push.Pusher("")
            push_attributes = pusher.push_attributes_for_app_session_id(app_session_id)
            res_list = get_states_for_system_widgets(push_attributes)

            LOGGER.debug(f"entities data: {res_list}")
            data = json.dumps({ "entities": res_list })
            LOGGER.debug(f"DomikaAPIPushStatesWithDelay data: {data}")

            return web.Response(
                body=data,
                content_type=CONTENT_TYPE_JSON,
                status=int(HTTPStatus.OK),
                headers=None,
                zlib_executor_size=32768,
            )
        else:
            return web.Response(
                body={"error": "no app_session_id"},
                content_type=CONTENT_TYPE_JSON,
                status=int(HTTPStatus.BAD_REQUEST),
                headers=None,
                zlib_executor_size=32768,
            )

def forward_event(event):
    def fire_events_to_app_session_ids(app_session_ids: list):
        for app_session_id in app_session_ids:
            dict_attributes = dict(attributes)
            dict_attributes["entity_id"] = entity_id
            dict_attributes["d.type"] = "state_changed"
            LOGGER.debug(f"""### domika_{app_session_id}, {dict_attributes}, {event.origin}, {event.context.id}, {event.time_fired} """)
            HASS.bus.async_fire_internal(f"domika_{app_session_id}", dict_attributes, event.origin, event.context, event.time_fired.timestamp())


    if event.event_type == "state_changed":
        LOGGER.debug(f">>> Got event for entity: {event.data['entity_id']}")
        event_id = str(uuid4())
        # Make a flat dict from state data.
        old_attributes = event_data_to_dict(event.data["old_state"]) or {}
        new_attributes = event_data_to_dict(event.data["new_state"]) or {}
        # Calculate the changed attributes by subtracting old_state elements from new_state.
        attributes = set(new_attributes.items()) - set(old_attributes.items())
        entity_id = event.data['entity_id'] or ""
        # LOGGER.debug(f"""### EVENT
        #     entity_id: {entity_id}
        #     old_attributes: {old_attributes}
        #     new_attributes: {new_attributes}
        #     attributes: {attributes}
        #     timestamp: {event.time_fired.timestamp()}
        #     """)

        if attributes:
            attributes.add( ("event_id", event_id) )
            if entity_id.startswith("binary_sensor."):
                # Get device_class for this binary sensor.
                sensor = HASS.states.get(entity_id)
                device_class = sensor.attributes.get("device_class")

                if device_class in SENSORS_DEVICE_CLASSES:
                    # Fetch current state for all critical binary sensors.
                    sensors_data = get_critical_sensors(HASS)
                    # Fire the event for app to catch.
                    HASS.bus.async_fire_internal("domika_critical_sensors_changed", sensors_data, event.origin, event.context, event.time_fired.timestamp())

            # Check if any app_session_ids are subscribed for these attributes.
            # If so, fire the event to those app_session_ids for app to catch.
            pusher = push.Pusher("")
            app_session_ids = pusher.app_session_ids_for_event(entity_id, attributes)
            LOGGER.debug(f"app_session_ids_for_event: {app_session_ids}")
            if app_session_ids:
                fire_events_to_app_session_ids(app_session_ids)

            # Record event in Pusher db.
            pusher.add_event(entity_id, attributes, event_id, event.time_fired.timestamp() * 1e6)
            pusher.close_connection()



