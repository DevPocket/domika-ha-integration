# vim: set fileencoding=utf-8
"""
Application device.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid
from typing import Sequence

import sqlalchemy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Device, DomikaDeviceCreate, DomikaDeviceUpdate


async def get(db_session: AsyncSession, app_session_id: uuid.UUID) -> Device | None:
    """Get device by application sesison id."""
    stmt = select(Device).where(Device.app_session_id == app_session_id)
    return await db_session.scalar(stmt)


async def get_all_with_push_session_id(db_session: AsyncSession) -> Sequence[Device]:
    """Get device by application sesison id."""
    stmt = select(Device).where(Device.push_session_id.is_not(None))
    return (await db_session.scalars(stmt)).all()


async def get_by_user_id(db_session: AsyncSession, user_id: str) -> Sequence[Device]:
    """Get device by user id."""
    stmt = select(Device).where(Device.user_id == user_id)
    return (await db_session.scalars(stmt)).all()


async def get_all_with_push_token_hash(db_session: AsyncSession, push_token_hash: str) -> [Device]:
    stmt = select(Device).where(Device.push_token_hash == push_token_hash)
    return (await db_session.scalars(stmt)).all()


async def remove_all_with_push_token_hash(
    db_session: AsyncSession,
    push_token_hash: str,
    device: Device,
    *,
    commit: bool = True,
):
    """Remove all devices with the given push_token_hash."""
    stmt = sqlalchemy.delete(Device).where(Device.push_token_hash == push_token_hash).where(Device.app_session_id != device.app_session_id)
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()


async def create(
    db_session: AsyncSession,
    device_in: DomikaDeviceCreate,
    *,
    commit: bool = True,
) -> Device:
    """Create new device."""
    device = Device(**device_in.to_dict())
    db_session.add(device)
    await db_session.flush()

    if commit:
        await db_session.commit()

    return device


async def update(
    db_session: AsyncSession,
    device: Device,
    device_in: DomikaDeviceUpdate,
    *,
    commit: bool = True,
) -> Device:
    """Update device model."""
    device_data = device.dict()
    update_data = device_in.to_dict()

    for field in device_data:
        if field in update_data:
            setattr(device, field, update_data[field])

    if commit:
        await db_session.commit()

    return device


async def update_in_place(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    device_in: DomikaDeviceUpdate,
    *,
    commit: bool = True,
):
    """Update device in place."""
    stmt = sqlalchemy.update(Device)
    stmt = stmt.where(Device.app_session_id == app_session_id)
    stmt = stmt.values(**device_in.to_dict())
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()


async def delete(db_session: AsyncSession, app_session_id: uuid.UUID, *, commit: bool = True):
    """Delete device."""
    stmt = sqlalchemy.delete(Device).where(Device.app_session_id == app_session_id)
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()
