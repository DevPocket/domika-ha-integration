"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""
import asyncio

from custom_components.domika.database.core import AsyncSessionFactory
from custom_components.domika.push_data.models import DomikaPushDataCreate
from custom_components.domika.push_data.service import create

def test_ha_event_fired():
    push_data = [
        DomikaPushDataCreate(
            "UUID_123",
            "test_entity_id",
            "state",
            "on",
            "event_context_id",
            123123,
        )
    ]
    session = AsyncSessionFactory()
    asyncio.run(create(session, push_data))
