"""Domika Constants."""

import logging
import os
from datetime import timedelta

from homeassistant.components import binary_sensor, sensor
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

LOGGER = logging.getLogger(__name__)

DOMAIN = "domika"

if os.getenv("DOMIKA_DEBUG") == "1":
    PUSH_SERVER_URL = os.getenv("DOMIKA_PUSH_SERVER_URL")
    PUSH_INTERVAL = timedelta(seconds=int(os.getenv("DOMIKA_PUSH_INTERVAL") or 30))
else:
    PUSH_SERVER_URL = "https://pns.domika.app:8000/api/v1"
    PUSH_INTERVAL = timedelta(minutes=15)

# Seconds
PUSH_SERVER_TIMEOUT = 10

SENSORS_DOMAIN = binary_sensor.DOMAIN

CRITICAL_NOTIFICATION_DEVICE_CLASSES = [
    BinarySensorDeviceClass.CO.value,
    BinarySensorDeviceClass.GAS.value,
    BinarySensorDeviceClass.MOISTURE.value,
    BinarySensorDeviceClass.SMOKE.value,
]
WARNING_NOTIFICATION_DEVICE_CLASSES = [
    BinarySensorDeviceClass.BATTERY.value,
    BinarySensorDeviceClass.COLD.value,
    BinarySensorDeviceClass.HEAT.value,
    BinarySensorDeviceClass.PROBLEM.value,
    BinarySensorDeviceClass.VIBRATION.value,
    BinarySensorDeviceClass.SAFETY.value,
    BinarySensorDeviceClass.TAMPER.value,
]

CRITICAL_PUSH_SETTINGS_DEVICE_CLASSES = {
    "smoke_select_all": BinarySensorDeviceClass.SMOKE,
    "moisture_select_all": BinarySensorDeviceClass.MOISTURE,
    "co_select_all": BinarySensorDeviceClass.CO,
    "gas_select_all": BinarySensorDeviceClass.GAS,
}

# How many cycles should we skip till push notification is sent.
PUSH_DELAY_DEFAULT = 2
PUSH_DELAY_FOR_DOMAIN = {sensor.const.DOMAIN: 2}

CRITICAL_PUSH_ALERT_STRINGS = {
    "default": "Sensor triggered",
    BinarySensorDeviceClass.BATTERY: "push.sensor.battery",
    BinarySensorDeviceClass.COLD: "push.sensor.cold",
    BinarySensorDeviceClass.HEAT: "push.sensor.heat",
    BinarySensorDeviceClass.PROBLEM: "push.sensor.problem",
    BinarySensorDeviceClass.VIBRATION: "push.sensor.vibration",
    BinarySensorDeviceClass.SAFETY: "push.sensor.safety",
    BinarySensorDeviceClass.TAMPER: "push.sensor.tamper",
    BinarySensorDeviceClass.CO: "push.sensor.co",
    BinarySensorDeviceClass.GAS: "push.sensor.gas",
    BinarySensorDeviceClass.MOISTURE: "push.sensor.moisture",
    BinarySensorDeviceClass.SMOKE: "push.sensor.smoke"
}