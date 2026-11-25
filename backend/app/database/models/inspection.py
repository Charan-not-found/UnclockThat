"""Inspection, anomaly result, and severity score ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.database.models.manufacturer import ManufacturerProfile, User
    from backend.app.database.models.model_config import ModelConfig
    from backend.app.database.models.pipeline import PipelineConfig


def _utcnow() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class InspectionRecord(Base):
    """Product-level inspection record pointing to local image storage."""

    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturer_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pipeline_config_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pipeline_configs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_serial: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    station_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    image_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)
    overall_decision: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    manufacturer: Mapped["ManufacturerProfile"] = relationship(back_populates="inspection_records")
    user: Mapped[Optional["User"]] = relationship(back_populates="inspections")
    pipeline_config: Mapped[Optional["PipelineConfig"]] = relationship(back_populates="inspection_records")
    anomaly_results: Mapped[list["AnomalyResult"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )
    severity_scores: Mapped[list["SeverityScore"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )


class AnomalyResult(Base):
    """Model anomaly detection output and local heatmap/mask paths."""

    __tablename__ = "anomaly_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_config_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("model_configs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_anomalous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    heatmap_file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    mask_file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    bounding_boxes_json: Mapped[Optional[list[dict[str, Any]] | dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    processing_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    inspection: Mapped["InspectionRecord"] = relationship(back_populates="anomaly_results")
    model_config: Mapped[Optional["ModelConfig"]] = relationship(back_populates="anomaly_results")
    severity_scores: Mapped[list["SeverityScore"]] = relationship(back_populates="anomaly_result")


class SeverityScore(Base):
    """Operational severity assessment for an inspection or anomaly result."""

    __tablename__ = "severity_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    anomaly_result_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("anomaly_results.id", ondelete="SET NULL"), nullable=True, index=True
    )
    severity_level: Mapped[str] = mapped_column(String(64), nullable=False)
    numeric_score: Mapped[float] = mapped_column(Float, nullable=False)
    affected_area_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rule_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    inspection: Mapped["InspectionRecord"] = relationship(back_populates="severity_scores")
    anomaly_result: Mapped[Optional["AnomalyResult"]] = relationship(back_populates="severity_scores")
