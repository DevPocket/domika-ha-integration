# vim: set fileencoding=utf-8
"""
Application dashboard.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant

from ..const import MAIN_LOGGER_NAME
from ..database.core import AsyncSessionFactory
from ..device import service as device_service
from .models import DomikaDashboardCreate, DomikaDashboardRead
from .service import create_or_update, get

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


@websocket_command(
    {
        vol.Required('type'): 'domika/update_dashboards',
        vol.Required('dashboards'): str,
        vol.Required('hash'): str,
    },
)
@async_response
async def websocket_domika_update_dashboards(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update dashboards request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "update_dashboards", msg_id is missing.')
        return

    LOGGER.debug(
        'Got websocket message "update_dashboards", user: "%s", data: %s',
        connection.user.id,
        msg,
    )

    hash_ = cast(str, msg.get('hash'))  # Required in command schema.
    async with AsyncSessionFactory() as session:
        await create_or_update(
            session,
            DomikaDashboardCreate(
                dashboards=cast(str, msg.get('dashboards')),  # Required in command schema.
                hash=hash_,
                user_id=connection.user.id,
            ),
        )

        devices = await device_service.get_by_user_id(session, connection.user.id)

    for device in devices:
        LOGGER.debug('### domika_%s, dashboard_update', device.app_session_id)
        hass.bus.async_fire(
            f'domika_{device.app_session_id}',
            {
                'd.type': 'dashboard_update',
                'hash': hash_,
            },
        )

    connection.send_result(
        msg_id,
        {},
    )


@websocket_command(
    {
        vol.Required('type'): 'domika/get_dashboards',
    },
)
@async_response
async def websocket_domika_get_dashboards(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika get dashboards request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "get_dashboards", msg_id is missing.')
        return

    LOGGER.debug(
        'Got websocket message "get_dashboards", data: %s, user_id: %s',
        msg,
        connection.user.id,
    )
    async with AsyncSessionFactory() as session:
        dashboards = await get(session, connection.user.id)

    # LOGGER.debug('>>> %s', dashboards.dict() if dashboards else '')

    # TODO: it is better to return None if there are no dashboards found.
    connection.send_result(
        msg_id,
        DomikaDashboardRead.from_dict(dashboards.dict()).to_dict()
        if dashboards
        else DomikaDashboardRead(dashboards='', hash=''),
    )
