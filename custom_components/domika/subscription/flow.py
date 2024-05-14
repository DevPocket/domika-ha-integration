# vim: set fileencoding=utf-8
"""
Subscription data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .models import DomikaSubscriptionCreate, DomikaSubscriptionUpdate
from .service import create, delete, update_in_place


# TODO: maybe reorganize data so it can support schemas.
async def resubscribe(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    subscriptions: dict[str, set[str]],
):
    """Remove all existing subscriptions, and subscribe to the new subscriptions."""
    await delete(db_session, app_session_id, commit=False)
    for entity, attrs in subscriptions.items():
        for attr in attrs:
            # TODO: create_many
            await create(
                db_session,
                DomikaSubscriptionCreate(
                    app_session_id=app_session_id,
                    entity_id=entity,
                    attribute=attr,
                    need_push=False,
                ),
                commit=False,
            )
    await db_session.commit()


# TODO: maybe reorganize data so it can support schemas.
async def resubscribe_push(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    subscriptions: dict[str, set[str]],
):
    """
    Set need_push for given app_session_id.

    Set need_push to true for given entities attributes, for all other set need_push to false.
    """
    await update_in_place(
        db_session,
        app_session_id,
        entity_id='',
        attribute='',
        subscription_in=DomikaSubscriptionUpdate(need_push=False),
        commit=False,
    )
    for entity, attrs in subscriptions.items():
        for attr in attrs:
            # TODO: update_many
            await update_in_place(
                db_session,
                app_session_id=app_session_id,
                entity_id=entity,
                attribute=attr,
                subscription_in=DomikaSubscriptionUpdate(need_push=True),
                commit=False,
            )
    await db_session.commit()
