# vim: set fileencoding=utf-8
"""
Entity.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

from dataclasses import dataclass

from mashumaro.mixins.json import DataClassJSONMixin


@dataclass
class DomikaEntitiesList(DataClassJSONMixin):
    """Entities data: name, related ids and capabilities."""

    entities: dict


@dataclass
class DomikaEntityInfo(DataClassJSONMixin):
    """Entity data: name, related ids and capabilities."""

    info: dict
