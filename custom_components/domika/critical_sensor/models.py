# vim: set fileencoding=utf-8
"""
Critical sensor.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from dataclasses import dataclass, field

from mashumaro.mixins.json import DataClassJSONMixin

from .enums import CriticalityLevel


@dataclass
class DomikaCriticalSensor(DataClassJSONMixin):
    """Critical sensor data."""

    entity_id: str
    type: CriticalityLevel = field(metadata={'serialize': lambda v: v.to_string()})
    name: str
    device_class: str
    state: str
    timestamp: int


@dataclass
class DomikaCriticalSensorsRead(DataClassJSONMixin):
    """Critical sensors read model."""

    sensors: list[DomikaCriticalSensor]
    sensors_on: list[str]
