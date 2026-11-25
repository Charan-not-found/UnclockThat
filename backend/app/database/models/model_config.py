"""AI model configuration ORM model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.database.models.inspection import AnomalyResult
    from backend.app.database.models.manufacturer import ManufacturerProfile


def _utcnow() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class ModelConfig(Base):
    """AI model configuration and local filesystem path references."""

    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_family: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(64), default="1.0.0", nullable=False)
    dataset_dir_path: Mapped[str] = mapped_column(String(512), nullable=False)
    weights_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    hyperparameters_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    metrics_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    manufacturer: Mapped["ManufacturerProfile"] = relationship(back_populates="model_configs")
    anomaly_results: Mapped[list["AnomalyResult"]] = relationship(back_populates="model_config")
