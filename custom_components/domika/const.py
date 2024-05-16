"""Domika Constants."""

import logging
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

LOGGER = logging.getLogger(__name__)

DOMAIN = 'Domika'
MAIN_LOGGER_NAME = DOMAIN

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

UPDATE_INTERVAL = timedelta(minutes=15)

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
