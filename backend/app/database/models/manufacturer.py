"""Manufacturer profile and user ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.database.models.inspection import InspectionRecord
    from backend.app.database.models.model_config import ModelConfig
    from backend.app.database.models.pipeline import PipelineConfig


def _utcnow() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class ManufacturerProfile(Base):
    """Manufacturer / tenant profile."""

    __tablename__ = "manufacturer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(120), nullable=False)
    plant_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan"
    )
    model_configs: Mapped[list["ModelConfig"]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan"
    )
    pipeline_configs: Mapped[list["PipelineConfig"]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan"
    )
    inspection_records: Mapped[list["InspectionRecord"]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan"
    )


class User(Base):
    """Platform user belonging to a manufacturer."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), default="operator", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    manufacturer: Mapped["ManufacturerProfile"] = relationship(back_populates="users")
    inspections: Mapped[list["InspectionRecord"]] = relationship(back_populates="user")
