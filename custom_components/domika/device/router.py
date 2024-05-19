# vim: set fileencoding=utf-8
"""
Application device.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import contextlib
import logging
import uuid
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import (
    async_response,
    websocket_command,
)
from homeassistant.core import HomeAssistant

from .. import errors, push_server_errors
from ..const import MAIN_LOGGER_NAME
from ..database.core import AsyncSessionFactory
from .flow import (
    create_push_session,
    need_update_push_token,
    remove_push_session,
    update_app_session_id,
    update_push_token,
    verify_push_session,
)
from .service import delete

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


@websocket_command(
    {
        vol.Required('type'): 'domika/update_app_session',
        vol.Optional('app_session_id'): str,
    },
)
@async_response
async def websocket_domika_update_app_session(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update app session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "update_app_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "update_app_session", data: %s', msg)

    app_session_id: uuid.UUID | None = None
    cm = contextlib.suppress(TypeError)
    with cm:
        app_session_id = uuid.UUID(msg.get('app_session_id'))

    async with AsyncSessionFactory() as session:
        app_session_id = await update_app_session_id(session, app_session_id)

    connection.send_result(msg_id, {'app_session_id': app_session_id})


@websocket_command(
    {
        vol.Required('type'): 'domika/update_push_token',
        vol.Optional('app_session_id'): vol.Coerce(uuid.UUID),
        vol.Required('push_token_hex'): str,
        vol.Required('platform'): vol.Any('ios', 'android', 'huawei'),
        vol.Required('environment'): vol.Any('sandbox', 'production'),
    },
)
@async_response
async def websocket_domika_update_push_token(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update push token request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "update_push_token", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "update_push_token", data: %s', msg)

    app_session_id = cast(uuid.UUID, msg.get('app_session_id'))

    # This method involves http request. We need to assume it may take quite some time.
    # Do we need to make it async with callback somehow?
    event_result: dict[str, Any] | None = None

    result = -1
    async with AsyncSessionFactory() as session:
        try:
            if await need_update_push_token(
                session,
                app_session_id,
                cast(str, msg.get('push_token_hex')),
            ):
                await update_push_token(
                    session,
                    app_session_id,
                    cast(str, msg.get('push_token_hex')),
                )
                result = 2
            else:
                result = 1
                event_result = {
                    'd.type': 'push_activation',
                    'push_activation_success': True,
                }
        except errors.AppSessionIdNotFoundError:
            result = -1
            event_result = {
                'd.type': 'push_activation',
                'invalid_app_session_id': True,
            }
        except (
            push_server_errors.PushSessionIdNotFoundError,
            push_server_errors.UnexpectedServerResponseError,
            push_server_errors.BadRequestError,
        ):
            result = 0
            event_result = {
                'd.type': 'push_activation',
                'push_activation_success': False,
            }

    if event_result:
        LOGGER.debug('### domika_%s, %s', app_session_id, event_result)
        hass.bus.async_fire(f'domika_{app_session_id}', event_result)

    connection.send_result(msg_id, {'result': result})


async def _remove_push_session(app_session_id: uuid.UUID) -> dict:
    result: dict[str, Any] = {}
    async with AsyncSessionFactory() as session:
        try:
            await remove_push_session(session, app_session_id)
            result = {
                'result': 1,
                'text': 'ok',
            }
        except errors.AppSessionIdNotFoundError as e:
            result = {
                'result': 0,
                'text': f'app_session_id "{e.app_session_id}" not found',
            }
        except errors.PushSessionIdNotFoundError as e:
            result = {
                'result': 0,
                'text': f'push_session_id not found for app_session_id "{e.app_session_id}"',
            }
        except push_server_errors.PushSessionIdNotFoundError as e:
            result = {
                'result': 0,
                'text': f'push_session_id "{e.push_session_id}" not found on the push server',
            }
        except push_server_errors.BadRequestError:
            result = {
                'result': 0,
                'text': 'push server respond with bad request',
            }
        except push_server_errors.UnexpectedServerResponseError as e:
            result = {
                'result': 0,
                'text': f'push server unexpected response "{e.status}"',
            }
    return result


@websocket_command(
    {
        vol.Required('type'): 'domika/remove_push_session',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
    },
)
@async_response
async def websocket_domika_remove_push_session(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika remove push session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "remove_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "remove_push_session", data: %s', msg)
    app_session_id = cast(uuid.UUID, msg.get('app_session_id'))
    connection.send_result(msg_id, _remove_push_session(app_session_id))


@websocket_command(
    {
        vol.Required('type'): 'domika/update_push_session',
        vol.Required('original_transaction_id'): str,
        vol.Required('push_token_hex'): str,
        vol.Required('platform'): str,
        vol.Required('environment'): str,
    },
)
@async_response
async def websocket_domika_update_push_session(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update push session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "update_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "update_push_session", data: %s', msg)

    result: dict[str, Any] = {}
    try:
        await create_push_session(
            cast(str, msg.get('original_transaction_id')),
            cast(str, msg.get('push_token_hex')),
            cast(str, msg.get('platform')),
            cast(str, msg.get('environment')),
        )
        result = {
            'result': 1,
            'text': 'ok',
        }
    except ValueError as e:
        result = {
            'result': 0,
            'text': f'{e}',
        }
    except push_server_errors.BadRequestError:
        result = {
            'result': 0,
            'text': 'push server respond with bad request',
        }
    except push_server_errors.UnexpectedServerResponseError as e:
        result = {
            'result': 0,
            'text': f'push server unexpected response "{e.status}"',
        }

    connection.send_result(msg_id, result)


@websocket_command(
    {
        vol.Required('type'): 'domika/remove_app_session',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
    },
)
@async_response
async def websocket_domika_remove_app_session(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika remove app session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "remove_app_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "remove_app_session", data: %s', msg)

    app_session_id = cast(uuid.UUID, msg.get('app_session_id'))
    async with AsyncSessionFactory() as session:
        await delete(session, app_session_id)

    connection.send_result(msg_id, await _remove_push_session(app_session_id))


@websocket_command(
    {
        vol.Required('type'): 'domika/verify_push_session',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
        vol.Required('verification_key'): str,
    },
)
@async_response
async def websocket_domika_verify_push_session(
    _hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika verify push session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "verify_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "verify_push_session", data: %s', msg)

    result: dict[str, Any] = {}
    try:
        async with AsyncSessionFactory() as session:
            await verify_push_session(
                session,
                cast(uuid.UUID, msg.get('app_session_id')),
                cast(str, msg.get('verification_key')),
            )
        result = {
            'result': 1,
            'text': 'ok',
        }
    except ValueError as e:
        result = {
            'result': 0,
            'text': f'{e}',
        }
    except errors.AppSessionIdNotFoundError as e:
        result = {
            'result': 0,
            'text': f'app_session_id "{e.app_session_id}" not found',
        }
    except push_server_errors.BadRequestError:
        result = {
            'result': 0,
            'text': 'push server respond with bad request',
        }
    except push_server_errors.UnexpectedServerResponseError as e:
        result = {
            'result': 0,
            'text': f'push server unexpected response "{e.status}"',
        }
    except push_server_errors.ResponseError as e:
        result = {
            'result': 0,
            'text': f'push server response error "{e}"',
        }

    connection.send_result(msg_id, result)
