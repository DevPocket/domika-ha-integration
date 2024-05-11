# vim: set fileencoding=utf-8
"""
Application dashboard.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from dataclasses import asdict

import sqlalchemy
import sqlalchemy.dialects.sqlite as sqlite_dialect
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Dashboard, DomikaDashboardCreate, DomikaDashoardUpdate


async def get(db_session: AsyncSession, user_id: str) -> Dashboard | None:
    """Get dashboard by user id."""
    stmt = sqlalchemy.select(Dashboard).where(Dashboard.user_id == user_id)
    return await db_session.scalar(stmt)


async def create(
    db_session: AsyncSession,
    dashboard_in: DomikaDashboardCreate,
    *,
    commit: bool = True,
) -> Dashboard | None:
    """Create new dashboard."""
    stmt = sqlite_dialect.insert(Dashboard)
    stmt = stmt.values(**dashboard_in.to_dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[Dashboard.user_id],
        set_={
            'dashboard': stmt.excluded.dashboard,
        },
    )
    stmt = stmt.returning(Dashboard)
    result = await db_session.scalar(stmt)

    if commit:
        await db_session.commit()

    return result


async def update(
    db_session: AsyncSession,
    dashboard: Dashboard,
    dashboard_in: DomikaDashoardUpdate,
    *,
    commit: bool = True,
):
    """Update dashboard."""
    dashboard_attrs = dashboard.dict()
    update_data = asdict(dashboard_in)
    for attr in dashboard_attrs:
        if attr in update_data:
            setattr(dashboard, attr, update_data[attr])

    if commit:
        await db_session.commit()


async def delete(db_session: AsyncSession, user_id: str, *, commit: bool = True):
    """Delete dashboard."""
    stmt = sqlalchemy.delete(Dashboard).where(Dashboard.user_id == user_id)
    await db_session.execute(stmt)

    if commit:
        await db_session.commit()
