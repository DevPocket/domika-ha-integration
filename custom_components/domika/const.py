"""Domika Constants."""

import logging
import os
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

LOGGER = logging.getLogger(__name__)

DOMAIN = "domika"
# MAIN_LOGGER_NAME = DOMAIN


if os.getenv("DOMIKA_DEBUG") == "1":
    DATABASE_URL = os.getenv("DOMIKA_DATABASE_URL")
    PUSH_SERVER_URL = os.getenv("DOMIKA_PUSH_SERVER_URL")
    PUSH_INTERVAL = timedelta(seconds=int(os.getenv("DOMIKA_PUSH_INTERVAL") or 30))
    ALEMBIC_INI_PATH = os.getenv("DOMIKA_ALEMBIC_INI_PATH")
else:
    DATABASE_URL = "sqlite+aiosqlite:///Domika.db"
    PUSH_SERVER_URL = "http://159.203.109.27:8000/api/v1"
    PUSH_INTERVAL = timedelta(minutes=15)
    ALEMBIC_INI_PATH = "custom_components/domika/alembic.ini"

# Seconds
PUSH_SERVER_TIMEOUT = 10

SENSORS_DOMAIN = "binary_sensor"

CRITICAL_NOTIFICATION_SENSORS = [
    BinarySensorDeviceClass.CO,
    BinarySensorDeviceClass.GAS,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.SMOKE,
]

WARNING_NOTIFICATION_SENSORS = [
    BinarySensorDeviceClass.BATTERY,
    BinarySensorDeviceClass.COLD,
    BinarySensorDeviceClass.HEAT,
    BinarySensorDeviceClass.PROBLEM,
    BinarySensorDeviceClass.VIBRATION,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.TAMPER,
]

CRITICAL_NOTIFICATION_DEVICE_CLASSES = [str(e) for e in CRITICAL_NOTIFICATION_SENSORS]
WARNING_NOTIFICATION_DEVICE_CLASSES = [str(e) for e in WARNING_NOTIFICATION_SENSORS]

CRITICAL_PUSH_SETTINGS_DEVICE_CLASSES = {
    "smoke_select_all": BinarySensorDeviceClass.SMOKE,
    "moisture_select_all": BinarySensorDeviceClass.MOISTURE,
    "co_select_all": BinarySensorDeviceClass.CO,
    "gas_select_all": BinarySensorDeviceClass.GAS,
}

PUSH_DELAY_DEFAULT = 0
PUSH_DELAY_FOR_DOMAIN = {"sensor": 4}
