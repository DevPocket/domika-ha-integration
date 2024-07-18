"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""
from tests_init import *
from custom_components.domika.device.flow import (
    update_app_session_id,
    check_push_token,
    remove_push_session,
    create_push_session,
    verify_push_session
)
from custom_components.domika.device.models import Device


async def test_push_session_create_update_delete():
    # Check that proper exception is raised if no app_session found
    try:
        res = await check_push_token(db_session, uuid.uuid4(), "ios", "sandbox", "dummy_push_token")
    except Exception as e:
        assert isinstance(e, errors.AppSessionIdNotFoundError)
    try:
        res = await remove_push_session(db_session, uuid.uuid4())
    except Exception as e:
        assert isinstance(e, errors.AppSessionIdNotFoundError)

    # Check that proper exception is raised if no app_session found
    app_session_id1, _ = await update_app_session_id(db_session, "", USER_ID1)
    try:
        res = await check_push_token(db_session, app_session_id1, "ios", "sandbox", "dummy_push_token")
    except Exception as e:
        assert isinstance(e, errors.PushSessionIdNotFoundError)
    try:
        res = await remove_push_session(db_session, app_session_id1)
    except Exception as e:
        assert isinstance(e, errors.PushSessionIdNotFoundError)

    # Just checking this doesn't crash
    await create_push_session(TRANSACTION_ID1, "ios", "sandbox", "dummy_push_token", str(app_session_id1))
    try:
        await verify_push_session(db_session, app_session_id1, "dummy_verification_key")
    except Exception as e:
        assert isinstance(e, server_errors.BadRequestError)



asyncio.run(test_push_session_create_update_delete())
asyncio.run(close_db())
