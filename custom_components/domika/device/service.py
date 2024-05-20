# vim: set fileencoding=utf-8
"""
Application device.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid

import sqlalchemy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Device, DomikaDeviceCreate, DomikaDeviceUpdate


async def get(db_session: AsyncSession, app_session_id: uuid.UUID) -> Device | None:
    """Get device by application sesison id."""
    stmt = select(Device).where(Device.app_session_id == app_session_id)
    return await db_session.scalar(stmt)


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


async def delete(db_session: AsyncSession, app_session_id: uuid.UUID, *, commit: bool = True):
    """Delete device."""
    stmt = sqlalchemy.delete(Device).where(Device.app_session_id == app_session_id)
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()
