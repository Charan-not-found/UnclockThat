"""Persistent JobBatch and InspectionJob ORM models for high-throughput inspection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobBatch(Base):
    """Represents a Mass Test or External API bulk/single submission batch."""

    __tablename__ = "job_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="MASS_TEST", nullable=False)  # MASS_TEST | API
    scanner_unit_id: Mapped[int] = mapped_column(
        ForeignKey("scanner_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False, index=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    jobs: Mapped[list["InspectionJob"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class InspectionJob(Base):
    """Durable execution record for a single image inspection within a JobBatch."""

    __tablename__ = "inspection_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("job_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scanner_unit_id: Mapped[int] = mapped_column(
        ForeignKey("scanner_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("inspection_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Processing metrics (ms & memory)
    queue_wait_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preprocessing_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_load_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inference_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analysis_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    persistence_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_processing_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    peak_process_memory_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    batch: Mapped["JobBatch"] = relationship(back_populates="jobs")
