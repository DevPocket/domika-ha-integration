# vim: set fileencoding=utf-8
"""
Push data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import json
import logging
import uuid
from typing import Any, Sequence

import aiohttp
import sqlalchemy
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from sqlalchemy.ext.asyncio import AsyncSession

from .. import push_server_errors, statuses
from ..const import IOS_PLATFORM, MAIN_LOGGER_NAME, PUSH_SERVER_URL
from ..critical_sensor import service as critical_sensor_service
from ..database.core import AsyncSessionFactory
from ..device.models import Device
from ..subscription.flow import get_app_session_id_by_attributes
from ..utils import flatten_json
from .models import DomikaPushDataCreate, PushData
from .service import create, delete_for_platform, get_by_platform

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


def _fire_events_to_app_session_ids(
    hass: HomeAssistant,
    event: Event[EventStateChangedData],
    entity_id: str,
    attributes: set[tuple],
    app_session_ids: Sequence[uuid.UUID],
):
    dict_attributes = dict(attributes)
    dict_attributes['entity_id'] = entity_id
    dict_attributes['d.type'] = 'state_changed'
    for app_session_id in app_session_ids:
        LOGGER.debug(
            '### domika_%s, %s, %s, %s, %s',
            app_session_id,
            dict_attributes,
            event.origin,
            event.context.id,
            event.time_fired,
        )
        hass.bus.async_fire(
            f'domika_{app_session_id}',
            dict_attributes,
            event.origin,
            event.context,
            event.time_fired.timestamp(),
        )


async def register_event(hass: HomeAssistant, event: Event[EventStateChangedData]):
    # Register only state_changed events.
    # if event.event_type != 'state_changed':
    #     return

    event_data: EventStateChangedData = event.data
    if not event_data:
        return

    entity_id = event_data['entity_id']
    old_state = event_data['old_state'].as_compressed_state if event_data['old_state'] else {}
    new_state = event_data['new_state'].as_compressed_state if event_data['new_state'] else {}

    # Make a flat dict from state data.
    old_attributes = flatten_json(old_state, exclude={'c', 'lc', 'lu'}) or {}
    new_attributes = flatten_json(new_state, exclude={'c', 'lc', 'lu'}) or {}

    # Calculate the changed attributes by subtracting old_state elements from new_state.
    attributes = set(new_attributes.items()) - set(old_attributes.items())

    LOGGER.debug('>>> Got event for entity: %s, attributes: %s', entity_id, attributes)

    if not attributes:
        return

    # Fire event for application if critical sensor changed it's state.
    if entity_id.startswith('binary_sensor.'):
        # If entity id is a critical sensor
        critical_sensor_state = critical_sensor_service.get_critical_sensor_state(hass, entity_id)
        if critical_sensor_state:
            # Fetch state for all critical binary sensors.
            sensors_data = critical_sensor_service.get(hass)
            # Fire the event for app.
            hass.bus.async_fire(
                'critical_sensors_changed',
                sensors_data.to_dict(),
                event.origin,
                event.context,
                event.time_fired.timestamp(),
            )

        # sensor = hass.states.get(entity_id)
        # # Get device_class for this binary sensor.
        # device_class = sensor.attributes.get('device_class')

        # if device_class in SENSORS_DEVICE_CLASSES:
        #     sensors_data = get_critical_sensors(HASS)
        #     # Fire the event for app to catch.
        #     hass.bus.async_fire(
        #         'critical_sensors_changed',
        #         sensors_data,
        #         event.origin,
        #         event.context,
        #         event.time_fired.timestamp(),
        #     )

    # Store events into db.
    event_uuid = uuid.uuid4()
    # TODO: use timestamp from event.
    push_data = [
        DomikaPushDataCreate(event_uuid, entity_id, attribute[0], attribute[1], event.context.id)
        for attribute in attributes
    ]
    async with AsyncSessionFactory() as session:
        await create(session, push_data)
        app_session_ids = await get_app_session_id_by_attributes(
            session,
            entity_id,
            [attribute[0] for attribute in attributes],
        )

    # If any app_session_ids are subscribed for these attributes - fire the event to those
    # app_session_ids for app to catch.
    if app_session_ids:
        _fire_events_to_app_session_ids(hass, event, entity_id, attributes, app_session_ids)

    # # Record event in Pusher db.
    # pusher.add_event(
    #     entity_id,
    #     attributes,
    #     event.context.id,
    #     event.time_fired.timestamp() * 1e6,
    # )


async def _send_push_data(push_session_id: uuid.UUID, events_dict: dict):
    async with (
        aiohttp.ClientSession(json_serialize=json.dumps) as session,
        session.post(
            f'{PUSH_SERVER_URL}/notification/push',
            headers={
                # TODO: rename to x-push-session-id
                'x-session-id': str(push_session_id),
            },
            json={'data': json.dumps(events_dict)},
        ) as resp,
    ):
        if resp.status == statuses.HTTP_200_OK:
            return

        if resp.status == statuses.HTTP_400_BAD_REQUEST:
            raise push_server_errors.BadRequestError(await resp.json())

        raise push_server_errors.UnexpectedServerResponseError(resp.status)


async def _push_ios(db_session: AsyncSession):
    # TODO: add check for elapsed time.
    stmt = sqlalchemy.select(PushData, Device.push_session_id)
    stmt = stmt.join(Device, PushData.app_session_id == Device.app_session_id)
    # TODO: uncomment.
    stmt = stmt.where(Device.push_session_id.is_not(None))
    # stmt = stmt.where(Device.platform == IOS_PLATFORM)
    stmt = stmt.group_by(
        PushData.app_session_id,
        PushData.entity_id,
        PushData.attribute,
    )
    stmt = stmt.having(PushData.timestamp == sqlalchemy.func.max(PushData.timestamp))
    stmt = stmt.order_by(
        PushData.app_session_id,
        Device.push_token,
        PushData.entity_id,
    )
    events = (await db_session.execute(stmt)).all()

    # events = await get_by_platform(db_session, IOS_PLATFORM)

    events_dict = {}
    current_entity_id: str | None = None
    current_push_session_id: uuid.UUID | None = None

    entity = {}
    for event in events:
        if current_push_session_id != event[1]:
            current_push_session_id = event[1]
            if events_dict and current_push_session_id:
                LOGGER.debug('Push ios events. %s', events_dict)
                await _send_push_data(current_push_session_id, events_dict)
            current_entity_id = None
            events_dict = {}
        if current_entity_id != event[0].entity_id:
            entity = {}
            events_dict[event[0].entity_id] = entity
            current_entity_id = event[0].entity_id
        entity[event[0].attribute] = {
            'v': event[0].value,
            't': event[0].timestamp,
        }

    if events_dict and current_push_session_id:
        LOGGER.debug('Push ios events. %s', events_dict)
        await _send_push_data(current_push_session_id, events_dict)

    # await delete_for_platform(db_session, IOS_PLATFORM)


async def push_registered_events():
    async with AsyncSessionFactory() as session:
        await _push_ios(session)
