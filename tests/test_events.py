"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

from tests_init import *
from custom_components.domika.device.flow import update_app_session_id
from custom_components.domika.push_data.models import DomikaPushDataCreate, PushData
from custom_components.domika.push_data.flow import register_event
from custom_components.domika.push_data.service import create
from custom_components.domika.subscription.flow import resubscribe, resubscribe_push, get_push_attributes, get_app_session_id_by_attributes


async def test_events():
    # Create some app_sessions
    app_session_id1 = await update_app_session_id(db_session, "", USER_ID1)
    app_session_id2 = await update_app_session_id(db_session, "", USER_ID2)
    await resubscribe(db_session, app_session_id1, {
        "entity1": {"attr1_1", "attr1_2", "attr1_3"},
        "entity2": {"attr2_1", "attr2_2", "attr2_3"},
    })
    await resubscribe(db_session, app_session_id2, {
        "entity1": {"attr1_1"},
        "entity2": {"attr2_1"},
        "entity3": {"attr3_1", "attr3_2", "attr3_3"},
    })
    await resubscribe_push(db_session, app_session_id1, {
        "entity1": {"attr1_1", "attr1_2"},
        "entity2": {"attr2_1"},
    })
    await resubscribe_push(db_session, app_session_id2, {
        "entity2": {"attr2_1"},
        "entity3": {"attr3_1", "attr3_2"},
    })


    # Create 3 similar events
    push_data = [
        DomikaPushDataCreate(uuid.uuid4(), "entity2", "attr2_1", "on", "event_context_id1", 1),
        DomikaPushDataCreate(uuid.uuid4(), "entity2", "attr2_1", "on", "event_context_id1", 1),
        DomikaPushDataCreate(uuid.uuid4(), "entity2", "attr2_1", "on", "event_context_id2", 2),
    ]
    res = await create(db_session, push_data, returning=True)
    # Check that 2 push_data records has been added.
    stmt = select(PushData)
    res = (await db_session.scalars(stmt)).all()
    assert len(res) == 2

    # Create events
    push_data = [
        DomikaPushDataCreate(uuid.uuid4(), "entity1", "attr1_1", "on", "event_context_id3", 3),
        DomikaPushDataCreate(uuid.uuid4(), "entity1", "attr1_2", "on", "event_context_id4", 4),
        DomikaPushDataCreate(uuid.uuid4(), "entity3", "attr3_1", "on", "event_context_id5", 6),
    ]
    res = await create(db_session, push_data, returning=True)
    # Check that 3 additional push_data records has been added (5 total).
    stmt = select(PushData)
    res = (await db_session.scalars(stmt)).all()
    assert len(res) == 5

    # Create events again
    res = await create(db_session, push_data, returning=True)
    # Check that there are still 5 push_data records.
    stmt = select(PushData)
    res = (await db_session.scalars(stmt)).all()
    assert len(res) == 5


asyncio.run(test_events())
asyncio.run(close_db())
