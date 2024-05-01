"""The Domika integration."""
from __future__ import annotations

import asyncio
import json
from http import HTTPStatus

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
    def generate_push_notifications_ios(time):
        pusher = push.Pusher("")
        pusher.generate_push_notifications_ios(EVENT_CONFIRMER)
        pusher.close_connection()

    hass.http.register_view(DomikaAPIDomainServicesView)
    hass.http.register_view(DomikaAPIPushStatesWithDelay)

    # Set up the Domika WebSocket commands
    websocket_api.async_register_command(hass, websocket_domika_update_install_id)
    websocket_api.async_register_command(hass, websocket_domika_update_push_token)
    websocket_api.async_register_command(hass, websocket_domika_delete_push_token)
    websocket_api.async_register_command(hass, websocket_domika_resubscribe)
    websocket_api.async_register_command(hass, websocket_domika_resubscribe_push)
    websocket_api.async_register_command(hass, websocket_domika_confirm_event)
    websocket_api.async_register_command(hass, websocket_domika_critical_sensors)
    websocket_api.async_register_command(hass, websocket_domika_save_dashboards)
    websocket_api.async_register_command(hass, websocket_domika_get_dashboards)
    websocket_api.async_register_command(hass, websocket_domika_critical_sensors)
    event.async_track_time_interval(hass, generate_push_notifications_ios, UPDATE_INTERVAL, cancel_on_shutdown=True)
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

        install_id = request.headers.get("X-Install-Id")
        LOGGER.debug(f"install_id: {install_id}")

        await asyncio.sleep(0.5)

        pusher = push.Pusher("")
        push_attributes = pusher.push_attributes_for_install_id(install_id)
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
        # request_dict = dict(json.loads(request_json))
        LOGGER.debug(f"request_dict: {request_dict}")

        # install_id = request.headers.get("X-Install-Id")
        install_id = request_dict.get("install_id")
        LOGGER.debug(f"install_id: {install_id}")

        if install_id:
            await asyncio.sleep(5)

            pusher = push.Pusher("")
            push_attributes = pusher.push_attributes_for_install_id(install_id)
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
                body={"error": "no install_id"},
                content_type=CONTENT_TYPE_JSON,
                status=int(HTTPStatus.BAD_REQUEST),
                headers=None,
                zlib_executor_size=32768,
            )

def forward_event(event):
    def fire_events_to_install_ids(install_ids: list):
        for install_id in install_ids:
            dict_attributes = dict(attributes)
            dict_attributes["entity_id"] = entity_id
            LOGGER.debug(f"""### domika_state_changed_{install_id}, {dict_attributes}, {event.origin}, {event.context.id}, {event.time_fired} """)
            HASS.bus.async_fire(f"domika_state_changed_{install_id}", dict_attributes, event.origin, event.context, event.time_fired.timestamp())


    if event.event_type == "state_changed":
        LOGGER.debug(f">>> Got event for entity: {event.data['entity_id']}")
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
            if entity_id.startswith("binary_sensor."):
                # Get device_class for this binary sensor.
                sensor = HASS.states.get(entity_id)
                device_class = sensor.attributes.get("device_class")

                if device_class in SENSORS_DEVICE_CLASSES:
                    # Fetch current state for all critical binary sensors.
                    sensors_data = get_critical_sensors(HASS)
                    # Fire the event for app to catch.
                    HASS.bus.async_fire("critical_sensors_changed", sensors_data, event.origin, event.context, event.time_fired.timestamp())

            # Check if any install_ids are subscribed for these attributes.
            # If so, fire the event to those install_ids for app to catch.
            pusher = push.Pusher("")
            install_ids = pusher.install_ids_for_event(entity_id, attributes)
            LOGGER.debug(f"install_ids_for_event: {install_ids}")
            if install_ids:
                fire_events_to_install_ids(install_ids)

            # Record event in Pusher db.
            pusher.add_event(entity_id, attributes, event.context.id, event.time_fired.timestamp() * 1e6)
            pusher.close_connection()



