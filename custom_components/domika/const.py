"""Domika Constants."""

import logging
import os
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

LOGGER = logging.getLogger(__name__)

DOMAIN = "Domika"
MAIN_LOGGER_NAME = DOMAIN

ALEMBIC_INI_PATH = "custom_components/domika/alembic.ini"

if os.getenv("DOMIKA_DEBUG") == "1":
    DATABASE_URL = os.getenv("DOMIKA_DATABASE_URL")
    PUSH_SERVER_URL = os.getenv("DOMIKA_PUSH_SERVER_URL")
    PUSH_INTERVAL = timedelta(seconds=int(os.getenv("DOMIKA_PUSH_INTERVAL") or 30))
else:
    DATABASE_URL = "sqlite+aiosqlite:///Domika.db"
    PUSH_SERVER_URL = "http://159.203.109.27:8000/api/v1"
    PUSH_INTERVAL = timedelta(minutes=15)

# Seconds
PUSH_SERVER_TIMEOUT = 10

# Number of days
DEVICE_EXPIRATION_TIME = 15

SENSORS_DOMAIN = "binary_sensor"

CRITICAL_SENSORS_DEVICE_ENUMS = [
    BinarySensorDeviceClass.CO,
    BinarySensorDeviceClass.GAS,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.SMOKE,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.TAMPER,
]

WARNING_SENSORS_DEVICE_ENUMS = [
    BinarySensorDeviceClass.BATTERY,
    BinarySensorDeviceClass.COLD,
    BinarySensorDeviceClass.HEAT,
    BinarySensorDeviceClass.PROBLEM,
    BinarySensorDeviceClass.VIBRATION,
]

CRITICAL_SENSORS_DEVICE_CLASSES = [str(e) for e in CRITICAL_SENSORS_DEVICE_ENUMS]
WARNING_SENSORS_DEVICE_CLASSES = [str(e) for e in WARNING_SENSORS_DEVICE_ENUMS]
