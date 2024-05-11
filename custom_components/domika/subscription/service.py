# vim: set fileencoding=utf-8
"""
Subscription data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from collections.abc import Sequence
from dataclasses import asdict

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DomikaSubscriptionCreate, DomikaSubscriptionUpdate, Subscription


async def get(
    db_session: AsyncSession,
    app_session_id: str,
    *,
    need_push: bool = True,
) -> Sequence[Subscription]:
    """
    Get all subscriptions by application sesison id.

    Subscriptions filtered by need_push flag.
    """
    stmt = sqlalchemy.select(Subscription).where(
        Subscription.app_session_id == app_session_id,
        Subscription.need_push == need_push,
    )
    return (await db_session.scalars(stmt)).all()


async def get_by_attributes(
    db_session: AsyncSession,
    entity_id: str,
    attributes: list[str],
) -> Sequence[Subscription]:
    """Get all subscriptions with given entity_id that contains attribute from attributes."""
    stmt = sqlalchemy.select(Subscription).where(
        Subscription.entity_id == entity_id,
        Subscription.attribute.in_(attributes),
    )
    return (await db_session.scalars(stmt)).all()


async def create(
    db_session: AsyncSession,
    subscription_in: DomikaSubscriptionCreate,
    *,
    commit: bool = True,
):
    """Create new subscription."""
    subscription = Subscription(**subscription_in.to_dict())
    db_session.add(subscription)
    await db_session.flush()
    if commit:
        await db_session.commit()


async def update(
    db_session: AsyncSession,
    subscription: Subscription,
    subscription_in: DomikaSubscriptionUpdate,
    *,
    commit: bool = True,
):
    """Update subscription."""
    subscription_attrs = subscription.dict()
    update_data = asdict(subscription_in)
    for attr in subscription_attrs:
        if attr in update_data:
            setattr(subscription, attr, update_data[attr])

    if commit:
        await db_session.commit()


async def update_in_place(
    db_session: AsyncSession,
    app_session_id: str,
    entity_id: str,
    attribute: str,
    subscription_in: DomikaSubscriptionUpdate,
    *,
    commit: bool = True,
):
    """Update subscription in place."""
    stmt = sqlalchemy.update(Subscription)
    stmt = stmt.where(Subscription.app_session_id == app_session_id)
    if entity_id:
        stmt = stmt.where(Subscription.entity_id == entity_id)
    if attribute:
        stmt = stmt.where(Subscription.attribute == attribute)
    stmt = stmt.values(**asdict(subscription_in))
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()


async def delete(db_session: AsyncSession, app_session_id: str, *, commit: bool = True):
    """Delete subscription."""
    stmt = sqlalchemy.delete(Subscription).where(Subscription.app_session_id == app_session_id)
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()
