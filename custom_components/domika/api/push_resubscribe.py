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
from typing import cast

import sqlalchemy
from aiohttp import web
from homeassistant.helpers.http import HomeAssistantView

from ..const import MAIN_LOGGER_NAME
from ..database.core import AsyncSessionFactory
from ..ha_entity import service as ha_entity_service
from ..push_data import service as push_data_service
from ..subscription.flow import resubscribe_push

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


class DomikaAPIPushResubscribe(HomeAssistantView):
    """Push state with delay endpoint."""

    url = '/domika/push_resubscribe'
    name = 'domika:push-resubscribe'

    def __init__(self) -> None:
        super().__init__()

    """{
        "app_session_id": "0eb99a18-5907-484a-873d-9e87e29faa50",
        "subscriptions": {
            "light.basement_back_light":
            [
                "a.effect",
                "a.brightness",
                "s"
            ],
            "light.basement":
            [
                "a.hs_color",
                "a.effect",
                "s"
            ]
        }
    }"""
    async def post(self, request: web.Request) -> web.Response:
        """Post method."""
        LOGGER.debug('DomikaAPIPushResubscribe')

        request_dict = await request.json()
        LOGGER.debug('request_dict: %s', request_dict)

        app_session_id = request.headers.get('X-App-Session-Id')
        try:
            app_session_id = uuid.UUID(app_session_id)
        except (TypeError, ValueError):
            return self.json_message(
                'Missing or malformed X-App-Session-Id.',
                HTTPStatus.UNAUTHORIZED,
            )

        subscriptions = cast(dict[str, set[str]], request_dict.get('subscriptions', None))
        if not subscriptions:
            return self.json_message(
                'Missing or malformed subscriptions.',
                HTTPStatus.UNAUTHORIZED,
            )

        try:
            async with AsyncSessionFactory() as session:
                await resubscribe_push(session, app_session_id, subscriptions)
        except sqlalchemy.exc.SQLAlchemyError as e:
            LOGGER.error('Can\'t resubscribe push "%s". Database error. %s', subscriptions, e)
        except Exception as e:
            LOGGER.exception('Can\'t resubscribe push "%s". Unhandled error. %s', subscriptions, e)

        data = {'result': "success"}
        LOGGER.debug('DomikaAPIPushResubscribe data: %s', data)

        return self.json(data, HTTPStatus.OK)
