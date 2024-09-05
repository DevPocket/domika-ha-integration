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

import domika_ha_framework.database.core as database_core
import domika_ha_framework.push_data.service as push_data_service
from aiohttp import web
from domika_ha_framework.errors import DomikaFrameworkBaseError
from homeassistant.components.api import APIDomainServicesView
from homeassistant.core import async_get_hass
from homeassistant.helpers.json import json_bytes

from ..const import DOMAIN
from ..ha_entity import service as ha_entity_service

LOGGER = logging.getLogger(__name__)


class DomikaAPIDomainServicesView(APIDomainServicesView):
    """View to handle Status requests."""

    url = "/domika/services/{domain}/{service}"
    name = "domika:domain-services"

    async def post(self, request: web.Request, domain: str, service: str) -> web.Response:
        """Retrieve if API is running."""
        # Check that integration still loaded.
        hass = async_get_hass()
        if not hass.data.get(DOMAIN):
            return self.json_message("Route not found.", HTTPStatus.NOT_FOUND)

        LOGGER.debug("DomikaAPIDomainServicesView, domain: %s, service: %s", domain, service)

        # Perform control over entities via given request.
        response = await super().post(request, domain, service)

        app_session_id = request.headers.get("X-App-Session-Id")
        LOGGER.debug("app_session_id: %s", app_session_id)
        try:
            app_session_id = uuid.UUID(app_session_id)
        except (TypeError, ValueError):
            return self.json_message(
                "Missing or malformed X-App-Session-Id.",
                HTTPStatus.UNAUTHORIZED,
            )

        delay = float(request.headers.get("X-Delay", 0.5))
        LOGGER.debug("delay: %s", delay)

        await asyncio.sleep(delay)

        try:
            async with database_core.get_session() as session:
                result = await ha_entity_service.get(session, app_session_id)
                await push_data_service.delete_for_app_session(
                    session,
                    app_session_id=app_session_id,
                )

        except DomikaFrameworkBaseError as e:
            LOGGER.error("DomikaAPIDomainServicesView post. Framework error. %s", e)
            return self.json_message("Framework error.", HTTPStatus.INTERNAL_SERVER_ERROR)
        except Exception as e:
            LOGGER.exception("DomikaAPIDomainServicesView post. Unhandled error. %s", e)
            return self.json_message("Internal error.", HTTPStatus.INTERNAL_SERVER_ERROR)

        LOGGER.debug("DomikaAPIDomainServicesView data: %s", {"entities": result})
        data = json_bytes({"entities": result})
        response.body = data
        return response
