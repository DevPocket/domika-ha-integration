# vim: set fileencoding=utf-8
"""
Integration api.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import asyncio
import logging
import uuid
from http import HTTPStatus

import sqlalchemy
from aiohttp import web
from homeassistant.helpers.http import HomeAssistantView

from ..database.core import AsyncSessionFactory
from ..ha_entity import service as ha_entity_service
from ..push_data import service as push_data_service

LOGGER = logging.getLogger(__name__)


class DomikaAPIPushStatesWithDelay(HomeAssistantView):
    """Push state with delay endpoint."""

    url = '/domika/push_states_with_delay'
    name = 'domika:push-states-with-delay'

    def __init__(self) -> None:
        super().__init__()

    async def post(self, request: web.Request) -> web.Response:
        """Post method."""
        LOGGER.debug('DomikaAPIPushStatesWithDelay')

        request_dict = await request.json()
        LOGGER.debug('request_dict: %s', request_dict)

        app_session_id = request.headers.get('X-App-Session-Id')
        LOGGER.debug('app_session_id: %s', app_session_id)
        try:
            app_session_id = uuid.UUID(app_session_id)
        except (TypeError, ValueError):
            return self.json_message(
                'Missing or malformed X-App-Session-Id.',
                HTTPStatus.UNAUTHORIZED,
            )

        entity_id = request_dict.get('entity_id')
        LOGGER.debug('entity_id: %s', entity_id)

        delay = float(request_dict.get('delay', 0))
        LOGGER.debug('delay: %s', delay)

        await asyncio.sleep(delay)

        try:
            async with AsyncSessionFactory() as session:
                result = await ha_entity_service.get(session, app_session_id, entity_id=entity_id)
            await push_data_service.delete_for_app_session(session, app_session_id=app_session_id)

        except sqlalchemy.exc.SQLAlchemyError as e:
            LOGGER.error('DomikaAPIPushStatesWithDelay. Database error. %s', e)
            return self.json_message('Database error.', HTTPStatus.INTERNAL_SERVER_ERROR)
        except Exception as e:
            LOGGER.exception('DomikaAPIPushStatesWithDelay. Unhandled error. %s', e)
            return self.json_message('Internal error.', HTTPStatus.INTERNAL_SERVER_ERROR)

        data = {'entities': result}
        LOGGER.debug('DomikaAPIPushStatesWithDelay data: %s', data)

        return self.json(data, HTTPStatus.OK)
