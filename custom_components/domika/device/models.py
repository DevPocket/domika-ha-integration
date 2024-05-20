# vim: set fileencoding=utf-8
"""
Application device.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid
from dataclasses import dataclass, field

from mashumaro import pass_through
from mashumaro.config import BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from ..models import NOT_SET, AsyncBase


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

    app_session_id: uuid.UUID = field(
        metadata={
            'serialization_strategy': pass_through,
        },
    )
    push_session_id: uuid.UUID | None = field(
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

    push_session_id: uuid.UUID | None | NOT_SET = field(
        default='NOT_SET',
        metadata={
            'serialization_strategy': pass_through,
        },
    )
    push_token: str | NOT_SET = 'NOT_SET'
    platform: str | NOT_SET = 'NOT_SET'
    environment: str | NOT_SET = 'NOT_SET'
    last_update: int | NOT_SET = 'NOT_SET'

    class Config(BaseConfig):
        """Mashumaro config."""

        omit_default = True
