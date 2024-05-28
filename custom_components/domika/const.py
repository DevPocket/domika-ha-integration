"""Domika Constants."""

import logging
import os
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

LOGGER = logging.getLogger(__name__)

DOMAIN = 'Domika'
MAIN_LOGGER_NAME = DOMAIN

ALEMBIC_INI_PATH = 'config/custom_components/domika/alembic.ini'

if os.getenv('DOMIKA_DEBUG') == '1':
    DATABASE_URL = os.getenv('DOMIKA_DATABASE_URL')
    PUSH_SERVER_URL = os.getenv('DOMIKA_PUSH_SERVER_URL')
    PUSH_INTERVAL = timedelta(seconds=int(os.getenv('DOMIKA_PUSH_INTERVAL') or 30))
else:
    DATABASE_URL = 'sqlite+aiosqlite:///Domika.db'
    PUSH_SERVER_URL = 'https://domika.app'
    PUSH_INTERVAL = timedelta(minutes=15)

# Event confirmation records will stay at least 15 seconds
EVENT_CONFIRMATION_EXPIRATION_TIME = 15 * 1e6

IOS_PLATFORM = 'ios'
IOS_SANDBOX_ENV = 'sandbox'
IOS_PRODUCTION_ENV = 'production'

ANDROID_PLATFORM = 'android'

# Number of days
DEVICE_EXPIRATION_TIME = 15

SENSORS_DOMAIN = 'binary_sensor'

SENSORS_DEVICE_ENUMS = [
    BinarySensorDeviceClass.CO,
    BinarySensorDeviceClass.GAS,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.SMOKE,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.TAMPER,
]

SENSORS_DEVICE_CLASSES = [str(e) for e in SENSORS_DEVICE_ENUMS]
