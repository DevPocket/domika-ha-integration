# vim: set fileencoding=utf-8
"""
Subscription data.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import uuid
from dataclasses import dataclass

from mashumaro.mixins.json import DataClassJSONMixin
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..models import AsyncBase


class Subscription(AsyncBase):
    """Event subscriptions."""

    __tablename__ = 'subscriptions'

    app_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('devices.app_session_id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
    )
    entity_id: Mapped[str] = mapped_column(primary_key=True)
    attribute: Mapped[str] = mapped_column(primary_key=True)
    need_push: Mapped[bool]


@dataclass
class DomikaSubscriptionBase(DataClassJSONMixin):
    """Base subscription model."""

    app_session_id: uuid.UUID
    entity_id: str
    attribute: str
    need_push: bool


@dataclass
class DomikaSubscriptionCreate(DomikaSubscriptionBase):
    """Subscription create model."""


@dataclass
class DomikaSubscriptionRead(DomikaSubscriptionBase):
    """Subscription read model."""


@dataclass
class DomikaSubscriptionUpdate(DataClassJSONMixin):
    """Subscription update model."""

    need_push: bool
