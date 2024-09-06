# vim: set fileencoding=utf-8
"""
Application dashboard.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
from typing import Any, cast

import domika_ha_framework.dashboard.service as dashboard_service
import domika_ha_framework.database.core as database_core
import domika_ha_framework.device.service as device_service
import voluptuous as vol
from domika_ha_framework.dashboard.models import DomikaDashboardCreate, DomikaDashboardRead
from domika_ha_framework.errors import DomikaFrameworkBaseError
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)


async def _update_dashboards(
    hass: HomeAssistant,
    dashboards: str,
    hash_: str,
    user_id: str,
):
    try:
        async with database_core.get_session() as session:
            await dashboard_service.create_or_update(
                session,
                DomikaDashboardCreate(
                    dashboards=dashboards,
                    hash=hash_,
                    user_id=user_id,
                ),
            )

            devices = await device_service.get_by_user_id(session, user_id)

        for device in devices:
            hass.bus.async_fire(
                f"domika_{device.app_session_id}",
                {
                    "d.type": "dashboard_update",
                    "hash": hash_,
                },
            )
    except DomikaFrameworkBaseError as e:
        LOGGER.error(
            'Can\'t update dashboards "%s" for user "%s". Framework error. %s',
            dashboards,
            user_id,
            e,
        )
    except Exception as e:
        LOGGER.exception(
            'Can\'t update dashboards "%s" for user "%s". Unhandled error. %s',
            dashboards,
            user_id,
            e,
        )


@websocket_command(
    {
        vol.Required("type"): "domika/update_dashboards",
        vol.Required("dashboards"): str,
        vol.Required("hash"): str,
    },
)
@async_response
async def websocket_domika_update_dashboards(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update dashboards request."""
    msg_id = cast(int, msg.get("id"))
    if not msg_id:
        LOGGER.error('Got websocket message "update_dashboards", msg_id is missing.')
        return

    LOGGER.debug(
        'Got websocket message "update_dashboards", user: "%s", data: %s',
        connection.user.id,
        msg.get("hash"),
    )

    # Fast send reply.
    connection.send_result(msg_id, {"result": "accepted"})
    LOGGER.debug("update_dashboards msg_id=%s data=%s", msg_id, {"result": "accepted"})

    hass.async_create_task(
        _update_dashboards(
            hass,
            cast(str, msg.get("dashboards")),
            cast(str, msg.get("hash")),
            connection.user.id,
        ),
        "update_dashboards",
    )


@websocket_command(
    {
        vol.Required("type"): "domika/get_dashboards",
    },
)
@async_response
async def websocket_domika_get_dashboards(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika get dashboards request."""
    msg_id = cast(int, msg.get("id"))
    if not msg_id:
        LOGGER.error('Got websocket message "get_dashboards", msg_id is missing.')
        return

    LOGGER.debug(
        'Got websocket message "get_dashboards", data: %s, user_id: %s',
        msg,
        connection.user.id,
    )

    dashboards = None
    try:
        async with database_core.get_session() as session:
            dashboards = await dashboard_service.get(session, connection.user.id)
    except DomikaFrameworkBaseError as e:
        LOGGER.error(
            'Can\'t get dashboards for user "%s". Framework error. %s',
            connection.user.id,
            e,
        )
    except Exception as e:
        LOGGER.exception(
            'Can\'t get dashboards for user "%s". Unhandled error. %s',
            connection.user.id,
            e,
        )

    result = (
        DomikaDashboardRead.from_dict(dashboards.dict()).to_dict()
        if dashboards
        else DomikaDashboardRead(dashboards="", hash="").to_dict()
    )

    connection.send_result(msg_id, result)
    LOGGER.debug("update_dashboards msg_id=%s", msg_id)


@websocket_command(
    {
        vol.Required("type"): "domika/get_dashboards_hash",
    },
)
@async_response
async def websocket_domika_get_dashboards_hash(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika get dashboards hash update request."""
    msg_id = cast(int, msg.get("id"))
    if not msg_id:
        LOGGER.error('Got websocket message "get_dashboards_hash", msg_id is missing.')
        return

    LOGGER.debug(
        'Got websocket message "get_dashboards_hash", data: %s, user_id: %s',
        msg,
        connection.user.id,
    )

    dashboards = None
    try:
        async with database_core.get_session() as session:
            dashboards = await dashboard_service.get(session, connection.user.id)
    except DomikaFrameworkBaseError as e:
        LOGGER.error(
            'Can\'t get dashboards hash for user "%s". Framework error. %s',
            connection.user.id,
            e,
        )
    except Exception as e:
        LOGGER.exception(
            'Can\'t get dashboards hash for user "%s". Unhandled error. %s',
            connection.user.id,
            e,
        )

    result = {"hash": dashboards.hash if dashboards else ""}

    connection.send_result(msg_id, result)
    LOGGER.debug("get_dashboards_hash msg_id=%s data=%s", msg_id, result)
