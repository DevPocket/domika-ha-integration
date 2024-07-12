"""
tests.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

from __future__ import annotations

import os
import asyncio
import uuid
from sqlalchemy import select

DB_NAME = "Domika.db"
os.environ['DOMIKA_DEBUG'] = "1"
os.environ['DOMIKA_DATABASE_URL'] = "sqlite+aiosqlite:///" + DB_NAME
os.environ['DOMIKA_PUSH_SERVER_URL'] = "http://159.203.109.27:8000/api/v1"
os.environ['DOMIKA_PUSH_INTERVAL'] = "60"  # sec
os.environ['DOMIKA_ALEMBIC_INI_PATH'] = "./alembic.ini"

if os.path.exists(DB_NAME):
    os.remove(DB_NAME)

from custom_components.domika.database.manage import migrate
from custom_components.domika.database.core import AsyncSessionFactory, close_db
from custom_components.domika.const import *
import custom_components.domika.errors as errors
import custom_components.domika.push_server_errors as server_errors

asyncio.run(migrate())
db_session = AsyncSessionFactory()

USER_ID1 = "user1"
USER_ID2 = "user2"
USER_ID3 = "user3"
TRANSACTION_ID1 = "test_transaction_1"
TRANSACTION_ID2 = "test_transaction_2"
TRANSACTION_ID3 = "test_transaction_3"
LOGGER = logging.getLogger(MAIN_LOGGER_NAME)
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())
