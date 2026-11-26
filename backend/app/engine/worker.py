"""Persistent DB-backed job dispatcher, worker pool, restart recovery, and engine monitoring."""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import BASE_DIR
from backend.app.database.connection import SessionLocal
from backend.app.database.models.engine_jobs import InspectionJob, JobBatch
from backend.app.database.models.scanner import ScannerUnit
from backend.app.engine.config import get_engine_config
from backend.app.engine.inference_scheduler import GpuInferenceScheduler, ModuleSpec
from backend.app.engine.model_registry import EngineModelRegistry
from backend.app.engine.preprocessing import get_prep_executor, validate_and_prepare_image
from backend.app.engine.result_aggregator import aggregate_and_persist_result

logger = logging.getLogger("clockit.engine.worker")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "QUEUED": {"PREPROCESSING", "CANCELLED", "FAILED"},
    "PREPROCESSING": {"PROCESSING", "QUEUED", "FAILED", "CANCELLED"},
    "PROCESSING": {"ANALYZING", "QUEUED", "FAILED"},
    "ANALYZING": {"COMPLETED", "QUEUED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": {"QUEUED"},
    "CANCELLED": set(),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _transition_job(job: InspectionJob, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(job.status, set())
    if target not in allowed:
        raise ValueError(f"Invalid job state transition: {job.status} -> {target}")
    job.status = target


def recalculate_batch_status(db: Session, batch_id: int) -> Optional[JobBatch]:
    """Derive batch progress counts and aggregate status directly from persisted InspectionJob rows."""
    db.flush()
    batch = db.get(JobBatch, batch_id)
    if batch is None:
        return None

    rows = db.execute(
        select(InspectionJob.status, func.count(InspectionJob.id))
        .where(InspectionJob.batch_id == batch_id)
        .group_by(InspectionJob.status)
    ).all()
    counts = {status: int(cnt) for status, cnt in rows}

    total = sum(counts.values())
    completed = counts.get("COMPLETED", 0)
    failed = counts.get("FAILED", 0)
    cancelled = counts.get("CANCELLED", 0)
    in_flight = counts.get("PREPROCESSING", 0) + counts.get("PROCESSING", 0) + counts.get("ANALYZING", 0)
    queued = counts.get("QUEUED", 0)

    batch.total_items = total
    batch.completed_items = completed
    batch.failed_items = failed
    batch.cancelled_items = cancelled

    if batch.is_paused and (queued > 0 or in_flight > 0):
        batch.status = "PAUSED"
    elif in_flight > 0 or (queued > 0 and (completed + failed + cancelled) > 0):
        batch.status = "RUNNING"
        if batch.started_at is None:
            batch.started_at = _utcnow()
    elif queued > 0:
        batch.status = "QUEUED"
    elif total > 0 and completed == 0 and failed > 0 and cancelled == 0:
        batch.status = "FAILED"
        if batch.completed_at is None:
            batch.completed_at = _utcnow()
    elif total > 0 and cancelled == total:
        batch.status = "CANCELLED"
        if batch.completed_at is None:
            batch.completed_at = _utcnow()
    else:
        batch.status = "COMPLETED"
        if batch.completed_at is None:
            batch.completed_at = _utcnow()

    return batch


def _is_transient_error(exc: Exception) -> bool:
    if isinstance(exc, (FileNotFoundError, ValueError)):
        return False
    msg = str(exc).lower()
    if "corrupt" in msg or "unsupported" in msg or "missing" in msg or "exceeds" in msg:
        return False
    if isinstance(exc, RuntimeError) and "out of memory" in msg:
        return True
    if "locked" in msg or "timeout" in msg or "temporarily" in msg:
        return True
    return False


def _get_memory_mb() -> tuple[Optional[float], Optional[float]]:
    ram_mb = None
    gpu_mb = None
    try:
        import psutil
        ram_mb = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    except Exception:
        pass
    try:
        import torch
        if torch.cuda.is_available():
            gpu_mb = round(torch.cuda.memory_allocated() / (1024 * 1024), 2)
    except Exception:
        pass
    return ram_mb, gpu_mb


class InspectionEngineWorker:
    """Singleton background dispatcher + worker pool driving the shared processing engine."""

    _stop_event = threading.Event()
    _claim_lock = threading.Lock()
    _threads: list[threading.Thread] = []
    _started = False

    @classmethod
    def start(cls) -> None:
        if cls._started:
            return
        cls._stop_event.clear()
        cls.recover_interrupted_jobs()
        cfg = get_engine_config()
        num_workers = max(1, cfg.cpu_prep_workers)
        cls._threads = []
        for idx in range(num_workers):
            t = threading.Thread(
                target=cls._worker_loop,
                name=f"clockit-engine-worker-{idx}",
                daemon=True,
            )
            t.start()
            cls._threads.append(t)
        cls._started = True
        logger.info("InspectionEngineWorker started (%d workers).", num_workers)

    @classmethod
    def stop(cls) -> None:
        if not cls._started:
            return
        cls._stop_event.set()
        for t in cls._threads:
            t.join(timeout=2.0)
        cls._threads = []
        cls._started = False
        logger.info("InspectionEngineWorker stopped.")

    @classmethod
    def recover_interrupted_jobs(cls) -> int:
        """Reconcile any non-terminal jobs left behind after an application restart."""
        db = SessionLocal()
        recovered = 0
        affected_batches: set[int] = set()
        try:
            stuck = list(
                db.scalars(
                    select(InspectionJob).where(
                        InspectionJob.status.in_(["PREPROCESSING", "PROCESSING", "ANALYZING"])
                    )
                ).all()
            )
            for job in stuck:
                affected_batches.add(job.batch_id)
                if job.inspection_id is not None:
                    job.status = "COMPLETED"
                    if job.completed_at is None:
                        job.completed_at = _utcnow()
                elif job.retry_count < job.max_retries:
                    job.retry_count += 1
                    job.status = "QUEUED"
                    job.error_code = "RECOVERED_AFTER_RESTART"
                    job.error_message = "Job interrupted by restart; requeued automatically."
                else:
                    job.status = "FAILED"
                    job.error_code = "INTERRUPTED_MAX_RETRIES"
                    job.error_message = "Job interrupted by restart and retry limit exceeded."
                    job.completed_at = _utcnow()
                recovered += 1

            for b_id in affected_batches:
                recalculate_batch_status(db, b_id)
            if recovered:
                db.commit()
                logger.info("Restart recovery reconciled %d interrupted job(s).", recovered)
            return recovered
        finally:
            db.close()

    @classmethod
    def _claim_next_job(cls) -> Optional[dict[str, Any]]:
        """Atomically claim one QUEUED job from a non-paused batch without holding DB open during inference."""
        with cls._claim_lock:
            db = SessionLocal()
            try:
                stmt = (
                    select(InspectionJob)
                    .join(JobBatch, InspectionJob.batch_id == JobBatch.id)
                    .where(InspectionJob.status == "QUEUED", JobBatch.is_paused.is_(False))
                    .order_by(InspectionJob.priority.desc(), InspectionJob.id.asc())
                    .limit(1)
                )
                job = db.scalar(stmt)
                if job is None:
                    return None

                # Atomic conditional UPDATE to guard against concurrent workers
                now = _utcnow()
                res = db.execute(
                    update(InspectionJob)
                    .where(InspectionJob.id == job.id, InspectionJob.status == "QUEUED")
                    .values(status="PREPROCESSING", started_at=now)
                )
                if res.rowcount == 0:
                    db.rollback()
                    return None

                batch = db.get(JobBatch, job.batch_id)
                if batch and batch.started_at is None:
                    batch.started_at = now
                if batch and batch.status == "QUEUED":
                    batch.status = "RUNNING"

                unit = db.scalar(
                    select(ScannerUnit)
                    .options(selectinload(ScannerUnit.modules))
                    .where(ScannerUnit.id == job.scanner_unit_id)
                )
                if unit is None:
                    raise ValueError(f"Scanner Unit {job.scanner_unit_id} not found")

                ready_mods = [m for m in unit.modules if m.state == "Ready"]
                specs = [
                    ModuleSpec(
                        module_id=m.id,
                        module_name=m.name,
                        model_key=m.model_key,
                        weight=int((m.config_json or {}).get("weight", 100)),
                        selected_outputs=list(m.selected_outputs_json or []),
                        cloned_weights_rel=(m.config_json or {}).get("cloned_weights_path"),
                    )
                    for m in ready_mods
                ]

                submitted_ts = job.submitted_at
                if submitted_ts.tzinfo is None:
                    submitted_ts = submitted_ts.replace(tzinfo=timezone.utc)
                queue_wait_ms = round(max(0.0, (now - submitted_ts).total_seconds() * 1000.0), 2)
                job.queue_wait_ms = queue_wait_ms
                db.commit()

                return {
                    "job_id": job.id,
                    "batch_id": job.batch_id,
                    "source_type": batch.source_type if batch else "MASS_TEST",
                    "scanner_unit_id": unit.id,
                    "industry": unit.industry or "General",
                    "product_name": unit.product_name or job.original_filename,
                    "unit_name": unit.name,
                    "threshold": float(batch.threshold if batch else 0.5),
                    "image_path": job.image_path,
                    "original_filename": job.original_filename,
                    "existing_inspection_id": job.inspection_id,
                    "queue_wait_ms": queue_wait_ms,
                    "modules": specs,
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

    @classmethod
    def process_next_job(cls) -> bool:
        """Claim and process a single queued job. Returns True if a job was processed."""
        ctx = cls._claim_next_job()
        if ctx is None:
            return False

        job_id = ctx["job_id"]
        batch_id = ctx["batch_id"]
        t_total_start = time.perf_counter()

        try:
            # 1. Bounded CPU Preprocessing
            img_path = BASE_DIR / ctx["image_path"]
            future = get_prep_executor().submit(validate_and_prepare_image, img_path)
            prepared = future.result()

            cls._set_job_state(job_id, "PROCESSING", preprocessing_ms=prepared.preprocess_ms)

            # 2. Controlled Single-Owner GPU Inference
            from backend.app.api.v1.inspections import _analyze_image_bytes

            exec_out = GpuInferenceScheduler.execute_modules(
                raw_bytes=prepared.raw_bytes,
                modules=ctx["modules"],
                threshold=ctx["threshold"],
                heuristic_fn=_analyze_image_bytes,
            )

            cls._set_job_state(
                job_id,
                "ANALYZING",
                inference_ms=exec_out["inference_ms"],
                model_load_ms=exec_out["model_load_ms"],
            )

            # 3. Result Aggregation & Idempotent Persistence (short DB transaction)
            db = SessionLocal()
            try:
                station = "External API" if ctx["source_type"] == "API" else "Mass Test Engine"
                agg = aggregate_and_persist_result(
                    db,
                    scanner_unit_id=ctx["scanner_unit_id"],
                    industry=ctx["industry"],
                    product=ctx["original_filename"],
                    pipeline_name=ctx["unit_name"],
                    stored_image_path=img_path,
                    threshold=ctx["threshold"],
                    execution_out=exec_out,
                    station_name=station,
                    existing_inspection_id=ctx["existing_inspection_id"],
                )
                ram_mb, gpu_mb = _get_memory_mb()
                total_ms = round((time.perf_counter() - t_total_start) * 1000.0, 2)

                job = db.get(InspectionJob, job_id)
                if job:
                    job.inspection_id = agg["inspection_db_id"]
                    job.status = "COMPLETED"
                    job.completed_at = _utcnow()
                    job.analysis_ms = agg["analysis_ms"]
                    job.persistence_ms = agg["persistence_ms"]
                    job.total_processing_ms = total_ms
                    job.peak_process_memory_mb = ram_mb
                    job.gpu_memory_mb = gpu_mb
                    job.error_code = None
                    job.error_message = None
                recalculate_batch_status(db, batch_id)
                db.commit()
            finally:
                db.close()

        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id, exc)
            db = SessionLocal()
            try:
                job = db.get(InspectionJob, job_id)
                if job:
                    transient = _is_transient_error(exc)
                    if transient and job.retry_count < job.max_retries:
                        job.retry_count += 1
                        job.status = "QUEUED"
                        job.error_code = "TRANSIENT_RETRY"
                        job.error_message = str(exc)[:500]
                    else:
                        job.status = "FAILED"
                        job.completed_at = _utcnow()
                        job.error_code = type(exc).__name__
                        job.error_message = str(exc)[:500]
                recalculate_batch_status(db, batch_id)
                db.commit()
            finally:
                db.close()

        return True

    @classmethod
    def _set_job_state(cls, job_id: int, target: str, **fields: Any) -> None:
        db = SessionLocal()
        try:
            job = db.get(InspectionJob, job_id)
            if job:
                _transition_job(job, target)
                for k, v in fields.items():
                    setattr(job, k, v)
                db.commit()
        finally:
            db.close()

    @classmethod
    def _worker_loop(cls) -> None:
        while not cls._stop_event.is_set():
            try:
                worked = cls.process_next_job()
                if not worked:
                    cls._stop_event.wait(0.15)
            except Exception as exc:
                logger.error("Worker loop error: %s", exc)
                cls._stop_event.wait(0.5)

    @classmethod
    def get_engine_status(cls) -> dict[str, Any]:
        db = SessionLocal()
        try:
            q_depth = int(
                db.scalar(select(func.count(InspectionJob.id)).where(InspectionJob.status == "QUEUED")) or 0
            )
            active_count = int(
                db.scalar(
                    select(func.count(InspectionJob.id)).where(
                        InspectionJob.status.in_(["PREPROCESSING", "PROCESSING", "ANALYZING"])
                    )
                ) or 0
            )
        finally:
            db.close()

        gpu_available = False
        try:
            import torch
            gpu_available = bool(torch.cuda.is_available())
        except Exception:
            pass

        ram_mb, gpu_mb = _get_memory_mb()
        cpu_pct = None
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=None)
        except Exception:
            pass

        cfg = get_engine_config()
        return {
            "engine_state": "RUNNING" if cls._started else "STOPPED",
            "worker_state": "BUSY" if active_count > 0 else "IDLE",
            "worker_threads": len(cls._threads) or cfg.cpu_prep_workers,
            "queue_depth": q_depth,
            "active_jobs": active_count,
            "loaded_models": EngineModelRegistry.list_entries(),
            "gpu_available": gpu_available,
            "cpu_percent": cpu_pct,
            "ram_mb": ram_mb,
            "gpu_memory_mb": gpu_mb,
        }

    @classmethod
    def get_engine_metrics(cls) -> dict[str, Any]:
        db = SessionLocal()
        try:
            rows = db.execute(
                select(InspectionJob.status, func.count(InspectionJob.id)).group_by(InspectionJob.status)
            ).all()
            counts = {s: int(c) for s, c in rows}
            completed_jobs = list(
                db.scalars(
                    select(InspectionJob)
                    .where(InspectionJob.status == "COMPLETED", InspectionJob.total_processing_ms.is_not(None))
                    .order_by(InspectionJob.id.desc())
                    .limit(500)
                ).all()
            )
        finally:
            db.close()

        total_accepted = sum(counts.values())
        completed_n = counts.get("COMPLETED", 0)
        failed_n = counts.get("FAILED", 0)
        q_depth = counts.get("QUEUED", 0)

        latencies = sorted(j.total_processing_ms for j in completed_jobs if j.total_processing_ms is not None)
        wait_times = [j.queue_wait_ms for j in completed_jobs if j.queue_wait_ms is not None]
        load_times = [j.model_load_ms for j in completed_jobs if j.model_load_ms]

        def _pct(vals: list[float], p: float) -> Optional[float]:
            if not vals:
                return None
            idx = min(len(vals) - 1, int(round((p / 100.0) * (len(vals) - 1))))
            return round(vals[idx], 2)

        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else None
        avg_wait = round(sum(wait_times) / len(wait_times), 2) if wait_times else None
        throughput_per_min = round(60000.0 / avg_latency, 2) if avg_latency and avg_latency > 0 else 0.0
        ram_mb, gpu_mb = _get_memory_mb()
        cpu_pct = None
        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=None)
        except Exception:
            pass

        return {
            "window": "last_500_completed_jobs",
            "queue_depth": q_depth,
            "total_accepted_jobs": total_accepted,
            "completed_jobs": completed_n,
            "failed_jobs": failed_n,
            "failure_rate_pct": round((failed_n / total_accepted) * 100, 2) if total_accepted else 0.0,
            "throughput_per_min": throughput_per_min,
            "avg_queue_wait_ms": avg_wait,
            "avg_processing_latency_ms": avg_latency,
            "p50_latency_ms": _pct(latencies, 50),
            "p95_latency_ms": _pct(latencies, 95),
            "avg_model_load_ms": round(sum(load_times) / len(load_times), 2) if load_times else 0.0,
            "cpu_percent": cpu_pct,
            "ram_mb": ram_mb,
            "gpu_memory_mb": gpu_mb,
        }
