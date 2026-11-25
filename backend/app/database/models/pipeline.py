"""Inspection pipeline configuration ORM model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.database.models.inspection import InspectionRecord
    from backend.app.database.models.manufacturer import ManufacturerProfile


def _utcnow() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class PipelineConfig(Base):
    """Configurable inspection workflow / pipeline definition."""

    __tablename__ = "pipeline_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), default="1.0.0", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modules_json: Mapped[list[dict[str, Any]] | dict[str, Any]] = mapped_column(JSON, nullable=False)
    thresholds_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    manufacturer: Mapped["ManufacturerProfile"] = relationship(back_populates="pipeline_configs")
    inspection_records: Mapped[list["InspectionRecord"]] = relationship(back_populates="pipeline_config")
