# vim: set fileencoding=utf-8
"""
Push data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid
from collections.abc import Sequence
from dataclasses import asdict

import sqlalchemy
import sqlalchemy.dialects.sqlite as sqlite_dialect
from sqlalchemy.ext.asyncio import AsyncSession

from ..device.models import Device
from .models import DomikaPushDataCreate, DomikaPushDataUpdate, PushData


async def get(
    db_session: AsyncSession,
    id: uuid.UUID,
) -> Sequence[PushData]:
    """Get push data by id."""
    stmt = sqlalchemy.select(PushData).where(PushData.id == id)
    return (await db_session.scalars(stmt)).all()


async def get_by_platform(db_session: AsyncSession, platform: str) -> Sequence[PushData]:
    """Get all push data for given platform."""
    # TODO: add check for elapsed time.
    stmt = sqlalchemy.select(PushData)
    stmt = stmt.join(Device, PushData.app_session_id == Device.app_session_id)
    stmt = stmt.where(Device.platform == platform)
    return (await db_session.scalars(stmt)).all()


async def create(
    db_session: AsyncSession,
    push_data_in: list[DomikaPushDataCreate],
    *,
    commit: bool = True,
) -> Sequence[PushData]:
    """
    Create new push data.

    If already exists updates value and timestamp.
    """
    stmt = sqlite_dialect.insert(PushData)
    stmt = stmt.on_conflict_do_update(
        index_elements=[PushData.app_session_id, PushData.entity_id, PushData.attribute],
        set_={
            'value': stmt.excluded.value,
            'timestamp': stmt.excluded.timestamp,
        },
    )
    stmt = stmt.returning(PushData)
    result = (await db_session.scalars(stmt, [pd.to_dict() for pd in push_data_in])).all()

    if commit:
        await db_session.commit()

    return result


async def update(
    db_session: AsyncSession,
    push_data: PushData,
    push_data_in: DomikaPushDataUpdate,
    *,
    commit: bool = True,
):
    """Update push data."""
    push_data_attrs = push_data.dict()
    update_data = asdict(push_data_in)
    for attr in push_data_attrs:
        if attr in update_data:
            setattr(push_data, attr, update_data[attr])

    if commit:
        await db_session.commit()


async def delete(db_session: AsyncSession, id: uuid.UUID | list[uuid.UUID], *, commit: bool = True):
    """Delete push data by id, or list of id's."""
    if isinstance(id, list):
        stmt = sqlalchemy.delete(PushData).where(PushData.id.in_(id))
    else:
        stmt = sqlalchemy.delete(PushData).where(PushData.id == id)
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()
