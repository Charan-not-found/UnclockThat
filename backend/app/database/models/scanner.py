"""Scanner Unit, Analysis Module, Dataset, Training Run, and Correction ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScannerUnit(Base):
    """Named, reusable inspection configuration grouping one or more Analysis Modules."""

    __tablename__ = "scanner_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[str] = mapped_column(String(120), default="Manufacturing", nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="Draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    modules: Mapped[list["AnalysisModule"]] = relationship(
        back_populates="scanner_unit", cascade="all, delete-orphan"
    )


class DatasetRecord(Base):
    """Uploaded and validated dataset stored in data/datasets/ and data/training/."""

    __tablename__ = "dataset_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), default="normal", nullable=False)
    industry: Mapped[str] = mapped_column(String(120), default="Manufacturing", nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(512), nullable=False)
    extracted_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_image_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(64), default="Uploaded", nullable=False)
    validation_details_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class AnalysisModule(Base):
    """Configurable inspection capability inside a Scanner Unit."""

    __tablename__ = "analysis_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scanner_unit_id: Mapped[int] = mapped_column(
        ForeignKey("scanner_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    model_key: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dataset_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    selected_outputs_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    config_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    state: Mapped[str] = mapped_column(String(64), default="Draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    scanner_unit: Mapped["ScannerUnit"] = relationship(back_populates="modules")
    dataset: Mapped[Optional["DatasetRecord"]] = relationship()


class TrainingRun(Base):
    """Reproducible training job execution tracked in SQLite."""

    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scanner_unit_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scanner_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    module_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("analysis_modules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dataset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dataset_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_key: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), default="initial_training", nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="Queued", nullable=False)
    max_epochs: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    limit_train_batches: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(255), default="Queued", nullable=False)
    logs_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metrics_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    checkpoint_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class CorrectionRecord(Base):
    """Human review feedback & false-positive training sample record."""

    __tablename__ = "correction_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scanner_unit_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scanner_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    feedback_category: Mapped[str] = mapped_column(String(100), nullable=False)
    original_decision: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    corrected_decision: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    saved_image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    review_status: Mapped[str] = mapped_column(String(64), default="Reviewed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
