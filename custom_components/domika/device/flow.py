# vim: set fileencoding=utf-8
"""
Application device.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import json
import logging
import uuid

import aiohttp
import sqlalchemy
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from .. import errors, push_server_errors, statuses
from ..const import MAIN_LOGGER_NAME, PUSH_SERVER_TIMEOUT, PUSH_SERVER_URL
from .models import Device, DomikaDeviceCreate, DomikaDeviceUpdate
from .service import create, get, update

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


async def update_app_session_id(
    db_session: AsyncSession,
    app_session_id: uuid.UUID | None,
    user_id: str,
) -> uuid.UUID:
    """
    Update or create app session id.

    If the session exists - updates its last_update and returns its id. Otherwise, it creates a new
    session and returns its id.

    Args:
        db_session: sqlalchemy session.
        app_session_id: Application session id.
        user_id: homeassistant user id.

    Returns:
        If the session exists - returns app_session_id. Otherwise, returns newly created session id.
    """
    result: uuid.UUID | None = None

    if app_session_id:
        # Try to find the proper record.
        device = await get(db_session, app_session_id=app_session_id)

        if device and device.user_id == user_id:
            # If found and user_id matches - update last_update.
            result = device.app_session_id
            stmt = sqlalchemy.update(Device)
            stmt = stmt.where(Device.app_session_id == result)
            stmt = stmt.values(last_update=func.datetime('now'))
            await db_session.execute(stmt)
            await db_session.commit()

    if not result:
        # If not found - create new one.
        device = await create(
            db_session,
            DomikaDeviceCreate(
                app_session_id=uuid.uuid4(),
                user_id=user_id,
                push_session_id=None,
                push_token='',
                platform='',
                environment='',
            ),
        )
        result = device.app_session_id

    return result


async def check_push_token(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    platform: str,
    environment: str,
    push_token: str,
) -> bool:
    """
    Check that push session is exists, and associated push token does not changed.

    If push session id is not found on push server - it will be implicitly deleted for device with
    given app_session_id.

    Args:
        db_session: sqlalchemy session.
        app_session_id: application session id.
        platform: application platform.
        environment: application environment.
        push_token: application push token.

    Returns:
        bool: True if push_token do not need to be updated, False otherwise.

    Raises:
        errors.AppSessionIdNotFoundError: if app session not found.
        errors.PushSessionIdNotFoundError: if push_session_id not set for device.
        push_server_errors.PushSessionIdNotFoundError: if push session id not found on the push
            server, or triplet x-session-id/platform/environment do not match.
        push_server_errors.BadRequestError: if push server response with bad request.
        push_server_errors.UnexpectedServerResponseError: if push server response with unexpected
        status.
    """
    device = await get(db_session, app_session_id)
    if not device:
        raise errors.AppSessionIdNotFoundError(app_session_id)

    push_session_id = device.push_session_id
    if not push_session_id:
        raise errors.PushSessionIdNotFoundError(app_session_id)

    try:
        async with (
            aiohttp.ClientSession(json_serialize=json.dumps) as session,
            session.post(
                f'{PUSH_SERVER_URL}/push_session/check',
                headers={
                    # TODO: rename to x-push-session-id
                    'x-session-id': str(push_session_id),
                },
                json={
                    'push_token': push_token,
                    'platform': platform,
                    'environment': environment,
                },
                timeout=PUSH_SERVER_TIMEOUT,
            ) as resp,
        ):
            if resp.status == statuses.HTTP_204_NO_CONTENT:
                return True

            if resp.status == statuses.HTTP_202_ACCEPTED:
                # Push server push token differs from the given one. Push server send verification
                # key to the application. No need to remove current push session due to application
                # can ignore verification key.
                return False

            if resp.status in (statuses.HTTP_401_UNAUTHORIZED, statuses.HTTP_404_NOT_FOUND):
                # Push server can't find push session with given triplet x-session-id/platform/
                # environment. Or even can't find push session at all.
                # Need to remove current push session.
                LOGGER.info(
                    'The server rejected push session id "%s"',
                    push_session_id,
                )
                await update(db_session, device, DomikaDeviceUpdate(push_session_id=None))
                LOGGER.info(
                    'Push session "%s" for app session "%s" successfully removed',
                    push_session_id,
                    app_session_id,
                )
                raise push_server_errors.PushSessionIdNotFoundError(push_session_id)

            if resp.status == statuses.HTTP_400_BAD_REQUEST:
                raise push_server_errors.BadRequestError(await resp.json())

            raise push_server_errors.UnexpectedServerResponseError(resp.status)
    except aiohttp.ClientError as e:
        raise push_server_errors.PushServerError(str(e)) from None


async def remove_push_session(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
) -> uuid.UUID:
    """
    Remove push session from push server.

    Args:
        db_session: sqlalchemy session.
        app_session_id: application session id.

    Raises:
        errors.AppSessionIdNotFoundError: if app session not found.
        errors.PushSessionIdNotFoundError: if push session id not found on the integration.
        push_server_errors.PushSessionIdNotFoundError: if push session id not found on the push
        server.
        push_server_errors.BadRequestError: if push server response with bad request.
        push_server_errors.UnexpectedServerResponseError: if push server response with unexpected
        status.
    """
    device = await get(db_session, app_session_id)
    if not device:
        raise errors.AppSessionIdNotFoundError(app_session_id)

    if not device.push_session_id:
        raise errors.PushSessionIdNotFoundError(app_session_id)
    push_session_id = device.push_session_id

    try:
        await update(db_session, device, DomikaDeviceUpdate(push_session_id=None))
        async with (
            aiohttp.ClientSession(json_serialize=json.dumps) as session,
            session.delete(
                f'{PUSH_SERVER_URL}/push_session',
                headers={
                    # TODO: rename to x-push-session-id
                    'x-session-id': str(push_session_id),
                },
                timeout=PUSH_SERVER_TIMEOUT,
            ) as resp,
        ):
            if resp.status == statuses.HTTP_204_NO_CONTENT:
                return push_session_id

            if resp.status == statuses.HTTP_400_BAD_REQUEST:
                raise push_server_errors.BadRequestError(await resp.json())

            if resp.status == statuses.HTTP_401_UNAUTHORIZED:
                raise push_server_errors.PushSessionIdNotFoundError(push_session_id)

            raise push_server_errors.UnexpectedServerResponseError(resp.status)
    except aiohttp.ClientError as e:
        raise push_server_errors.PushServerError(str(e)) from None


async def create_push_session(
    original_transaction_id: str,
    platform: str,
    environment: str,
    push_token: str,
    app_session_id: str,
):
    """
    Initialize push session creation flow on the push server.

    Args:
        original_transaction_id: original transaction id from the application.
        platform: application platform.
        environment: application environment.
        push_token: application push token.
        app_session_id: application push session id.

    Raises:
        ValueError: if original_transaction_id, push_token, platform or environment is empty.
        push_server_errors.BadRequestError: if push server response with bad request.
        push_server_errors.UnexpectedServerResponseError: if push server response with unexpected
        status.
    """
    if not (original_transaction_id and push_token and platform and environment and app_session_id):
        msg = 'One of the parameters is missing'
        raise ValueError(msg)

    try:
        async with (
            aiohttp.ClientSession(json_serialize=json.dumps) as session,
            session.post(
                f'{PUSH_SERVER_URL}/push_session/create',
                json={
                    'original_transaction_id': original_transaction_id,
                    'platform': platform,
                    'environment': environment,
                    'push_token': push_token,
                    'app_session_id': app_session_id,
                },
                timeout=PUSH_SERVER_TIMEOUT,
            ) as resp,
        ):
            if resp.status == statuses.HTTP_202_ACCEPTED:
                return

            if resp.status == statuses.HTTP_400_BAD_REQUEST:
                raise push_server_errors.BadRequestError(await resp.json())

            raise push_server_errors.UnexpectedServerResponseError(resp.status)
    except aiohttp.ClientError as e:
        raise push_server_errors.PushServerError(str(e)) from None


async def verify_push_session(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    verification_key: str,
) -> uuid.UUID:
    """
    Finishes push session generation.

    After successfull generation store new push session id for device with given app_session_id.

    Args:
        db_session: sqlalchemy session.
        app_session_id: application session id.
        verification_key: verification key.

    Raises:
        ValueError: if verification_key is empty.
        errors.AppSessionIdNotFoundError: if app session not found.
        push_server_errors.BadRequestError: if push server response with bad request.
        push_server_errors.UnexpectedServerResponseError: if push server response with unexpected
        status.
        push_server_errors.ResponseError: if push server response with malformed data.
    """
    if not verification_key:
        msg = 'One of the parameters is missing'
        raise ValueError(msg)

    device = await get(db_session, app_session_id)
    if not device:
        raise errors.AppSessionIdNotFoundError(app_session_id)

    try:
        async with (
            aiohttp.ClientSession(json_serialize=json.dumps) as session,
            session.post(
                f'{PUSH_SERVER_URL}/push_session/verify',
                json={
                    'verification_key': verification_key,
                },
                timeout=PUSH_SERVER_TIMEOUT,
            ) as resp,
        ):
            if resp.status == statuses.HTTP_201_CREATED:
                try:
                    body = await resp.json()
                    push_session_id = uuid.UUID(body.get('push_session_id'))
                except json.JSONDecodeError as e:
                    raise push_server_errors.ResponseError(e) from None
                except ValueError:
                    msg = 'Malformed push_session_id.'
                    raise push_server_errors.ResponseError(msg) from None
                await update(
                    db_session,
                    device,
                    DomikaDeviceUpdate(push_session_id=push_session_id),
                )
                return push_session_id

            if resp.status == statuses.HTTP_400_BAD_REQUEST:
                raise push_server_errors.BadRequestError(await resp.json())

            if resp.status == statuses.HTTP_409_CONFLICT:
                raise push_server_errors.InvalidVerificationKeyError()

            raise push_server_errors.UnexpectedServerResponseError(resp.status)
    except aiohttp.ClientError as e:
        raise push_server_errors.PushServerError(str(e)) from None
