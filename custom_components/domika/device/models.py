# vim: set fileencoding=utf-8
"""
Application device.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional

from mashumaro import pass_through
from mashumaro.mixins.json import DataClassJSONMixin
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from ..models import AsyncBase


class Device(AsyncBase):
    """Application device."""

    __tablename__ = 'devices'

    app_session_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    push_session_id: Mapped[uuid.UUID] = mapped_column(default=None, nullable=True)
    push_token: Mapped[str]
    platform: Mapped[str]
    environment: Mapped[str]
    last_update: Mapped[int] = mapped_column(
        server_default=func.datetime('now'),
        onupdate=func.datetime('now'),
    )


@dataclass
class DomikaDeviceBase(DataClassJSONMixin):
    """Base application device model."""

    app_session_id: uuid.UUID
    push_session_id: Optional[uuid.UUID] = field(
        metadata={
            'serialization_strategy': pass_through,
        },
    )
    push_token: str
    platform: str
    environment: str


@dataclass
class DomikaDeviceCreate(DomikaDeviceBase):
    """Application device create model."""


@dataclass
class DomikaDeviceRead(DomikaDeviceBase):
    """Application device read model."""

    last_update: int


@dataclass
class DomikaDeviceUpdate(DataClassJSONMixin):
    """Application device update model."""

    push_session_id: uuid.UUID | None = None
    push_token: str | None = None
    platform: str | None = None
    environment: str | None = None
    last_update: int | None = None
