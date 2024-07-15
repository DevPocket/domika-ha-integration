"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

from tests_init import *
from custom_components.domika.device.flow import update_app_session_id
from custom_components.domika.push_data.models import DomikaPushDataCreate, PushData
from custom_components.domika.push_data.flow import register_event
from custom_components.domika.push_data.service import create, delete
from custom_components.domika.subscription.flow import resubscribe, resubscribe_push, get_push_attributes, get_app_session_id_by_attributes
import sqlalchemy
import sqlalchemy.dialects.sqlite as sqlite_dialect

app_session_id1 = None
app_session_id2 = None


async def get_push_data_len():
    stmt = select(PushData)
    return len((await db_session.scalars(stmt)).all())


async def test_events():
    # Create some app_sessions
    global app_session_id1
    global app_session_id2
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
    assert await get_push_data_len() == 2

    # Create events
    push_data = [
        DomikaPushDataCreate(uuid.uuid4(), "entity1", "attr1_1", "on", "event_context_id3", 3),
        DomikaPushDataCreate(uuid.uuid4(), "entity1", "attr1_2", "on", "event_context_id4", 4),
        DomikaPushDataCreate(uuid.uuid4(), "entity3", "attr3_1", "on", "event_context_id5", 6),
    ]
    res = await create(db_session, push_data, returning=True)
    # Check that 3 additional push_data records has been added (5 total).
    assert await get_push_data_len() == 5

    # Create the same events again
    res = await create(db_session, push_data, returning=True)
    # Check that there are still 5 push_data records.
    assert await get_push_data_len() == 5


async def test_events_confirmation():
    # Clean push_data
    stmt = sqlalchemy.delete(PushData)
    await db_session.execute(stmt)
    await db_session.commit()
    # Check that there are 0 records.
    assert await get_push_data_len() == 0

    event_id1 = uuid.uuid4()
    event_id2 = uuid.uuid4()
    event_id3 = uuid.uuid4()
    # Create 3 similar events
    push_data = [
        DomikaPushDataCreate(event_id1, "entity1", "attr1_1", "on", "event_context_id1", 1),
        DomikaPushDataCreate(event_id2, "entity2", "attr2_1", "on", "event_context_id1", 1),
        DomikaPushDataCreate(event_id3, "entity3", "attr3_1", "on", "event_context_id2", 2),
    ]
    res = await create(db_session, push_data, returning=True)
    # Check that 4 push_data records has been added.
    assert await get_push_data_len() == 4

    # Delete some of push_data records
    await delete(db_session, [event_id1], app_session_id1)
    # Check that we have 3 push_data records left.
    assert await get_push_data_len() == 3

    # Delete some of push_data records
    await delete(db_session, [event_id2], app_session_id1)
    # Check that we have 3 push_data records left.
    assert await get_push_data_len() == 2

    # Delete some of push_data records
    await delete(db_session, [event_id2], app_session_id2)
    # Check that we have 3 push_data records left.
    assert await get_push_data_len() == 1

asyncio.run(test_events())
asyncio.run(test_events_confirmation())
asyncio.run(close_db())
