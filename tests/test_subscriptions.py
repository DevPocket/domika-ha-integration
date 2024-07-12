"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""
from tests_init import *
from custom_components.domika.device.flow import update_app_session_id
from custom_components.domika.subscription.flow import resubscribe, resubscribe_push, get_push_attributes, get_app_session_id_by_attributes
from custom_components.domika.subscription.models import Subscription
from custom_components.domika.push_data.service import create


async def test_subscriptions():
    # Create some app_sessions
    app_session_id1 = await update_app_session_id(db_session, "", USER_ID1)
    app_session_id2 = await update_app_session_id(db_session, "", USER_ID2)

    # Create some subscriptions
    await resubscribe(db_session, app_session_id1,
                {
                    "entity1_1": {"attr1_1", "attr1_2", "attr1_3"},
                    "entity2_1": {"attr2_1", "attr2_2", "attr2_3"},
                })
    # Check that 6 subscriptions were created
    stmt = select(Subscription).where(Subscription.app_session_id == app_session_id1)
    subscriptions = (await db_session.scalars(stmt)).all()
    assert len(subscriptions) == 6

    # Re-create subscriptions
    await resubscribe(db_session, app_session_id1,
                {
                    "entity1": {"attr1_1", "attr1_2"},
                    "entity2": {"attr2_1", "attr2_2", "attr2_3"},
                })
    # Check that 5 subscriptions were created
    stmt = select(Subscription).where(Subscription.app_session_id == app_session_id1)
    subscriptions = (await db_session.scalars(stmt)).all()
    assert len(subscriptions) == 5

    # Create subscriptions for other app_session_id
    await resubscribe(db_session, app_session_id2,
                {
                    "entity1": {"attr1_1"},
                    "entity3": {"attr3_1", "attr3_2", "attr3_3"},
                })
    # Check that 4 subscriptions were created
    stmt = select(Subscription).where(Subscription.app_session_id == app_session_id2)
    subscriptions = (await db_session.scalars(stmt)).all()
    assert len(subscriptions) == 4
    # Check that 5 subscriptions still exist for app_session_id1
    stmt = select(Subscription).where(Subscription.app_session_id == app_session_id1)
    subscriptions = (await db_session.scalars(stmt)).all()
    assert len(subscriptions) == 5
    # Check that need_push == False
    for sub in subscriptions:
        assert sub.need_push == False

    # Add some need_push == True values
    await resubscribe_push(db_session, app_session_id1, {
                    "entity1": {"attr1_1"},
                    "entity2": {"attr2_1"},
                })
    # Check that 2 subscriptions exist for app_session_id1 with need_push == True
    stmt = select(Subscription).where(Subscription.app_session_id == app_session_id1).where(Subscription.need_push == True)
    subscriptions = (await db_session.scalars(stmt)).all()
    assert len(subscriptions) == 2

    # Add more need_push == True values, with some non-existent subscriptions mentioned
    await resubscribe_push(db_session, app_session_id2, {
                    "entity1": {"attr1_1"},
                    "entity2": {"attr2_1"},
                    "entity3": {"attr3_1", "attr3_2"},
    })
    # Check that 3 subscriptions exist for app_session_id2 with need_push == True
    stmt = select(Subscription).where(Subscription.app_session_id == app_session_id2).where(Subscription.need_push == True)
    subscriptions = (await db_session.scalars(stmt)).all()
    assert len(subscriptions) == 3

    # Check that get_push_attributes works properly
    push_attributes = await get_push_attributes(db_session, app_session_id1)
    assert sorted(push_attributes, key=lambda x: x['entity_id']) == sorted([
        {
            "entity_id": "entity1",
            "attributes": ["attr1_1"]
        },
        {
            "entity_id": "entity2",
            "attributes": ["attr2_1"]
        }
    ], key=lambda x: x['entity_id'])

    # Check that get_push_attributes works properly
    push_attributes = await get_push_attributes(db_session, app_session_id2)
    assert sorted(push_attributes, key=lambda x: x['entity_id']) == sorted([
        {
            "entity_id": "entity1",
            "attributes": ["attr1_1"]
        },
        {
            "entity_id": "entity3",
            "attributes": ["attr3_1", "attr3_2"]
        },
    ], key=lambda x: x['entity_id'])

    # Check that get_app_session_id_by_attributes works properly
    app_session_ids = await get_app_session_id_by_attributes(db_session, "entity1", ["attr1_1"])
    assert set(app_session_ids) == {app_session_id1, app_session_id2}
    # Check that get_app_session_id_by_attributes works properly
    app_session_ids = await get_app_session_id_by_attributes(db_session, "entity1", ["attr1_1", "attr2_2"])
    assert set(app_session_ids) == {app_session_id1, app_session_id2}
    # Check that get_app_session_id_by_attributes works properly
    app_session_ids = await get_app_session_id_by_attributes(db_session, "entity3", ["attr1_1", "attr2_2"])
    assert set(app_session_ids) == set()
    # Check that get_app_session_id_by_attributes works properly
    app_session_ids = await get_app_session_id_by_attributes(db_session, "entity3", ["attr3_1", "attr1_1"])
    assert set(app_session_ids) == {app_session_id2}


asyncio.run(test_subscriptions())
asyncio.run(close_db())
