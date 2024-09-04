# vim: set fileencoding=utf-8
"""
Integration api.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
import uuid
from http import HTTPStatus
from typing import cast

import domika_ha_framework.database.core as database_core
import domika_ha_framework.subscription.flow as subscription_flow
from aiohttp import web
from domika_ha_framework.errors import DomikaFrameworkBaseError
from homeassistant.helpers.http import HomeAssistantView

LOGGER = logging.getLogger(__name__)


class DomikaAPIPushResubscribe(HomeAssistantView):
    """Update subscriptions, set need_push=1 for the given attributes of given entities."""

    url = "/domika/push_resubscribe"
    name = "domika:push-resubscribe"

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
        LOGGER.debug("DomikaAPIPushResubscribe")

        request_dict = await request.json()
        LOGGER.debug("request_dict: %s", request_dict)

        app_session_id = request.headers.get("X-App-Session-Id")
        try:
            app_session_id = uuid.UUID(app_session_id)
        except (TypeError, ValueError):
            return self.json_message(
                "Missing or malformed X-App-Session-Id.",
                HTTPStatus.UNAUTHORIZED,
            )

        subscriptions = cast(dict[str, set[str]], request_dict.get("subscriptions", None))
        if not subscriptions:
            return self.json_message(
                "Missing or malformed subscriptions.",
                HTTPStatus.UNAUTHORIZED,
            )

        try:
            async with database_core.get_session() as session:
                await subscription_flow.resubscribe_push(session, app_session_id, subscriptions)
        except DomikaFrameworkBaseError as e:
            LOGGER.error('Can\'t resubscribe push "%s". Framework error. %s', subscriptions, e)
        except Exception as e:
            LOGGER.exception('Can\'t resubscribe push "%s". Unhandled error. %s', subscriptions, e)

        # TODO: is it OK to send success after failed resubscribe_push?
        data = {"result": "success"}
        LOGGER.debug("DomikaAPIPushResubscribe data: %s", data)

        return self.json(data, HTTPStatus.OK)
