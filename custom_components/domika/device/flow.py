# vim: set fileencoding=utf-8
"""
Application device.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import json
import uuid

import aiohttp
import sqlalchemy
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from .. import errors, push_server_errors, statuses
from ..const import PUSH_SERVER_URL
from .models import Device, DomikaDeviceCreate, DomikaDeviceUpdate
from .service import create, get, update, update_in_place


async def update_app_session_id(
    db_session: AsyncSession,
    app_session_id: uuid.UUID | None,
) -> uuid.UUID:
    """
    Update or create app session id.

    If the session exists - updates its last_update and returns its id. Otherwise it creates a new
    session and returns its id.

    Args:
        db_session: sqlalchemy session.
        app_session_id: Application session id.

    Returns:
        If the session exists - returns app_session_id. Otherwise returns newly created session id.
    """
    result: uuid.UUID | None = None

    if app_session_id:
        # Try to find the proper record.
        device = await get(db_session, app_session_id=app_session_id)

        if device:
            # If found - update last_update.
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
                push_session_id=None,
                push_token='',
                platform='',
                environment='',
            ),
        )
        result = device.app_session_id

    return result


async def need_update_push_token(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    push_token: str,
) -> bool:
    """
    Check that push session is exists, and associated push token does not changed.

    Args:
        db_session: sqlalchemy session.
        app_session_id: application session id.
        push_token: device push token.

    Returns:
        bool: True if push_token need to be updated, False otherwise.

    Raises:
        errors.AppSessionIdNotFoundError: if app session not found.
        push_server_errors.PushSessionIdNotFoundError: if push session id not found on the push
        server.
        push_server_errors.BadRequestError: if push server response with bad request.
        push_server_errors.UnexpectedServerResponseError: if push server response with unexpected
        status.
    """
    device = await get(db_session, app_session_id)
    if not device:
        raise errors.AppSessionIdNotFoundError(app_session_id)

    headers = {}
    # TODO: Is it really need here?
    if device.push_session_id:
        headers = {
            # TODO: rename to x-push-session-id
            'x-session-id': str(device.push_session_id),
        }

    async with (
        aiohttp.ClientSession(json_serialize=json.dumps) as session,
        session.post(
            f'{PUSH_SERVER_URL}/push_session/check',
            json={
                'push_token': push_token,
            },
            headers=headers,
            timeout=10,
        ) as resp,
    ):
        if resp.status == statuses.HTTP_200_OK:
            return False

        if resp.status == statuses.HTTP_409_CONFLICT:
            # Current push token conflicts with the given one.
            return True

        if resp.status == statuses.HTTP_400_BAD_REQUEST:
            raise push_server_errors.BadRequestError(await resp.json())

        if resp.status == statuses.HTTP_401_UNAUTHORIZED:
            raise push_server_errors.PushSessionIdNotFoundError(device.push_session_id)

        raise push_server_errors.UnexpectedServerResponseError(resp.status)


async def update_push_token(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    push_token: str,
    platform: str,
    environment: str,
) -> None:
    """
    Start push token update flow.

    Args:
        db_session: sqlalchemy session.
        app_session_id: application session id.
        push_token: device push token.
        platform: application platform,
        environment: application environment,

    Raises:
        errors.AppSessionIdNotFoundError: if app session not found.
        push_server_errors.PushSessionIdNotFoundError: if push session id not found on the push
        server.
        push_server_errors.BadRequestError: if push server response with bad request.
        push_server_errors.UnexpectedServerResponseError: if push server response with unexpected
        status.
    """
    device = await get(db_session, app_session_id)
    if not device:
        raise errors.AppSessionIdNotFoundError(app_session_id)

    await update(
        db_session,
        device,
        DomikaDeviceUpdate(
            push_token=push_token,
            platform=platform,
            environment=environment,
        ),
    )

    async with (
        aiohttp.ClientSession(json_serialize=json.dumps) as session,
        session.post(
            f'{PUSH_SERVER_URL}/push_session/update',
            json={
                'push_token': push_token,
            },
            headers={
                # TODO: rename to x-push-session-id
                'x-session-id': str(device.push_session_id),
            },
        ) as resp,
    ):
        if resp.status in {statuses.HTTP_200_OK, statuses.HTTP_202_ACCEPTED}:
            return

        if resp.status == statuses.HTTP_400_BAD_REQUEST:
            raise push_server_errors.BadRequestError(await resp.json())

        if resp.status == statuses.HTTP_401_UNAUTHORIZED:
            raise push_server_errors.PushSessionIdNotFoundError(device.push_session_id)

        raise push_server_errors.UnexpectedServerResponseError(resp.status)


async def remove_push_session(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
):
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

    await update(db_session, device, DomikaDeviceUpdate(push_session_id=None))
    async with (
        aiohttp.ClientSession(json_serialize=json.dumps) as session,
        session.post(
            f'{PUSH_SERVER_URL}/push_session/remove',
            headers={
                # TODO: rename to x-push-session-id
                'x-session-id': str(device.push_session_id),
            },
        ) as resp,
    ):
        if resp.status == statuses.HTTP_200_OK:
            return

        if resp.status == statuses.HTTP_401_UNAUTHORIZED:
            raise push_server_errors.PushSessionIdNotFoundError(device.push_session_id)

        raise push_server_errors.UnexpectedServerResponseError(resp.status)


async def create_push_session(
    original_transaction_id: str,
    platform: str,
    environment: str,
    push_token: str,
):
    """
    Initialize push session creation flow on the push server.

    Args:
        original_transaction_id: original transaction id from the application.
        platform: application platform.
        environment: application environment.
        push_token: application push token.

    Raises:
        ValueError: if original_transaction_id, push_token, platform or environment is empty.
        push_server_errors.BadRequestError: if push server response with bad request.
        push_server_errors.UnexpectedServerResponseError: if push server response with unexpected
        status.
    """
    if not (original_transaction_id and push_token and platform and environment):
        msg = 'one of the parameters is missing'
        raise ValueError(msg)

    async with (
        aiohttp.ClientSession(json_serialize=json.dumps) as session,
        session.post(
            f'{PUSH_SERVER_URL}/push_session/create',
            json={
                'original_transaction_id': original_transaction_id,
                'platform': platform,
                'environment': environment,
                'push_token': push_token,
            },
        ) as resp,
    ):
        if resp.status == statuses.HTTP_202_ACCEPTED:
            return

        if resp.status == statuses.HTTP_400_BAD_REQUEST:
            raise push_server_errors.BadRequestError(await resp.json())

        raise push_server_errors.UnexpectedServerResponseError(resp.status)


async def _update_push_session(push_session_id: uuid.UUID, verification_key: str):
    async with (
        aiohttp.ClientSession(json_serialize=json.dumps) as session,
        session.post(
            f'{PUSH_SERVER_URL}/push_session/update/verification_key/verify',
            headers={
                # TODO: rename to x-push-session-id
                'x-session-id': str(push_session_id),
            },
            json={
                'verification_key': verification_key,
            },
        ) as resp,
    ):
        if resp.status == statuses.HTTP_200_OK:
            return

        if resp.status == statuses.HTTP_400_BAD_REQUEST:
            raise push_server_errors.BadRequestError(await resp.json())

        raise push_server_errors.UnexpectedServerResponseError(resp.status)


async def _create_push_session(verification_key: str) -> uuid.UUID:
    async with (
        aiohttp.ClientSession(json_serialize=json.dumps) as session,
        session.post(
            f'{PUSH_SERVER_URL}/push_session/create/verification_key/verify',
            json={
                'verification_key': verification_key,
            },
        ) as resp,
    ):
        if resp.status == statuses.HTTP_201_CREATED:
            try:
                body = await resp.json()
                result = uuid.UUID(body.get('push_session_id'))
            except json.JSONDecodeError as e:
                raise push_server_errors.ResponseError(e) from None
            except ValueError:
                msg = 'Malformed push_session_id.'
                raise push_server_errors.ResponseError(msg) from None
            return result

        if resp.status == statuses.HTTP_400_BAD_REQUEST:
            raise push_server_errors.BadRequestError(await resp.json())

        raise push_server_errors.UnexpectedServerResponseError(resp.status)


async def verify_push_session(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    verification_key: str,
):
    """
    Finishes push session generation.

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
        msg = 'one of the parameters is missing'
        raise ValueError(msg)

    device = await get(db_session, app_session_id)
    if not device:
        raise errors.AppSessionIdNotFoundError(app_session_id)

    if device.push_session_id:
        await _update_push_session(device.push_session_id, verification_key)
    else:
        await update(
            db_session,
            device,
            DomikaDeviceUpdate(
                push_session_id=await _create_push_session(verification_key),
            ),
        )
