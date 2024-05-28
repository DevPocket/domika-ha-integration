# vim: set fileencoding=utf-8
"""
Domika integration.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from dataclasses import dataclass

from mashumaro.mixins.json import DataClassJSONMixin


@dataclass
class DomikaHaEntity(DataClassJSONMixin):
    """Base homeassistant entity state model."""

    entity_id: str
    time_updated: float
    attribute: dict[str, str]
