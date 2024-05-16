# vim: set fileencoding=utf-8
"""
Database core.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    close_all_sessions,
    create_async_engine,
)

from ..const import DATABASE_URL

ENGINE = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionFactory = async_sessionmaker(ENGINE, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Return async database session."""
    async with AsyncSessionFactory() as session:
        yield session


async def close_db():
    """Close all sessions and dispose database connection pool."""
    await close_all_sessions()
    await ENGINE.dispose()
