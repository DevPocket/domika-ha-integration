"""Domika Constants."""
from datetime import timedelta
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

import logging
LOGGER = logging.getLogger(__name__)

DOMAIN = "Domika"
DEFAULT_NAME = "Domika"

UPDATE_INTERVAL = timedelta(minutes=15)

SENSORS_DOMAIN = "binary_sensor"

CRITICAL_SENSORS_DEVICE_ENUMS = [
    BinarySensorDeviceClass.CO,
    BinarySensorDeviceClass.GAS,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.SMOKE,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.TAMPER
]

WARNING_SENSORS_DEVICE_ENUMS = [
    BinarySensorDeviceClass.BATTERY,
    BinarySensorDeviceClass.COLD,
    BinarySensorDeviceClass.HEAT,
    BinarySensorDeviceClass.PROBLEM,
    BinarySensorDeviceClass.VIBRATION
]

CRITICAL_SENSORS_DEVICE_CLASSES = [str(e) for e in CRITICAL_SENSORS_DEVICE_ENUMS]
WARNING_SENSORS_DEVICE_CLASSES = [str(e) for e in WARNING_SENSORS_DEVICE_ENUMS]

