# vim: set fileencoding=utf-8
"""
Notification sensor.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from dataclasses import dataclass, field

from mashumaro.mixins.json import DataClassJSONMixin

from .enums import NotificationType


@dataclass
class DomikaNotificationSensor(DataClassJSONMixin):
    """Notification sensor data."""

    entity_id: str
    type: NotificationType = field(metadata={'serialize': lambda v: v.to_string()})
    name: str
    device_class: str
    state: str
    timestamp: int


@dataclass
class DomikaNotificationSensorsRead(DataClassJSONMixin):
    """Notification sensors read model."""

    sensors: list[DomikaNotificationSensor]
    sensors_on: list[str]
