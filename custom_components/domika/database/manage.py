# vim: set fileencoding=utf-8
"""
Database core.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import asyncio

import alembic.command
from alembic.config import Config
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from ..const import ALEMBIC_INI_PATH, DATABASE_URL


def _run_upgrade(connection: Connection, cfg: Config):
    cfg.attributes["connection"] = connection
    cfg.attributes["configure_loggers"] = False
    alembic.command.upgrade(cfg, "head")


async def _migrate():
    alembic_config = Config(ALEMBIC_INI_PATH)
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_run_upgrade, alembic_config)


async def migrate():
    """
    Perform database migration.

    All this strange stuff is made only for one reason - avoid HA warning about synchronous calls.
    Alembic developers do not plan to do true async migrations.
    """
    await asyncio.get_event_loop().run_in_executor(None, lambda: asyncio.run(_migrate()))
