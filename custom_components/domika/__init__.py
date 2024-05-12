"""The Domika integration."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
from http import HTTPStatus

import homeassistant.helpers.config_validation as cv
import orjson
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.api import APIDomainServicesView, APIServicesView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.helpers.typing import ConfigType

from . import websocket_commands as wsc
from .const import DOMAIN, MAIN_LOGGER_NAME, SENSORS_DEVICE_CLASSES, UPDATE_INTERVAL
from .critical_sensors import router as critical_sensor_router
from .dashboard import router as dashboard_router
from .database.manage import migrate
from .functions import (
    event_data_to_dict,
    get_critical_sensors,
    json_encoder_domika,
    make_dictionary,
)
from .HA_Pusher.pusher import Pusher

# Importing database models to fill sqlalchemy metadata.
# isort: off
from .dashboard.models import Dashboard
from .device.models import Device
from .push_data.models import PushData
from .push_data.models import _Event
from .subscription.models import Subscription
# isort: on

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
HASS: HomeAssistant


async def heartbeat():
    """
    Domika heartbeat.

    Perform perioodic activities.
    """
    LOGGER.info('Heartbeat started.')
    try:
        while True:
            await asyncio.sleep(2)
            LOGGER.debug('Heartbeat')
    except asyncio.CancelledError as e:
        LOGGER.info('Heartbeat stopped. %s.', e)
        raise


async def async_setup_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    # Migrate database.
    await migrate()

    _entry.async_create_background_task(_hass, heartbeat(), 'heartbeat')
    LOGGER.debug('Entry loaded.')
    return True


async def async_unload_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug('Entry unloaded.')
    return True


async def async_migrate_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    LOGGER.debug('Entry migration finished.')
    return True


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up component."""
    LOGGER.setLevel(logging.DEBUG)

    LOGGER.debug('Async setup.')

    def generate_push_notifications_ios(_time: datetime.datetime):
        pusher = Pusher('')
        pusher.generate_push_notifications_ios(wsc.EVENT_CONFIRMER)
        pusher.close_connection()

    hass.http.register_view(DomikaAPIDomainServicesView)
    hass.http.register_view(DomikaAPIPushStatesWithDelay)

    # Set up the Domika WebSocket commands
    websocket_api.async_register_command(hass, wsc.websocket_domika_update_app_session)
    websocket_api.async_register_command(hass, wsc.websocket_domika_update_push_token)
    websocket_api.async_register_command(hass, wsc.websocket_domika_remove_app_session)
    websocket_api.async_register_command(hass, wsc.websocket_domika_update_push_session)
    websocket_api.async_register_command(hass, wsc.websocket_domika_verify_push_session)
    websocket_api.async_register_command(hass, wsc.websocket_domika_remove_push_session)
    websocket_api.async_register_command(hass, wsc.websocket_domika_resubscribe)
    websocket_api.async_register_command(hass, wsc.websocket_domika_resubscribe_push)
    websocket_api.async_register_command(hass, wsc.websocket_domika_confirm_event)
    websocket_api.async_register_command(
        hass,
        critical_sensor_router.websocket_domika_critical_sensors,
    )
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_update_dashboards)
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_get_dashboards)

    async_track_time_interval(
        hass,
        generate_push_notifications_ios,
        UPDATE_INTERVAL,
        cancel_on_shutdown=True,
    )
    # Set up the Domika Event Listener
    hass.bus.async_listen('state_changed', forward_event)
    global HASS
    HASS = hass

    return True


def get_states_for_system_widgets(push_attributes: list):
    res_list = []
    for entity_data in push_attributes:
        entity_id = entity_data['entity_id']
        attributes_list = entity_data['attributes']
        state = HASS.states.get(entity_id)
        if state:
            dict_attributes = {}
            state_bytes = orjson.dumps(
                state.as_compressed_state,
                default=json_encoder_domika,
                option=orjson.OPT_NON_STR_KEYS,
            )
            compressed_state = orjson.loads(state_bytes)
            make_dictionary(compressed_state, '', dict_attributes)
            filtered_dict = {k: v for (k, v) in dict_attributes.items() if k in attributes_list}
            time_updated = max(state.last_changed, state.last_updated).timestamp()
            res_list.append(
                {'entity_id': entity_id, 'time_updated': time_updated, 'attributes': filtered_dict}
            )
        else:
            LOGGER.error(
                'get_states_for_system_widgets is requesting state of unknown entity: %s',
                entity_id,
            )
    return res_list


class DomikaAPIDomainServicesView(APIDomainServicesView):
    """View to handle Status requests."""

    url = '/domika/services/{domain}/{service}'
    name = 'domika:domain-services'

    async def post(self, request: web.Request, domain: str, service: str) -> web.Response:
        """Retrieve if API is running."""
        LOGGER.debug('DomikaAPIDomainServicesView')
        response = await super().post(request, domain, service)

        app_session_id = request.headers.get('X-App-Session-Id')
        LOGGER.debug(f'app_session_id: {app_session_id}')

        await asyncio.sleep(0.5)

        pusher = Pusher('')
        push_attributes = pusher.push_attributes_for_app_session_id(app_session_id)
        res_list = get_states_for_system_widgets(push_attributes)

        LOGGER.debug(f'entities data: {res_list}')
        data = json.dumps({'entities': res_list})
        LOGGER.debug(f'DomikaAPIDomainServicesView data: {data}')
        response.body = data
        return response


class DomikaAPIPushStatesWithDelay(HomeAssistantView):
    url = '/domika/push_states_with_delay'
    name = 'domika:push-states-with-delay'

    async def post(self, request: web.Request) -> web.Response:
        LOGGER.debug('DomikaAPIPushStatesWithDelay')

        request_dict = await request.json()
        LOGGER.debug(f'request_dict: {request_dict}')

        app_session_id = request_dict.get('app_session_id')
        delay = int(request_dict.get('delay'))
        LOGGER.debug(f'app_session_id: {app_session_id}')

        if app_session_id:
            await asyncio.sleep(delay)

            pusher = Pusher('')
            push_attributes = pusher.push_attributes_for_app_session_id(app_session_id)
            res_list = get_states_for_system_widgets(push_attributes)

            LOGGER.debug(f'entities data: {res_list}')
            data = json.dumps({'entities': res_list})
            LOGGER.debug(f'DomikaAPIPushStatesWithDelay data: {data}')

            return web.Response(
                body=data,
                content_type=CONTENT_TYPE_JSON,
                status=int(HTTPStatus.OK),
                headers=None,
                zlib_executor_size=32768,
            )

        return web.Response(
            body={'error': 'no app_session_id'},
            content_type=CONTENT_TYPE_JSON,
            # TODO: NOT_FOUND
            status=int(HTTPStatus.BAD_REQUEST),
            headers=None,
            zlib_executor_size=32768,
        )


def forward_event(event: Event):
    def fire_events_to_app_session_ids(app_session_ids: list):
        for app_session_id in app_session_ids:
            dict_attributes = dict(attributes)
            dict_attributes['entity_id'] = entity_id
            LOGGER.debug(
                f'### domika_state_changed_{app_session_id}, {dict_attributes}, {event.origin}, '
                f'{event.context.id}, {event.time_fired}',
            )
            HASS.bus.async_fire(
                f'domika_state_changed_{app_session_id}',
                dict_attributes,
                event.origin,
                event.context,
                event.time_fired.timestamp(),
            )

    if event.event_type == 'state_changed':
        LOGGER.debug('>>> Got event for entity: %s', event.data['entity_id'])
        # Make a flat dict from state data.
        old_attributes = event_data_to_dict(event.data['old_state']) or {}
        new_attributes = event_data_to_dict(event.data['new_state']) or {}
        # Calculate the changed attributes by subtracting old_state elements from new_state.
        attributes = set(new_attributes.items()) - set(old_attributes.items())
        entity_id = event.data['entity_id'] or ''
        # LOGGER.debug(f"""### EVENT
        #     entity_id: {entity_id}
        #     old_attributes: {old_attributes}
        #     new_attributes: {new_attributes}
        #     attributes: {attributes}
        #     timestamp: {event.time_fired.timestamp()}
        #     """)

        if attributes:
            if entity_id.startswith('binary_sensor.'):
                # Get device_class for this binary sensor.
                sensor = HASS.states.get(entity_id)
                device_class = sensor.attributes.get('device_class')

                if device_class in SENSORS_DEVICE_CLASSES:
                    # Fetch current state for all critical binary sensors.
                    sensors_data = get_critical_sensors(HASS)
                    # Fire the event for app to catch.
                    HASS.bus.async_fire(
                        'critical_sensors_changed',
                        sensors_data,
                        event.origin,
                        event.context,
                        event.time_fired.timestamp(),
                    )

            # Check if any app_session_ids are subscribed for these attributes.
            # If so, fire the event to those app_session_ids for app to catch.
            pusher = Pusher('')
            app_session_ids = pusher.app_session_ids_for_event(entity_id, attributes)
            LOGGER.debug(f'app_session_ids_for_event: {app_session_ids}')
            if app_session_ids:
                fire_events_to_app_session_ids(app_session_ids)

            # Record event in Pusher db.
            pusher.add_event(
                entity_id,
                attributes,
                event.context.id,
                event.time_fired.timestamp() * 1e6,
            )
            pusher.close_connection()
