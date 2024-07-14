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
from custom_components.domika.subscription.flow import resubscribe, resubscribe_push, get_push_attributes, get_app_session_id_by_attributes


async def test_events():
    # Create some app_sessions
    app_session_id1 = await update_app_session_id(db_session, "", USER_ID1)
    app_session_id2 = await update_app_session_id(db_session, "", USER_ID2)
    await resubscribe(db_session, app_session_id1,
                {
                    "entity1": {"attr1_1", "attr1_2", "attr1_3"},
                    "entity2": {"attr2_1", "attr2_2", "attr2_3"},
                })
    await resubscribe_push(db_session, app_session_id1, {
                    "entity1": {"attr1_1"},
                    "entity2": {"attr2_1"},
                })

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
