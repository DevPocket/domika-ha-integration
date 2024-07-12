"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

from tests_init import *
from custom_components.domika.device.flow import update_app_session_id
from custom_components.domika.push_data.models import DomikaPushDataCreate
from custom_components.domika.push_data.flow import register_event
from custom_components.domika.push_data.service import create


async def test_events():
    # Create some app_sessions
    app_session_id1 = await update_app_session_id(db_session, "", USER_ID1)
    app_session_id2 = await update_app_session_id(db_session, "", USER_ID2)

    # Create events
    push_data = [
        DomikaPushDataCreate(
            uuid.uuid4(),
            "entity_1",
            "attr1_1",
            "on",
            "event_context_id",
            123123,
        )
    ]
    res = await create(db_session, push_data, returning=True)
    print(res)


asyncio.run(test_events())
asyncio.run(close_db())
