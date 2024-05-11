# vim: set fileencoding=utf-8
"""
Push data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid
from dataclasses import dataclass

from mashumaro.mixins.json import DataClassJSONMixin
from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..models import AsyncBase


class PushData(AsyncBase):
    """Data to be pushed."""

    __tablename__ = 'push_data'

    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4(), primary_key=True)
    app_session_id: Mapped[str] = mapped_column(
        ForeignKey('devices.app_session_id', ondelete='CASCADE', onupdate='CASCADE'),
    )
    entity_id: Mapped[str]
    attribute: Mapped[str]
    value: Mapped[str]
    context_id: Mapped[str]
    timestamp: Mapped[int] = mapped_column(server_default=func.datetime('now'))

    __table_args__ = (UniqueConstraint('app_session_id', 'entity_id', 'attribute'),)


@dataclass
class DomikaPushDataBase(DataClassJSONMixin):
    """Base push data model."""

    app_session_id: str
    entity_id: str
    attribute: str
    need_push: bool


@dataclass
class DomikaPushDatanCreate(DomikaPushDataBase):
    """Push data create model."""


@dataclass
class DomikPushDataRead(DomikaPushDataBase):
    """Push data read model."""


@dataclass
class DomikaPushDataUpdate(DataClassJSONMixin):
    """Push data update model."""

    need_push: bool
