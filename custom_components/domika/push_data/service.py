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
from ..subscription.models import Subscription
from .models import DomikaPushDataCreate, DomikaPushDataUpdate, PushData, _Event


async def get(
    db_session: AsyncSession,
    event_id: uuid.UUID,
) -> Sequence[PushData]:
    """Get push data by id."""
    stmt = sqlalchemy.select(PushData).where(PushData.event_id == event_id)
    return (await db_session.scalars(stmt)).all()


async def get_by_platform(
    db_session: AsyncSession,
    platform: str,
) -> Sequence[PushData]:
    """
    Get all push data for given platform.

    If there are more than one event for the app_session_id/entity_id/attribute binding, returns
    last one.
    """
    # TODO: add check for elapsed time.
    stmt = sqlalchemy.select(PushData)
    stmt = stmt.join(Device, PushData.app_session_id == Device.app_session_id)
    stmt = stmt.where(Device.platform == platform)
    stmt = stmt.group_by(
        PushData.app_session_id,
        PushData.entity_id,
        PushData.attribute,
    )
    stmt = stmt.having(PushData.timestamp == sqlalchemy.func.max(PushData.timestamp))
    return (await db_session.scalars(stmt)).all()


async def create(
    db_session: AsyncSession,
    push_data_in: list[DomikaPushDataCreate],
    *,
    commit: bool = True,
    returning: bool = False,
) -> Sequence[PushData]:
    """
    Create new push data.

    If already exists updates value and timestamp.
    """
    result: Sequence[PushData] = []

    # Insert temporary homeassistant events.
    await db_session.execute(
        sqlalchemy.insert(_Event),
        [pd.to_dict() for pd in push_data_in],
    )

    # Select events which need to be pushed.
    sel = sqlalchemy.select(
        _Event.event_id,
        Subscription.app_session_id,
        _Event.entity_id,
        _Event.attribute,
        _Event.value,
        _Event.context_id,
        _Event.timestamp,
    )
    sel = sel.join(
        Subscription,
        (Subscription.entity_id == _Event.entity_id) & (Subscription.attribute == _Event.attribute),
    )
    sel = sel.where(
        Subscription.need_push.is_(True),
    )

    # Insert events that need to be pushed.
    stmt = sqlite_dialect.insert(PushData)
    stmt = stmt.from_select(
        [
            _Event.event_id,
            Subscription.app_session_id,
            _Event.entity_id,
            _Event.attribute,
            _Event.value,
            _Event.context_id,
            _Event.timestamp,
        ],
        sel,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            PushData.event_id,
            PushData.app_session_id,
            PushData.entity_id,
            PushData.attribute,
        ],
        set_={
            'value': stmt.excluded.value,
            'timestamp': stmt.excluded.timestamp,
        },
    )
    if returning:
        stmt = stmt.returning(PushData)
        result = (await db_session.scalars(stmt)).all()
    else:
        await db_session.execute(stmt)

    # Remove temporary events.
    del_ = sqlalchemy.delete(_Event)
    await db_session.execute(del_)

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


async def delete(
    db_session: AsyncSession,
    event_id: uuid.UUID | list[uuid.UUID],
    *,
    commit: bool = True,
):
    """Delete push data by event id, or list of event id's."""
    if isinstance(event_id, list):
        stmt = sqlalchemy.delete(PushData).where(PushData.event_id.in_(event_id))
    else:
        stmt = sqlalchemy.delete(PushData).where(PushData.event_id == event_id)
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()
