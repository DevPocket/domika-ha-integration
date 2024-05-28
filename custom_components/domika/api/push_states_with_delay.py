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

from aiohttp import web
from homeassistant.helpers.http import HomeAssistantView

from ..const import MAIN_LOGGER_NAME
from ..database.core import AsyncSessionFactory
from ..ha_entity import service as ha_entity_service

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


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

        app_session_id = request_dict.get('app_session_id', None)
        try:
            app_session_id = uuid.UUID(app_session_id)
        except (TypeError, ValueError):
            return self.json_message(
                'Missing or malformed X-App-Session-Id.',
                HTTPStatus.UNAUTHORIZED,
            )

        delay = int(request_dict.get('delay', 0))
        LOGGER.debug('app_session_id: %s', app_session_id)

        await asyncio.sleep(delay)

        async with AsyncSessionFactory() as session:
            result = await ha_entity_service.get(session, app_session_id)

        data = {'entities': result}
        LOGGER.debug('DomikaAPIPushStatesWithDelay data: %s', data)

        return self.json(data, HTTPStatus.OK)
