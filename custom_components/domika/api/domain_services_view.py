# vim: set fileencoding=utf-8
"""
Integration api.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import asyncio
import json
import logging
import uuid
from http import HTTPStatus

import sqlalchemy.exc
from aiohttp import web
from homeassistant.components.api import APIDomainServicesView

from ..const import MAIN_LOGGER_NAME
from ..database.core import AsyncSessionFactory
from ..ha_entity import service as ha_entity_service

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


class DomikaAPIDomainServicesView(APIDomainServicesView):
    """View to handle Status requests."""

    url = '/domika/services/{domain}/{service}'
    name = 'domika:domain-services'

    async def post(self, request: web.Request, domain: str, service: str) -> web.Response:
        """Retrieve if API is running."""
        LOGGER.debug('DomikaAPIDomainServicesView')
        # Perform control over entities via given request.
        response = await super().post(request, domain, service)

        app_session_id = request.headers.get('X-App-Session-Id')
        LOGGER.debug('app_session_id: %s', app_session_id)
        try:
            app_session_id = uuid.UUID(app_session_id)
        except (TypeError, ValueError):
            return self.json_message(
                'Missing or malformed X-App-Session-Id.',
                HTTPStatus.UNAUTHORIZED,
            )

        await asyncio.sleep(0.5)

        try:
            async with AsyncSessionFactory() as session:
                result = await ha_entity_service.get(session, app_session_id)
        except sqlalchemy.exc.SQLAlchemyError as e:
            LOGGER.error('DomikaAPIDomainServicesView post. Database error. %s', e)
            return self.json_message('Database error.', HTTPStatus.INTERNAL_SERVER_ERROR)
        except Exception as e:
            LOGGER.exception('DomikaAPIDomainServicesView post. Unhandled error. %s', e)
            return self.json_message('Internal error.', HTTPStatus.INTERNAL_SERVER_ERROR)

        data = json.dumps({'entities': result})
        LOGGER.debug('DomikaAPIDomainServicesView data: %s', {'entities': result})
        response.body = data.encode()
        return response
