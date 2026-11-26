"""High-throughput Job, Batch, Mass Test, External API, and Engine Monitoring endpoints."""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
import uuid
import zipfile
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import BASE_DIR, get_settings
from backend.app.database.connection import get_db
from backend.app.database.models.engine_jobs import InspectionJob, JobBatch
from backend.app.database.models.inspection import InspectionRecord, SeverityScore
from backend.app.database.models.scanner import ScannerUnit
from backend.app.engine.config import get_engine_config
from backend.app.engine.worker import InspectionEngineWorker, recalculate_batch_status

logger = logging.getLogger("clockit.api.engine")

router = APIRouter(tags=["engine"])

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
_RATE_WINDOW: dict[str, deque[float]] = defaultdict(deque)


def _check_api_auth_and_rate(request: Request, x_api_key: Optional[str] = Header(None)) -> None:
    expected = os.getenv("CLOCKIT_API_KEY", "").strip()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")

    cfg = get_engine_config()
    client_ip = request.client.host if request.client else "local"
    now = time.time()
    q = _RATE_WINDOW[client_ip]
    while q and now - q[0] > 60.0:
        q.popleft()
    if len(q) >= cfg.api_rate_limit_per_min:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Retry shortly.")
    q.append(now)


def _check_admission_and_disk(db: Session, incoming_count: int) -> None:
    cfg = get_engine_config()
    settings = get_settings()
    try:
        usage = shutil.disk_usage(settings.storage_root)
        free_mb = usage.free / (1024 * 1024)
        if free_mb < cfg.min_free_disk_mb:
            raise HTTPException(status_code=507, detail="Insufficient disk space for inspection ingestion.")
    except OSError:
        pass

    queued_now = len(list(db.scalars(select(InspectionJob.id).where(InspectionJob.status == "QUEUED")).all()))
    if queued_now + incoming_count > cfg.max_queue_size:
        raise HTTPException(
            status_code=429,
            detail=f"Queue capacity reached ({queued_now}/{cfg.max_queue_size}). Wait for pending jobs to drain.",
        )


def _stream_upload_to_path(upload: UploadFile, dst: Path, max_bytes: int) -> int:
    total = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as f:
        while True:
            chunk = upload.file.read(1024 * 256)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"File '{upload.filename}' exceeds maximum allowed size.")
            f.write(chunk)
    return total


def _safe_extract_zip_members(
    zip_path: Path,
    dest_dir: Path,
    max_entries: int,
    max_uncompressed_bytes: int,
) -> tuple[list[tuple[str, Path]], list[dict[str, str]]]:
    """Stream-extract valid image members from a ZIP archive with traversal & zip-bomb guards."""
    accepted: list[tuple[str, Path]] = []
    rejected: list[dict[str, str]] = []
    total_uncompressed = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > max_entries:
            raise HTTPException(
                status_code=422,
                detail=f"ZIP contains {len(infos)} entries, exceeding max_zip_entries ({max_entries}).",
            )
        for info in infos:
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts:
                rejected.append({"filename": info.filename, "reason": "Unsafe path traversal rejected"})
                continue
            ext = Path(name).suffix.lower()
            if ext not in IMAGE_EXTS:
                rejected.append({"filename": info.filename, "reason": f"Unsupported format ({ext or 'none'})"})
                continue
            if info.compress_size > 0 and (info.file_size / info.compress_size) > 100:
                rejected.append({"filename": info.filename, "reason": "Suspicious compression ratio rejected"})
                continue
            total_uncompressed += info.file_size
            if total_uncompressed > max_uncompressed_bytes:
                raise HTTPException(status_code=422, detail="ZIP uncompressed size exceeds limit.")

            safe_name = f"{uuid.uuid4().hex}{ext}"
            out_path = dest_dir / safe_name
            with zf.open(info, "r") as src, out_path.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 256)
            accepted.append((Path(name).name, out_path))

    return accepted, rejected


class BatchSubmitOut(BaseModel):
    batch_id: str
    status: str
    total_items: int
    completed_items: int
    rejected_files: list[dict[str, str]] = []
    status_url: str


def _batch_to_dict(db: Session, batch: JobBatch) -> dict[str, Any]:
    jobs = list(db.scalars(select(InspectionJob).where(InspectionJob.batch_id == batch.id)).all())
    counts = {
        "QUEUED": 0,
        "PREPROCESSING": 0,
        "PROCESSING": 0,
        "ANALYZING": 0,
        "COMPLETED": 0,
        "FAILED": 0,
        "CANCELLED": 0,
    }
    for j in jobs:
        counts[j.status] = counts.get(j.status, 0) + 1

    total = len(jobs)
    terminal = counts["COMPLETED"] + counts["FAILED"] + counts["CANCELLED"]
    progress_pct = round((terminal / total) * 100, 1) if total else 0.0

    elapsed_sec = 0.0
    if batch.started_at:
        st = batch.started_at if batch.started_at.tzinfo else batch.started_at.replace(tzinfo=timezone.utc)
        end = batch.completed_at if batch.completed_at else datetime.now(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        elapsed_sec = round(max(0.0, (end - st).total_seconds()), 2)

    throughput_per_min = round((counts["COMPLETED"] / elapsed_sec) * 60.0, 2) if elapsed_sec > 0.1 else 0.0

    return {
        "batch_id": batch.batch_uid,
        "source_type": batch.source_type,
        "scanner_unit_id": batch.scanner_unit_id,
        "status": batch.status,
        "is_paused": batch.is_paused,
        "total_items": total,
        "queued_items": counts["QUEUED"],
        "preprocessing_items": counts["PREPROCESSING"],
        "processing_items": counts["PROCESSING"],
        "analyzing_items": counts["ANALYZING"],
        "completed_items": counts["COMPLETED"],
        "failed_items": counts["FAILED"],
        "cancelled_items": counts["CANCELLED"],
        "progress_pct": progress_pct,
        "elapsed_sec": elapsed_sec,
        "throughput_per_min": throughput_per_min,
        "created_at": batch.created_at.isoformat(),
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        "metadata": batch.metadata_json,
    }


def _create_batch_and_jobs(
    db: Session,
    *,
    scanner_unit_id: int,
    source_type: str,
    files: list[UploadFile],
    threshold: float,
    priority: int,
    idempotency_key: Optional[str],
    metadata_str: Optional[str],
) -> BatchSubmitOut:
    unit = db.get(ScannerUnit, scanner_unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Scanner Unit not found")

    if idempotency_key:
        existing = db.scalar(select(JobBatch).where(JobBatch.idempotency_key == idempotency_key))
        if existing is not None:
            return BatchSubmitOut(
                batch_id=existing.batch_uid,
                status=existing.status,
                total_items=existing.total_items,
                completed_items=existing.completed_items,
                rejected_files=[],
                status_url=f"/api/v1/batches/{existing.batch_uid}",
            )

    if not files:
        raise HTTPException(status_code=422, detail="At least one image or ZIP archive must be uploaded.")

    cfg = get_engine_config()
    settings = get_settings()
    prefix = "API" if source_type == "API" else "MASS"
    batch_uid = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
    batch_dir = settings.storage_root / "uploads" / "batches" / batch_uid
    batch_dir.mkdir(parents=True, exist_ok=True)

    accepted: list[tuple[str, Path]] = []
    rejected: list[dict[str, str]] = []

    for up in files:
        fname = up.filename or "upload.bin"
        ext = Path(fname).suffix.lower()
        if ext == ".zip":
            zip_tmp = batch_dir / f"_archive_{uuid.uuid4().hex}.zip"
            try:
                _stream_upload_to_path(up, zip_tmp, cfg.max_zip_mb * 1024 * 1024)
                z_acc, z_rej = _safe_extract_zip_members(
                    zip_tmp,
                    batch_dir,
                    max_entries=cfg.max_zip_entries,
                    max_uncompressed_bytes=cfg.max_zip_mb * 1024 * 1024,
                )
                accepted.extend(z_acc)
                rejected.extend(z_rej)
            except ValueError as exc:
                rejected.append({"filename": fname, "reason": str(exc)})
            except zipfile.BadZipFile:
                rejected.append({"filename": fname, "reason": "Corrupt or invalid ZIP archive"})
            finally:
                zip_tmp.unlink(missing_ok=True)
        elif ext in IMAGE_EXTS:
            safe_name = f"{uuid.uuid4().hex}{ext}"
            dst = batch_dir / safe_name
            try:
                _stream_upload_to_path(up, dst, cfg.max_upload_mb * 1024 * 1024)
                accepted.append((Path(fname).name, dst))
            except ValueError as exc:
                dst.unlink(missing_ok=True)
                rejected.append({"filename": fname, "reason": str(exc)})
        else:
            rejected.append({"filename": fname, "reason": f"Unsupported file type ({ext or 'none'})"})

    if not accepted:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise HTTPException(
            status_code=422,
            detail=f"No valid images accepted. Rejected {len(rejected)} file(s).",
        )

    _check_admission_and_disk(db, len(accepted))

    meta = None
    if metadata_str:
        try:
            meta = json.loads(metadata_str)
        except Exception:
            meta = {"raw": metadata_str}

    batch = JobBatch(
        batch_uid=batch_uid,
        source_type=source_type,
        scanner_unit_id=scanner_unit_id,
        total_items=len(accepted),
        status="QUEUED",
        threshold=threshold,
        idempotency_key=idempotency_key,
        metadata_json=meta,
    )
    db.add(batch)
    db.flush()

    for orig_name, abs_path in accepted:
        rel_path = str(abs_path.relative_to(BASE_DIR)).replace("\\", "/")
        job = InspectionJob(
            job_uid=f"JOB-{uuid.uuid4().hex[:10].upper()}",
            batch_id=batch.id,
            scanner_unit_id=scanner_unit_id,
            original_filename=orig_name,
            image_path=rel_path,
            priority=priority,
            status="QUEUED",
            max_retries=cfg.max_retries,
        )
        db.add(job)

    db.commit()
    return BatchSubmitOut(
        batch_id=batch.batch_uid,
        status=batch.status,
        total_items=batch.total_items,
        completed_items=0,
        rejected_files=rejected,
        status_url=f"/api/v1/batches/{batch.batch_uid}",
    )


@router.post("/jobs", response_model=BatchSubmitOut, status_code=202)
def submit_single_job(
    request: Request,
    scanner_unit_id: int = Form(...),
    threshold: float = Form(0.5),
    priority: int = Form(5),
    idempotency_key: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(_check_api_auth_and_rate),
) -> BatchSubmitOut:
    """External API & shared pipeline: submit a single inspection image asynchronously."""
    return _create_batch_and_jobs(
        db,
        scanner_unit_id=scanner_unit_id,
        source_type="API",
        files=[file],
        threshold=threshold,
        priority=priority,
        idempotency_key=idempotency_key,
        metadata_str=metadata,
    )


@router.post("/jobs/bulk", response_model=BatchSubmitOut, status_code=202)
def submit_bulk_jobs(
    request: Request,
    scanner_unit_id: int = Form(...),
    source_type: str = Form("MASS_TEST"),
    threshold: float = Form(0.5),
    priority: int = Form(5),
    idempotency_key: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(_check_api_auth_and_rate),
) -> BatchSubmitOut:
    """Mass Test & External API shared endpoint: submit multiple images or ZIP archives."""
    normalized_source = "API" if source_type.upper() == "API" else "MASS_TEST"
    return _create_batch_and_jobs(
        db,
        scanner_unit_id=scanner_unit_id,
        source_type=normalized_source,
        files=files,
        threshold=threshold,
        priority=priority,
        idempotency_key=idempotency_key,
        metadata_str=metadata,
    )


@router.get("/jobs/{job_uid}")
def get_job_status(job_uid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve individual job execution status, timings, and linked inspection ID."""
    job = db.scalar(select(InspectionJob).where(InspectionJob.job_uid == job_uid))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_uid,
        "scanner_unit_id": job.scanner_unit_id,
        "original_filename": job.original_filename,
        "status": job.status,
        "retry_count": job.retry_count,
        "inspection_id": f"INS-{job.inspection_id}" if job.inspection_id else None,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "submitted_at": job.submitted_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "queue_wait_ms": job.queue_wait_ms,
        "preprocessing_ms": job.preprocessing_ms,
        "model_load_ms": job.model_load_ms,
        "inference_ms": job.inference_ms,
        "analysis_ms": job.analysis_ms,
        "persistence_ms": job.persistence_ms,
        "total_processing_ms": job.total_processing_ms,
    }


@router.get("/batches")
def list_batches(
    limit: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List recent Mass Test and External API batches."""
    batches = list(db.scalars(select(JobBatch).order_by(JobBatch.id.desc()).limit(limit)).all())
    return [_batch_to_dict(db, b) for b in batches]


@router.get("/batches/{batch_uid}")
def get_batch_status(batch_uid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve live batch progress and execution breakdown."""
    batch = db.scalar(select(JobBatch).where(JobBatch.batch_uid == batch_uid))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_to_dict(db, batch)


@router.get("/batches/{batch_uid}/results")
def get_batch_results(
    batch_uid: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    job_status: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve paginated batch results using CLOCKIT's standard inspection result fields."""
    batch = db.scalar(select(JobBatch).where(JobBatch.batch_uid == batch_uid))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    stmt = select(InspectionJob).where(InspectionJob.batch_id == batch.id).order_by(InspectionJob.id.asc())
    if job_status:
        stmt = stmt.where(InspectionJob.status == job_status)
    jobs = list(db.scalars(stmt).all())

    insp_ids = [j.inspection_id for j in jobs if j.inspection_id is not None]
    insp_map: dict[int, InspectionRecord] = {}
    sev_map: dict[int, str] = {}
    if insp_ids:
        for r in db.scalars(select(InspectionRecord).where(InspectionRecord.id.in_(insp_ids))).all():
            insp_map[r.id] = r
        for s in db.scalars(select(SeverityScore).where(SeverityScore.inspection_id.in_(insp_ids))).all():
            sev_map[s.inspection_id] = s.severity_level

    items = []
    for j in jobs:
        insp = insp_map.get(j.inspection_id) if j.inspection_id else None
        dec = insp.overall_decision if insp else None
        sev = sev_map.get(j.inspection_id) if j.inspection_id else None
        if decision and dec != decision:
            continue
        if severity and sev != severity:
            continue
        items.append({
            "job_id": j.job_uid,
            "original_filename": j.original_filename,
            "execution_status": j.status,
            "inspection_id": f"INS-{j.inspection_id}" if j.inspection_id else None,
            "passed": (dec == "PASS") if dec is not None else None,
            "overall_decision": dec,
            "quality_score": int(round(insp.quality_score * 100)) if (insp and insp.quality_score is not None) else None,
            "severity": sev,
            "total_processing_ms": j.total_processing_ms,
            "error_code": j.error_code,
            "error_message": j.error_message,
        })

    total = len(items)
    return {
        "batch_id": batch.batch_uid,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items[offset : offset + limit],
    }


@router.post("/batches/{batch_uid}/pause")
def pause_batch(batch_uid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Pause dispatching new queued jobs for this batch (in-flight work finishes safely)."""
    batch = db.scalar(select(JobBatch).where(JobBatch.batch_uid == batch_uid))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch.is_paused = True
    recalculate_batch_status(db, batch.id)
    db.commit()
    return _batch_to_dict(db, batch)


@router.post("/batches/{batch_uid}/resume")
def resume_batch(batch_uid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Resume dispatching queued jobs for this batch."""
    batch = db.scalar(select(JobBatch).where(JobBatch.batch_uid == batch_uid))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch.is_paused = False
    recalculate_batch_status(db, batch.id)
    db.commit()
    return _batch_to_dict(db, batch)


@router.post("/batches/{batch_uid}/cancel")
def cancel_batch(batch_uid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Cancel all QUEUED jobs in this batch."""
    batch = db.scalar(select(JobBatch).where(JobBatch.batch_uid == batch_uid))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch.is_paused = False
    queued_jobs = list(
        db.scalars(
            select(InspectionJob).where(
                InspectionJob.batch_id == batch.id,
                InspectionJob.status == "QUEUED",
            )
        ).all()
    )
    now = datetime.now(timezone.utc)
    for j in queued_jobs:
        j.status = "CANCELLED"
        j.completed_at = now
    recalculate_batch_status(db, batch.id)
    db.commit()
    return _batch_to_dict(db, batch)


@router.post("/batches/{batch_uid}/retry")
def retry_batch_failures(batch_uid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Requeue eligible FAILED jobs in this batch."""
    batch = db.scalar(select(JobBatch).where(JobBatch.batch_uid == batch_uid))
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    failed_jobs = list(
        db.scalars(
            select(InspectionJob).where(
                InspectionJob.batch_id == batch.id,
                InspectionJob.status == "FAILED",
            )
        ).all()
    )
    for j in failed_jobs:
        j.status = "QUEUED"
        j.error_code = None
        j.error_message = None
        j.completed_at = None
    batch.completed_at = None
    recalculate_batch_status(db, batch.id)
    db.commit()
    return _batch_to_dict(db, batch)


@router.get("/engine/status")
def engine_status() -> dict[str, Any]:
    """Retrieve live engine health, worker state, queue depth, loaded models, and hardware usage."""
    return InspectionEngineWorker.get_engine_status()


@router.get("/engine/metrics")
def engine_metrics() -> dict[str, Any]:
    """Retrieve engine throughput, queue wait, P50/P95 latency, failure rate, and resource metrics."""
    return InspectionEngineWorker.get_engine_metrics()
