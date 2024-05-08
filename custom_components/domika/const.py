"""Domika Constants."""

import logging
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

LOGGER = logging.getLogger(__name__)

DOMAIN = 'Domika'
MAIN_LOGGER_NAME = DOMAIN

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
