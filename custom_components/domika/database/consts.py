# vim: set fileencoding=utf-8
"""
Database core.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

DATABASE_URL = 'sqlite+aiosqlite:///Domika.db'
ALEMBIC_INI_PATH = 'config/custom_components/domika/alembic.ini'

# Event confirmation records will stay at least 15 seconds
EVENT_CONFIRMATION_EXPIRATION_TIME = 15 * 1e6

IOS_PLATFORM = 'ios'
IOS_SANDBOX_ENV = 'sandbox'
IOS_PRODUCTION_ENV = 'production'

ANDROID_PLATFORM = 'android'

# Number of days
DEVICE_EXPIRATION_TIME = 15
