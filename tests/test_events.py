"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""
from __future__ import annotations
import os
import uuid

os.environ['DOMIKA_DEBUG'] = "1"
os.environ[
    'DOMIKA_DATABASE_URL'] = "sqlite+aiosqlite:///Domika.db"
os.environ['DOMIKA_PUSH_SERVER_URL'] = "http://159.203.109.27:8000/api/v1"
os.environ['DOMIKA_PUSH_INTERVAL'] = "60"  # sec
os.environ['DOMIKA_ALEMBIC_INI_PATH'] = "./alembic.ini"

import asyncio
from custom_components.domika.database.manage import migrate
from custom_components.domika.database.core import AsyncSessionFactory
from custom_components.domika.push_data.models import DomikaPushDataCreate
from custom_components.domika.push_data.service import create

def test_ha_event_fired():
    push_data = [
        DomikaPushDataCreate(
            uuid.uuid4(),
            "test_entity_id",
            "state",
            "on",
            "event_context_id",
            123123,
        )
    ]

    asyncio.run(migrate())
    session = AsyncSessionFactory()
    asyncio.run(create(session, push_data))


test_ha_event_fired()