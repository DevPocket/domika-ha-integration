# vim: set fileencoding=utf-8
"""
Domika integration.

Active tasks registery.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import asyncio
import enum


class BackgroundTask(enum.StrEnum):
    """Persist tasks types."""

    EVENT_PUSHER = "event_pusher"


BACKGROUND_TASKS: dict[BackgroundTask, asyncio.Task] = {}
WORKER_TASKS: list[asyncio.Task] = []
