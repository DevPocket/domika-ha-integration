# vim: set fileencoding=utf-8
"""
Application dashboard.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from dataclasses import dataclass

from mashumaro.mixins.json import DataClassJSONMixin
from sqlalchemy.orm import Mapped, mapped_column

from ..models import AsyncBase


class Dashboard(AsyncBase):
    """Application dashboard."""

    __tablename__ = 'dashboards'

    user_id: Mapped[str] = mapped_column(primary_key=True)
    dashboard: Mapped[str]


@dataclass
class DomikaDashboardBase(DataClassJSONMixin):
    """Base dashboard model."""

    user_id: str
    dashboard: str


@dataclass
class DomikaDashoardCreate(DomikaDashboardBase):
    """Dashboard create model."""


@dataclass
class DomikaDashoardRead(DomikaDashboardBase):
    """Dashboard read model."""


@dataclass
class DomikaDashoardUpdate(DataClassJSONMixin):
    """Dashboard update model."""

    dashboard: str
