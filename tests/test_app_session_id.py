"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

from tests_init import *
from custom_components.domika.device.flow import update_app_session_id
from custom_components.domika.device.service import delete
from custom_components.domika.device.models import Device


async def test_app_session_id_create_update_delete():
    # Create a new app_session
    app_session_id1 = await update_app_session_id(db_session, "", USER_ID1)
    # Check that we have just one record
    stmt = select(Device).where(Device.app_session_id == app_session_id1)
    res = (await db_session.scalars(stmt)).all()
    assert len(res) == 1

    # Try to create it again
    app_session_id2 = await update_app_session_id(db_session, app_session_id1, USER_ID1)
    # Check that app_session_id didn't change
    assert app_session_id1 == app_session_id2
    # Check that we still have just one record
    stmt = select(Device).where(Device.app_session_id == app_session_id2)
    res = (await db_session.scalars(stmt)).all()
    assert len(res) == 1

    # Create the same one with a different user_id
    app_session_id3 = await update_app_session_id(db_session, app_session_id2, USER_ID2)

    # Check that app_session_id was recreated
    assert app_session_id2 != app_session_id3
    # Check that app_session_id2 was deleted
    stmt = select(Device).where(Device.app_session_id == app_session_id2)
    res = (await db_session.scalars(stmt)).all()
    assert len(res) == 0
    # Check that the new app_session has the new user_id
    stmt = select(Device).where(Device.app_session_id == app_session_id3)
    device = await db_session.scalar(stmt)
    assert device.user_id == USER_ID2

    # Create another 3 app_sessions
    app_session_id1 = await update_app_session_id(db_session, "", USER_ID1)
    app_session_id2 = await update_app_session_id(db_session, "", USER_ID2)
    app_session_id4 = await update_app_session_id(db_session, "", USER_ID3)

    # Check that we have 4 records
    stmt = select(Device)
    res = (await db_session.scalars(stmt)).all()
    assert len(res) == 4

    # Delete all app_sessions
    await delete(db_session, app_session_id1)
    await delete(db_session, app_session_id2)
    await delete(db_session, app_session_id3)
    await delete(db_session, app_session_id4)
    # Check that we have zero records
    stmt = select(Device)
    res = (await db_session.scalars(stmt)).all()
    assert len(res) == 0


asyncio.run(test_app_session_id_create_update_delete())
asyncio.run(close_db())
