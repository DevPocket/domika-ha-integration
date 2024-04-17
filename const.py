"""Domika Constants."""
from datetime import timedelta
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

import logging
LOGGER = logging.getLogger(__name__)

DOMAIN = "domika"
UPDATE_INTERVAL = timedelta(minutes=15)

SENSORS_DOMAIN = "binary_sensor"

SENSORS_DEVICE_ENUMS = [
    BinarySensorDeviceClass.CO,
    BinarySensorDeviceClass.GAS,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.SMOKE,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.TAMPER
]

SENSORS_DEVICE_CLASSES = [str(e) for e in SENSORS_DEVICE_ENUMS]

