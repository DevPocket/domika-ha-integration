# vim: set fileencoding=utf-8
"""
Critical sensors.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from dataclasses import dataclass

from mashumaro.mixins.json import DataClassJSONMixin


@dataclass
class DomikaCriticalSensor(DataClassJSONMixin):
    """Critical sensor data."""

    entity_id: str
    name: str
    device_class: str
    state: str
    timestamp: int


@dataclass
class DomikaCriticalSensorsRead(DataClassJSONMixin):
    """Critical sensors read model."""

    sensors: list[DomikaCriticalSensor]
    sensors_on: list[str]
