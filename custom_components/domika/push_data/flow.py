# vim: set fileencoding=utf-8
"""
Push data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import json
import logging
import uuid
from typing import Sequence

import aiohttp
import sqlalchemy
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from sqlalchemy.ext.asyncio import AsyncSession

from .. import push_server_errors, statuses
from ..const import MAIN_LOGGER_NAME, PUSH_SERVER_TIMEOUT, PUSH_SERVER_URL
from ..critical_sensor import service as critical_sensor_service
from ..critical_sensor.enums import CriticalityLevel
from ..database.core import AsyncSessionFactory
from ..device import service as device_service
from ..device.models import Device, DomikaDeviceUpdate
from ..subscription.flow import get_app_session_id_by_attributes
from ..utils import flatten_json
from .models import DomikaPushDataCreate, PushData
from .service import create, delete_all

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)

DOMIKA_CRITICAL_SENSOR_CHANGED = 'domika_critical_sensors_changed'


def _fire_events_to_app_session_ids(
    hass: HomeAssistant,
    event: Event[EventStateChangedData],
    event_id: uuid.UUID,
    entity_id: str,
    attributes: set[tuple],
    app_session_ids: Sequence[uuid.UUID],
):
    dict_attributes = dict(attributes)
    dict_attributes['d.type'] = 'state_changed'
    dict_attributes['event_id'] = event_id
    dict_attributes['entity_id'] = entity_id
    for app_session_id in app_session_ids:
        hass.bus.async_fire(
            f'domika_{app_session_id}',
            dict_attributes,
            event.origin,
            event.context,
            event.time_fired.timestamp(),
        )
        LOGGER.debug(
            '### domika_%s, %s, %s, %s, %s',
            app_session_id,
            dict_attributes,
            event.origin,
            event.context.id,
            event.time_fired,
        )


async def register_event(hass: HomeAssistant, event: Event[EventStateChangedData]):
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

    LOGGER.debug('Got event for entity: %s, attributes: %s', entity_id, attributes)

    if not attributes:
        return

    is_critical = critical_sensor_service.is_critical(hass, entity_id, CriticalityLevel.CRITICAL)

    # Fire event for application if critical sensor changed it's state.
    if is_critical:
        # If entity id is a critical binary sensor.
        # Fetch state for all levels of critical binary sensors.
        sensors_data = critical_sensor_service.get(hass, CriticalityLevel.ANY)
        # Fire the event for app.
        hass.bus.async_fire(
            DOMIKA_CRITICAL_SENSOR_CHANGED,
            sensors_data.to_dict(),
            event.origin,
            event.context,
            event.time_fired.timestamp(),  # TODO: convert to int?
        )
        LOGGER.debug(
            '### %s, %s, %s, %s, %s',
            DOMIKA_CRITICAL_SENSOR_CHANGED,
            sensors_data.to_dict(),
            event.origin,
            event.context.id,
            event.time_fired,
        )

    # Store events into db.
    event_id = uuid.uuid4()
    # TODO: use timestamp from event. event.time_fired.timestamp() * 1e6
    push_data = [
        DomikaPushDataCreate(
            event_id,
            entity_id,
            attribute[0],
            attribute[1],
            event.context.id,
            int(event.time_fired.timestamp() * 1e6),
        )
        for attribute in attributes
    ]
    async with AsyncSessionFactory() as session:
        # Create push_data.
        await create(session, push_data)
        app_session_ids = await get_app_session_id_by_attributes(
            session,
            entity_id,
            [attribute[0] for attribute in attributes],
        )
        # If any app_session_ids are subscribed for these attributes - fire the event to those
        # app_session_ids for app to catch.
        if app_session_ids:
            _fire_events_to_app_session_ids(
                hass,
                event,
                event_id,
                entity_id,
                attributes,
                app_session_ids,
            )

        if is_critical:
            verified_devices = await device_service.get_all_with_push_session_id(session)

            # Create events dict for critical push.
            # Format example:
            # '{
            # '  "binary_sensor.smoke": {
            # '    "s": {
            # '      "v": "on",
            # '        "t": 717177272
            # '     }
            # '  }
            # '}
            events_dict = {}
            entity = {}
            events_dict[entity_id] = entity
            for pd in push_data:
                entity[pd.attribute] = {
                    'v': pd.value,
                    't': pd.timestamp,
                }

            for device in verified_devices:
                await _send_push_data(
                    session,
                    device.app_session_id,
                    # get_all_with_push_session_id return devices with filled push_session_id.
                    device.push_session_id,  # type: ignore
                    events_dict,
                    critical=True,
                )


async def _send_push_data(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    push_session_id: uuid.UUID,
    events_dict: dict,
    *,
    critical: bool = False,
):
    LOGGER.debug('Push %sevents. %s', 'critical ' if critical else '', events_dict)

    try:
        async with (
            aiohttp.ClientSession(json_serialize=json.dumps) as session,
            session.post(
                f'{PUSH_SERVER_URL}/notification/critical_push'
                if critical
                else f'{PUSH_SERVER_URL}/notification/push',
                headers={
                    # TODO: rename to x-push-session-id
                    'x-session-id': str(push_session_id),
                },
                json={'data': json.dumps(events_dict)},
                timeout=PUSH_SERVER_TIMEOUT,
            ) as resp,
        ):
            if resp.status == statuses.HTTP_204_NO_CONTENT:
                # All OK. Notification pushed.
                return

            if resp.status == statuses.HTTP_401_UNAUTHORIZED:
                # Push session id not found on push server.
                # Remove push session id for device.
                device = await device_service.get(db_session, app_session_id)
                if device:
                    LOGGER.info(
                        'The server rejected push session id "%s"',
                        push_session_id,
                    )
                    await device_service.update(
                        db_session,
                        device,
                        DomikaDeviceUpdate(push_session_id=None),
                    )
                    LOGGER.info(
                        'Push session "%s" for app session "%s" successfully removed',
                        push_session_id,
                        app_session_id,
                    )
                return

            if resp.status == statuses.HTTP_400_BAD_REQUEST:
                raise push_server_errors.BadRequestError(await resp.json())

            raise push_server_errors.UnexpectedServerResponseError(resp.status)
    except aiohttp.ClientError as e:
        raise push_server_errors.PushServerError(str(e)) from None


async def push_registered_events():
    async with AsyncSessionFactory() as session:
        # TODO: add check for elapsed time.
        stmt = sqlalchemy.select(PushData, Device.push_session_id)
        stmt = stmt.join(Device, PushData.app_session_id == Device.app_session_id)
        stmt = stmt.where(Device.push_session_id.is_not(None))
        stmt = stmt.group_by(
            PushData.app_session_id,
            PushData.entity_id,
            PushData.attribute,
        )
        stmt = stmt.having(PushData.timestamp == sqlalchemy.func.max(PushData.timestamp))
        stmt = stmt.order_by(
            PushData.app_session_id,
            PushData.entity_id,
        )
        events = (await session.execute(stmt)).all()

        # Create events dict.
        # Format example:
        # '{
        # '  "binary_sensor.smoke": {
        # '    "s": {
        # '       "v": "on",
        # '       "t": 717177272
        # '     }
        # '  },
        # '  "light.light": {
        # '    "s": {
        # '       "v": "off",
        # '       "t": 717145367
        # '     }
        # '  },
        # '}
        events_dict = {}
        current_entity_id: str | None = None
        current_push_session_id: uuid.UUID | None = None
        current_app_session_id: uuid.UUID | None = None

        entity = {}
        for event in events:
            if current_push_session_id != event[1]:
                current_push_session_id = event[1]
                current_app_session_id = event[0].app_session_id
                if events_dict and current_push_session_id:
                    await _send_push_data(
                        session,
                        current_app_session_id,  # type: ignore
                        current_push_session_id,
                        events_dict,
                    )
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
            await _send_push_data(
                session,
                current_app_session_id,  # type: ignore
                current_push_session_id,
                events_dict,
            )

        await delete_all(session)
