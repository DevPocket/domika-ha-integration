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

import sqlalchemy.exc
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
    check_push_token,
    create_push_session,
    remove_push_session,
    update_app_session_id,
    verify_push_session, get_hass_network_properties,
)
from .service import delete

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


@websocket_command(
    {
        vol.Required('type'): 'domika/update_app_session',
        vol.Optional('app_session_id'): str,
        vol.Optional('push_token_hash'): str,
    },
)
@async_response
async def websocket_domika_update_app_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update app session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "update_app_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "update_app_session", data: %s', msg)

    push_token_hash = cast(str, msg.get('push_token_hash') or "")
    app_session_id: uuid.UUID | None = None
    cm = contextlib.suppress(TypeError)
    with cm:
        app_session_id = uuid.UUID(msg.get('app_session_id'))

    async with AsyncSessionFactory() as session:
        app_session_id, old_app_session_ids = await update_app_session_id(session, app_session_id, connection.user.id, push_token_hash)
        LOGGER.info('Successfully updated app session id "%s".', app_session_id)

    result = {
        'app_session_id': app_session_id,
        'old_app_session_ids': old_app_session_ids
    }
    result.update(await get_hass_network_properties(hass))

    connection.send_result(msg_id, result)
    LOGGER.debug('update_app_session msg_id=%s data=%s', msg_id, result)


async def _check_push_token(
    hass: HomeAssistant,
    app_session_id: uuid.UUID,
    platform: str,
    environment: str,
    push_token_hex: str,
):
    event_result: dict[str, Any] | None = None
    try:
        async with AsyncSessionFactory() as session:
            if await check_push_token(
                session,
                app_session_id,
                platform,
                environment,
                push_token_hex,
            ):
                event_result = {
                    'd.type': 'push_activation',
                    'push_activation_success': True,
                }
                LOGGER.info('Push token "%s" check. OK', push_token_hex)
            else:
                LOGGER.info('Push token "%s" check. Need validation', push_token_hex)
    except errors.AppSessionIdNotFoundError:
        LOGGER.error(
            'Can\'t check push token "%s". App session id "%s" not found',
            push_token_hex,
            app_session_id,
        )
        event_result = {
            'd.type': 'push_activation',
            'invalid_app_session_id': True,
        }
    except errors.PushSessionIdNotFoundError:
        LOGGER.info('Can\'t check push token "%s". Missing push session id', push_token_hex)
        event_result = {
            'd.type': 'push_activation',
            'push_activation_success': False,
        }
    except push_server_errors.PushSessionIdNotFoundError as e:
        LOGGER.error('Can\'t check push token "%s". %s', push_token_hex, e)
        event_result = {
            'd.type': 'push_activation',
            'push_activation_success': False,
        }
    except (
        push_server_errors.UnexpectedServerResponseError,
        push_server_errors.BadRequestError,
    ) as e:
        LOGGER.error('Can\'t check push token "%s". Push server error. %s', push_token_hex, e)
        event_result = {
            'd.type': 'push_activation',
            'push_activation_success': False,
        }
    except push_server_errors.PushServerError as e:
        LOGGER.error('Can\'t check push token "%s". Push server error. %s', push_token_hex, e)
    except sqlalchemy.exc.SQLAlchemyError as e:
        LOGGER.error('Can\'t check push token "%s". Database error. %s', push_token_hex, e)
    except Exception as e:
        LOGGER.exception('Can\'t check push token "%s". Unhandled error. %s', push_token_hex, e)

    if event_result:
        LOGGER.debug('### domika_%s, %s', app_session_id, event_result)
        hass.bus.async_fire(f'domika_{app_session_id}', event_result)


@websocket_command(
    {
        vol.Required('type'): 'domika/update_push_token',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
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

    # Fast send reply.
    connection.send_result(msg_id, {'result': 'accepted'})
    LOGGER.debug('update_push_token msg_id=%s data=%s', msg_id, {'result': 'accepted'})

    hass.async_create_task(
        _check_push_token(
            hass,
            cast(uuid.UUID, msg.get('app_session_id')),
            cast(str, msg.get('platform')),
            cast(str, msg.get('environment')),
            cast(str, msg.get('push_token_hex')),
        ),
        'check_push_token',
    )


async def _remove_push_session(app_session_id: uuid.UUID):
    try:
        async with AsyncSessionFactory() as session:
            push_session_id = await remove_push_session(session, app_session_id)
            LOGGER.info('Push session "%s" successfully removed.', push_session_id)
    except errors.AppSessionIdNotFoundError as e:
        LOGGER.info(
            'Can\'t remove push session. Application with id "%s" not found.',
            e.app_session_id,
        )
    except errors.PushSessionIdNotFoundError as e:
        LOGGER.warning(
            "Can't remove push session. "
            'Application with id "%s" has no associated push session id.',
            e.app_session_id,
        )
    except push_server_errors.BadRequestError as e:
        LOGGER.error("Can't remove push session. Push server error. %s. %s", e, e.body)
    except push_server_errors.PushServerError as e:
        LOGGER.error("Can't remove push session. Push server error. %s", e)
    except sqlalchemy.exc.SQLAlchemyError as e:
        LOGGER.error("Can't remove push session. Database error. %s", e)
    except Exception as e:
        LOGGER.exception("Can't remove push session. Unhandled error. %s", e)


@websocket_command(
    {
        vol.Required('type'): 'domika/remove_push_session',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
    },
)
@async_response
async def websocket_domika_remove_push_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika remove push session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "remove_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "remove_push_session", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {'result': 'accepted'})
    LOGGER.debug('remove_push_session msg_id=%s data=%s', msg_id, {'result': 'accepted'})

    hass.async_create_task(
        _remove_push_session(cast(uuid.UUID, msg.get('app_session_id'))),
        'remove_push_session',
    )


async def _create_push_session(
    original_transaction_id: str,
    platform: str,
    environment: str,
    push_token: str,
    app_session_id: str,
):
    try:
        await create_push_session(original_transaction_id, platform, environment, push_token, app_session_id)
        LOGGER.info(
            'Push session creation process successfully initialized. '
            'original_transaction_id="%s", platform="%s", environment="%s", push_token="%s", app_session_id="%s" ',
            original_transaction_id,
            platform,
            environment,
            push_token,
            app_session_id,
        )
    except ValueError as e:
        LOGGER.error(
            "Can't initialize push session creation. "
            'original_transaction_id="%s", platform="%s", environment="%s", push_token="%s", app_session_id="%s" %s',
            original_transaction_id,
            platform,
            environment,
            push_token,
            app_session_id,
            e,
        )
    except push_server_errors.PushServerError as e:
        LOGGER.error(
            "Can't initialize push session creation. "
            'original_transaction_id="%s", platform="%s", environment="%s", push_token="%s", app_session_id="%s" '
            'Push server error. %s',
            original_transaction_id,
            platform,
            environment,
            push_token,
            app_session_id,
            e,
        )
    except Exception as e:
        LOGGER.exception(
            "Can't initialize push session creation. "
            'original_transaction_id="%s", platform="%s", environment="%s", push_token="%s", app_session_id="%s" '
            'Unhandled error. %s',
            original_transaction_id,
            platform,
            environment,
            push_token,
            e,
        )


@websocket_command(
    {
        vol.Required('type'): 'domika/update_push_session',
        vol.Required('original_transaction_id'): str,
        vol.Required('push_token_hex'): str,
        vol.Required('platform'): vol.Any('ios', 'android', 'huawei'),
        vol.Required('environment'): vol.Any('sandbox', 'production'),
        vol.Required('app_session_id'): str,
    },
)
@async_response
async def websocket_domika_update_push_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update push session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "update_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "update_push_session", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {'result': 'accepted'})
    LOGGER.debug('update_push_session msg_id=%s data=%s', msg_id, {'result': 'accepted'})

    hass.async_create_task(
        _create_push_session(
            cast(str, msg.get('original_transaction_id')),
            cast(str, msg.get('platform')),
            cast(str, msg.get('environment')),
            cast(str, msg.get('push_token_hex')),
            cast(str, msg.get('app_session_id')),
        ),
        'create_push_session',
    )


async def _remove_app_session(app_session_id: uuid.UUID):
    try:
        async with AsyncSessionFactory() as session:
            try:
                push_session_id = await remove_push_session(session, app_session_id)
                LOGGER.info(
                    'Push session "%s" for app session "%s" successfully removed.',
                    push_session_id,
                    app_session_id,
                )
            except errors.AppSessionIdNotFoundError as e:
                LOGGER.error(
                    'Can\'t remove app session. Application with id "%s" not found.',
                    e.app_session_id,
                )
                return
            except errors.PushSessionIdNotFoundError:
                pass
            except push_server_errors.BadRequestError as e:
                LOGGER.error(
                    'Can\'t remove push session for app session "%s". Push server error. %s. %s',
                    app_session_id,
                    e,
                    e.body,
                )
            except push_server_errors.PushServerError as e:
                LOGGER.error(
                    'Can\'t remove push session for app session "%s". Push server error. %s',
                    app_session_id,
                    e,
                )

            await delete(session, app_session_id)
            LOGGER.info('App session "%s" successfully removed.', app_session_id)
    except sqlalchemy.exc.SQLAlchemyError as e:
        LOGGER.error("Can't remove app session. Database error. %s", e)
    except Exception as e:
        LOGGER.exception("Can't remove app session. Unhandled error. %s", e)


@websocket_command(
    {
        vol.Required('type'): 'domika/remove_app_session',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
    },
)
@async_response
async def websocket_domika_remove_app_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika remove app session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "remove_app_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "remove_app_session", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {'result': 'accepted'})
    LOGGER.debug('remove_app_session msg_id=%s data=%s', msg_id, {'result': 'accepted'})

    hass.async_create_task(
        _remove_app_session(cast(uuid.UUID, msg.get('app_session_id'))),
        'remove_app_session',
    )


async def _verify_push_session(
    app_session_id: uuid.UUID,
    verification_key: str,
    push_token_hash: str,
):
    try:
        async with AsyncSessionFactory() as session:
            push_session_id = await verify_push_session(session, app_session_id, verification_key, push_token_hash)
        LOGGER.info(
            'Verification key "%s" for application "%s" successfully verified. '
            'New push session id "%s". Push token hash "%s"',
            verification_key,
            app_session_id,
            push_session_id,
            push_token_hash,
        )
    except (ValueError, errors.AppSessionIdNotFoundError) as e:
        LOGGER.error(
            'Can\'t verify verification key "%s" for application "%s". Push token hash "%s". %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
        )
    except push_server_errors.BadRequestError as e:
        LOGGER.error(
            'Can\'t verify verification key "%s" for application "%s". Push server error. Push token hash "%s". %s. %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
            e.body,
        )
    except push_server_errors.PushServerError as e:
        LOGGER.error(
            'Can\'t verify verification key "%s" for application "%s". Push server error. Push token hash "%s". %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
        )
    except sqlalchemy.exc.SQLAlchemyError as e:
        LOGGER.error(
            'Can\'t verify verification key "%s" for application "%s". Database error. Push token hash "%s". %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
        )
    except Exception as e:
        LOGGER.exception(
            'Can\'t verify verification key "%s" for application "%s". Push token hash "%s". Unhandled error. %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
        )


@websocket_command(
    {
        vol.Required('type'): 'domika/verify_push_session',
        vol.Required('app_session_id'): vol.Coerce(uuid.UUID),
        vol.Required('verification_key'): str,
        vol.Optional('push_token_hash'): str,
    },
)
@async_response
async def websocket_domika_verify_push_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika verify push session request."""
    msg_id = cast(int, msg.get('id'))
    if not msg_id:
        LOGGER.error('Got websocket message "verify_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "verify_push_session", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {'result': 'accepted'})
    LOGGER.debug('verify_push_session msg_id=%s data=%s', msg_id, {'result': 'accepted'})

    hass.async_create_task(
        _verify_push_session(
            cast(uuid.UUID, msg.get('app_session_id')),
            cast(str, msg.get('verification_key')),
            cast(str, msg.get('push_token_hash') or ""),
        ),
        'verify_push_session',
    )
