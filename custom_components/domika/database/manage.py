# vim: set fileencoding=utf-8
"""
Database core.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import alembic.command
from alembic.config import Config
from sqlalchemy import Connection

from ..const import ALEMBIC_INI_PATH
from .core import ENGINE


def _run_upgrade(connection: Connection, cfg: Config):
    cfg.attributes['connection'] = connection
    cfg.attributes['configure_loggers'] = False
    alembic.command.upgrade(cfg, 'head')


async def migrate():
    """Perform database migration."""
    alembic_config = Config(ALEMBIC_INI_PATH)
    async with ENGINE.begin() as conn:
        await conn.run_sync(_run_upgrade, alembic_config)
