"""Training job orchestration endpoints — real background execution, live progress, dataset validation."""

from __future__ import annotations

import os
import shutil
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import BASE_DIR, get_settings
from backend.app.database.connection import SessionLocal, get_db
from backend.app.database.models.model_config import ModelConfig
from backend.app.database.models.scanner import AnalysisModule, DatasetRecord, ScannerUnit, TrainingRun
from backend.app.models.catalogue import get_model_capability

router = APIRouter(prefix="/training-jobs", tags=["training"])

_train_lock = threading.Lock()
_queue_lock = threading.Lock()
_train_queue: deque[tuple[str, Any]] = deque()
_queue_worker_active = False
_cancelled_jobs: set[int] = set()


class _TrainingCancelledError(Exception):
    """Raised inside a running training job when cancelled by user."""


def _check_cancelled(job_id: int) -> None:
    with _queue_lock:
        if job_id in _cancelled_jobs:
            raise _TrainingCancelledError("Training cancelled by user.")


def _is_job_cancelled(job_id: int) -> bool:
    db = SessionLocal()
    try:
        r = db.get(TrainingRun, job_id)
        return r is None or r.status == "Cancelled"
    finally:
        with _queue_lock:
            _cancelled_jobs.discard(job_id)
        db.close()


def _training_queue_worker() -> None:
    global _queue_worker_active
    while True:
        with _queue_lock:
            if not _train_queue:
                _queue_worker_active = False
                return
            kind, payload = _train_queue.popleft()

        with _train_lock:
            if kind == "single":
                if not _is_job_cancelled(payload):
                    _run_efficientad_job(payload, release_lock=False)
            elif kind == "chained":
                for jid in payload:
                    if not _is_job_cancelled(jid):
                        _run_efficientad_job(jid, release_lock=False)
            elif kind == "simultaneous":
                threads = [
                    threading.Thread(target=_run_efficientad_job, args=(jid, False), daemon=True)
                    for jid in payload
                    if not _is_job_cancelled(jid)
                ]
                for th in threads:
                    th.start()
                for th in threads:
                    th.join()


def _enqueue_training(kind: str, payload: Any) -> int:
    """Append a single or batch training request to the FIFO queue and ensure worker is running."""
    global _queue_worker_active
    with _queue_lock:
        _train_queue.append((kind, payload))
        q_len = len(_train_queue)
        if not _queue_worker_active:
            _queue_worker_active = True
            t = threading.Thread(target=_training_queue_worker, name="clockit-train-queue", daemon=True)
            t.start()
        return q_len


class TrainingJobIn(BaseModel):
    model_key: str = "efficientad_small"
    scanner_unit_id: Optional[int] = None
    module_id: Optional[int] = None
    dataset_id: Optional[int] = None
    strategy: str = "initial_training"
    max_epochs: int = Field(default=2, ge=1, le=50)
    limit_train_batches: int = Field(default=50, ge=5, le=2000)


class TrainingJobOut(BaseModel):
    id: int
    scanner_unit_id: Optional[int]
    scanner_unit_name: Optional[str] = None
    module_id: Optional[int]
    module_name: Optional[str] = None
    dataset_id: Optional[int]
    model_key: str
    strategy: str
    status: str
    progress_pct: int
    current_step: str
    logs: list[str]
    max_epochs: int
    limit_train_batches: int
    metrics: Optional[dict[str, Any]]
    checkpoint_path: Optional[str]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str


def _to_out(r: TrainingRun) -> TrainingJobOut:
    from sqlalchemy.orm import object_session

    sess = object_session(r)
    unit_name = None
    mod_name = None
    if sess is not None:
        if r.scanner_unit_id:
            u = sess.get(ScannerUnit, r.scanner_unit_id)
            if u:
                unit_name = u.name
        if r.module_id:
            m = sess.get(AnalysisModule, r.module_id)
            if m:
                mod_name = m.name

    return TrainingJobOut(
        id=r.id,
        scanner_unit_id=r.scanner_unit_id,
        scanner_unit_name=unit_name,
        module_id=r.module_id,
        module_name=mod_name,
        dataset_id=r.dataset_id,
        model_key=r.model_key,
        strategy=r.strategy,
        status=r.status,
        progress_pct=r.progress_pct,
        current_step=r.current_step,
        logs=list(r.logs_json or []),
        max_epochs=r.max_epochs,
        limit_train_batches=r.limit_train_batches,
        metrics=r.metrics_json,
        checkpoint_path=r.checkpoint_path,
        error_message=r.error_message,
        started_at=r.started_at.isoformat() if r.started_at else None,
        completed_at=r.completed_at.isoformat() if r.completed_at else None,
        created_at=r.created_at.isoformat(),
    )


def _update_progress(db: Session, job_id: int, pct: int, step: str, log_line: Optional[str] = None) -> None:
    run = db.get(TrainingRun, job_id)
    if not run:
        return
    run.progress_pct = max(0, min(100, pct))
    run.current_step = step
    if log_line:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        logs = list(run.logs_json or [])
        logs.append(f"[{ts}] {log_line}")
        run.logs_json = logs[-100:]
    db.commit()


def _run_efficientad_job(job_id: int, release_lock: bool = True) -> None:
    """Execute real training job in a background thread with live step updates."""
    db = SessionLocal()
    try:
        run = db.get(TrainingRun, job_id)
        if run is None:
            return
        run.status = "Running"
        run.started_at = datetime.now(timezone.utc)
        if run.module_id:
            mod = db.get(AnalysisModule, run.module_id)
            if mod:
                mod.state = "Training"
        db.commit()
        _update_progress(db, job_id, 5, "Initializing environment", f"Starting {run.model_key} training job.")

        settings = get_settings()
        tmp_dir = settings.storage_root / "temporary"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(tmp_dir / "mpl"))
        os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

        import torch
        import lightning.pytorch as pl
        from anomalib.data import Folder
        from anomalib.engine import Engine
        from anomalib.models.image.efficient_ad.lightning_model import (
            EfficientAd,
            get_pretrained_weights_dir,
        )

        use_cuda = torch.cuda.is_available()
        device_label = f"GPU ({torch.cuda.get_device_name(0)})" if use_cuda else "CPU"
        ckpt_dir = BASE_DIR / "artifacts" / "checkpoints" / f"run_{job_id}"
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        ds = db.get(DatasetRecord, run.dataset_id) if run.dataset_id else None
        if ds is None or not Path(ds.extracted_path).is_dir() or ds.valid_image_count <= 0:
            raise ValueError("Training issue: Uploaded dataset is missing, empty, or has no valid images.")

        ds_root = Path(ds.extracted_path)
        _update_progress(db, job_id, 15, "Loading validated dataset", f"Loaded dataset '{ds.name}' ({ds.valid_image_count} valid images).")

        if run.model_key == "anomalydino":
            from backend.app.models.anomalydino_adapter import AnomalyDINOAdapter

            trained_dir = BASE_DIR / "models" / "custom"
            trained_dir.mkdir(parents=True, exist_ok=True)
            if run.module_id:
                mod_obj = db.get(AnalysisModule, run.module_id)
                cloned_rel = (mod_obj.config_json or {}).get("cloned_weights_path") if mod_obj else None
                out_ckpt = (BASE_DIR / cloned_rel) if cloned_rel else (trained_dir / f"module_{run.module_id}_anomalydino.pt")
            else:
                out_ckpt = trained_dir / f"run_{job_id}_anomalydino.pt"

            _update_progress(db, job_id, 22, f"Building AnomalyDINO memory bank on {device_label}", "Extracting DINOv2 patch tokens (with PCA masking)...")
            metrics = AnomalyDINOAdapter.fit_dataset(
                dataset_dir=ds_root,
                out_path=out_ckpt,
                progress_cb=lambda pct, msg: (_check_cancelled(job_id), _update_progress(db, job_id, pct, msg, msg)),
            )
            run = db.get(TrainingRun, job_id)
            if run:
                run.status = "Completed"
                run.progress_pct = 100
                run.current_step = "Completed"
                logs = list(run.logs_json or [])
                ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
                logs.append(f"[{ts}] AnomalyDINO bank built ({metrics.get('memory_bank_patches')} patches, PCA mask={metrics.get('pca_masking_enabled')}) -> {out_ckpt.relative_to(BASE_DIR)}")
                run.logs_json = logs[-100:]
                run.metrics_json = metrics
                run.checkpoint_path = str(out_ckpt.relative_to(BASE_DIR))
                run.completed_at = datetime.now(timezone.utc)
            if run and run.module_id:
                mod = db.get(AnalysisModule, run.module_id)
                if mod:
                    mod.state = "Ready"
                    mod.dataset_id = run.dataset_id
                    mc_id = (mod.config_json or {}).get("cloned_model_config_id")
                    if mc_id:
                        mc = db.get(ModelConfig, mc_id)
                        if mc:
                            mc.is_active = True
                            mc.metrics_json = metrics
                            mc.weights_file_path = str(out_ckpt.relative_to(BASE_DIR))
                    if mod.scanner_unit_id:
                        unit = db.get(ScannerUnit, mod.scanner_unit_id)
                        if unit:
                            unit.status = "Ready"
            db.commit()
            return

        if run.model_key == "omniposead":
            from backend.app.models.omnipose_adapter import OmniPoseAdapter

            trained_dir = BASE_DIR / "models" / "custom"
            trained_dir.mkdir(parents=True, exist_ok=True)
            if run.module_id:
                mod_obj = db.get(AnalysisModule, run.module_id)
                cloned_rel = (mod_obj.config_json or {}).get("cloned_weights_path") if mod_obj else None
                out_ckpt = (BASE_DIR / cloned_rel) if cloned_rel else (trained_dir / f"module_{run.module_id}_omniposead.pt")
            else:
                out_ckpt = trained_dir / f"run_{job_id}_omniposead.pt"

            _update_progress(db, job_id, 22, f"Indexing multi-view reference bank on {device_label}", "Extracting DINOv2 pose-agnostic features...")
            metrics = OmniPoseAdapter.fit_dataset(
                dataset_dir=ds_root,
                out_path=out_ckpt,
                progress_cb=lambda pct, msg: (_check_cancelled(job_id), _update_progress(db, job_id, pct, msg, msg)),
            )
            run = db.get(TrainingRun, job_id)
            if run:
                run.status = "Completed"
                run.progress_pct = 100
                run.current_step = "Completed"
                logs = list(run.logs_json or [])
                ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
                logs.append(f"[{ts}] OmniPoseAD bank built ({metrics.get('reference_views_indexed')} views) -> {out_ckpt.relative_to(BASE_DIR)}")
                run.logs_json = logs[-100:]
                run.metrics_json = metrics
                run.checkpoint_path = str(out_ckpt.relative_to(BASE_DIR))
                run.completed_at = datetime.now(timezone.utc)
            if run and run.module_id:
                mod = db.get(AnalysisModule, run.module_id)
                if mod:
                    mod.state = "Ready"
                    mod.dataset_id = run.dataset_id
                    mc_id = (mod.config_json or {}).get("cloned_model_config_id")
                    if mc_id:
                        mc = db.get(ModelConfig, mc_id)
                        if mc:
                            mc.is_active = True
                            mc.metrics_json = metrics
                            mc.weights_file_path = str(out_ckpt.relative_to(BASE_DIR))
                    if mod.scanner_unit_id:
                        unit = db.get(ScannerUnit, mod.scanner_unit_id)
                        if unit:
                            unit.status = "Ready"
            db.commit()
            return

        if run.model_key == "patchcore":
            from anomalib.models import Patchcore
            _update_progress(db, job_id, 15, f"Initializing PatchCore (WideResNet-50) on {device_label}", f"Using {device_label} with PatchCore coreset memory bank.")
            model = Patchcore(backbone="wide_resnet50_2", coreset_sampling_ratio=0.1)
            effective_epochs = 1
        elif run.model_key == "dinomaly":
            from anomalib.models import Dinomaly
            _update_progress(db, job_id, 15, f"Initializing Dinomaly (DINOv2 ViT) on {device_label}", f"Using {device_label} with Dinomaly ViT-B/14.")
            model = Dinomaly()
            effective_epochs = run.max_epochs
        else:
            model_size = "medium" if run.model_key == "efficientad_medium" else "small"
            teacher_filename = f"pretrained_teacher_{model_size}.pth"
            _update_progress(db, job_id, 12, f"Preparing {teacher_filename} on {device_label}", f"Using {device_label}. Checking local {teacher_filename}...")
            local_weights = BASE_DIR / "models" / "base" / teacher_filename
            if not local_weights.is_file():
                raise FileNotFoundError(f"Missing pretrained weights at {local_weights}")
            target_dir = get_pretrained_weights_dir() / "efficientad_pretrained_weights"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / teacher_filename
            if not target_file.is_file():
                shutil.copy2(local_weights, target_file)
            aux_dir = tmp_dir / "aux_imagenette"
            aux_class = aux_dir / "aux_class"
            if not aux_class.is_dir() or not any(aux_class.iterdir()):
                aux_class.mkdir(parents=True, exist_ok=True)
                ds_tmp = db.get(DatasetRecord, run.dataset_id) if run.dataset_id else None
                if ds_tmp and Path(ds_tmp.extracted_path).is_dir():
                    for i, p in enumerate(sorted(Path(ds_tmp.extracted_path).rglob("*.*"))):
                        if i >= 40:
                            break
                        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
                            shutil.copy2(p, aux_class / p.name)
            model = EfficientAd(model_size=model_size, imagenet_dir=str(aux_dir))
            effective_epochs = run.max_epochs

        # Aux imagenette prep for EfficientAD

        # Prepare local auxiliary images using a small subset of dataset images if needed
        aux_dir = tmp_dir / "aux_imagenette"
        aux_class = aux_dir / "aux_class"
        if not aux_class.is_dir() or not any(aux_class.iterdir()):
            aux_class.mkdir(parents=True, exist_ok=True)
            for i, p in enumerate(sorted(ds_root.rglob("*.*"))):
                if i >= 40:
                    break
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
                    shutil.copy2(p, aux_class / p.name)

        normal_sub = "normal" if (ds_root / "normal").is_dir() else "."
        datamodule = Folder(
            name=f"dataset_{ds.id}",
            root=ds_root,
            normal_dir=normal_sub,
            train_batch_size=1,
            eval_batch_size=8,
            num_workers=0,
        )

        class _ProgressCallback(pl.Callback):
            def on_train_epoch_start(self, trainer, pl_module):
                _check_cancelled(job_id)
                ep = trainer.current_epoch + 1
                pct = 25 + int((trainer.current_epoch / max(1, run.max_epochs)) * 55)
                _update_progress(db, job_id, pct, f"Training epoch {ep}/{run.max_epochs}", f"Epoch {ep}/{run.max_epochs} started.")

            def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
                with _queue_lock:
                    if job_id in _cancelled_jobs:
                        trainer.should_stop = True
                        raise _TrainingCancelledError("Training cancelled by user.")

            def on_train_epoch_end(self, trainer, pl_module):
                _check_cancelled(job_id)
                ep = trainer.current_epoch + 1
                pct = 25 + int((ep / max(1, run.max_epochs)) * 55)
                _update_progress(db, job_id, pct, f"Completed epoch {ep}/{run.max_epochs}", f"Epoch {ep}/{run.max_epochs} finished.")

        engine = Engine(
            default_root_dir=str(ckpt_dir),
            max_epochs=effective_epochs,
            limit_train_batches=run.limit_train_batches,
            limit_val_batches=15,
            limit_test_batches=15,
            accelerator="gpu" if use_cuda else "cpu",
            devices=1,
            logger=False,
            enable_progress_bar=False,
            callbacks=[_ProgressCallback()],
        )

        _update_progress(db, job_id, 25, "Fitting EfficientAD student & autoencoder", "Running teacher stats and training epochs...")
        engine.fit(model=model, datamodule=datamodule)

        _update_progress(db, job_id, 85, "Evaluating trained model", "Running evaluation on validation/test split...")
        metrics: dict[str, Any] = {}
        try:
            test_results = engine.test(model=model, datamodule=datamodule)
            if test_results:
                for k, v in test_results[0].items():
                    metrics[k] = round(float(v), 4) if isinstance(v, (int, float)) else v
        except Exception as test_exc:
            metrics["evaluation_note"] = f"Normal-only dataset ({test_exc})"

        _update_progress(db, job_id, 95, "Saving trained checkpoint", "Exporting module checkpoint...")
        trained_dir = BASE_DIR / "models" / "custom"
        trained_dir.mkdir(parents=True, exist_ok=True)
        if run.module_id:
            mod_obj = db.get(AnalysisModule, run.module_id)
            cloned_rel = (mod_obj.config_json or {}).get("cloned_weights_path") if mod_obj else None
            out_ckpt = (BASE_DIR / cloned_rel) if cloned_rel else (trained_dir / f"module_{run.module_id}_{run.model_key}.ckpt")
        else:
            out_ckpt = trained_dir / f"run_{job_id}_{run.model_key}.ckpt"

        out_ckpt.parent.mkdir(parents=True, exist_ok=True)
        best_ckpt = getattr(engine.trainer.checkpoint_callback, "best_model_path", "")
        if best_ckpt and Path(best_ckpt).is_file():
            shutil.copy2(best_ckpt, out_ckpt)
        else:
            engine.trainer.save_checkpoint(str(out_ckpt))

        run = db.get(TrainingRun, job_id)
        if run:
            run.status = "Completed"
            run.progress_pct = 100
            run.current_step = "Completed"
            logs = list(run.logs_json or [])
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            logs.append(f"[{ts}] Training complete. Saved checkpoint -> {out_ckpt.relative_to(BASE_DIR)}")
            run.logs_json = logs[-100:]
            run.metrics_json = metrics
            run.checkpoint_path = str(out_ckpt.relative_to(BASE_DIR))
            run.completed_at = datetime.now(timezone.utc)

        if run and run.module_id:
            mod = db.get(AnalysisModule, run.module_id)
            if mod:
                mod.state = "Ready"
                mod.dataset_id = run.dataset_id
                mc_id = (mod.config_json or {}).get("cloned_model_config_id")
                if mc_id:
                    mc = db.get(ModelConfig, mc_id)
                    if mc:
                        mc.is_active = True
                        mc.metrics_json = metrics
                        mc.weights_file_path = str(out_ckpt.relative_to(BASE_DIR))
                if mod.scanner_unit_id:
                    unit = db.get(ScannerUnit, mod.scanner_unit_id)
                    if unit:
                        unit.status = "Ready"
        db.commit()
    except _TrainingCancelledError:
        db.rollback()
        run = db.get(TrainingRun, job_id)
        if run:
            run.status = "Cancelled"
            run.current_step = "Cancelled"
            logs = list(run.logs_json or [])
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            logs.append(f"[{ts}] Training cancelled by user.")
            run.logs_json = logs[-100:]
            run.completed_at = datetime.now(timezone.utc)
            if run.module_id:
                mod = db.get(AnalysisModule, run.module_id)
                if mod and mod.state == "Training":
                    mod.state = "Configured"
            db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(TrainingRun, job_id)
        if run:
            run.status = "Failed"
            run.current_step = "Failed"
            run.error_message = str(exc)
            logs = list(run.logs_json or [])
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            logs.append(f"[{ts}] ERROR: {exc}")
            run.logs_json = logs[-100:]
            run.completed_at = datetime.now(timezone.utc)
            if run.module_id:
                mod = db.get(AnalysisModule, run.module_id)
                if mod:
                    mod.state = "Failed"
            db.commit()
    finally:
        with _queue_lock:
            _cancelled_jobs.discard(job_id)
        db.close()
        if release_lock and _train_lock.locked():
            _train_lock.release()


def _run_chained_batch(job_ids: list[int]) -> None:
    """Run multiple training jobs sequentially (one-by-one) and release lock at the end."""
    try:
        for jid in job_ids:
            _run_efficientad_job(jid, release_lock=False)
    finally:
        if _train_lock.locked():
            _train_lock.release()


@router.get("", response_model=list[TrainingJobOut])
def list_training_jobs(db: Session = Depends(get_db)) -> list[TrainingJobOut]:
    rows = db.scalars(select(TrainingRun).order_by(TrainingRun.created_at.desc())).all()
    return [_to_out(r) for r in rows]


@router.get("/{job_id}", response_model=TrainingJobOut)
def get_training_job(job_id: int, db: Session = Depends(get_db)) -> TrainingJobOut:
    row = db.get(TrainingRun, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Training job not found")
    return _to_out(row)


@router.post("/{job_id}/cancel", response_model=TrainingJobOut)
def cancel_training_job(job_id: int, db: Session = Depends(get_db)) -> TrainingJobOut:
    """Cancel a queued or running training job."""
    row = db.get(TrainingRun, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Training job not found")
    if row.status not in ("Queued", "Running"):
        raise HTTPException(status_code=422, detail=f"Only Queued or Running jobs can be cancelled (current: {row.status}).")

    logs = list(row.logs_json or [])
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    if row.status == "Queued":
        row.status = "Cancelled"
        row.current_step = "Cancelled"
        row.completed_at = datetime.now(timezone.utc)
        logs.append(f"[{ts}] Job cancelled by user while in queue.")
    else:
        with _queue_lock:
            _cancelled_jobs.add(job_id)
        row.current_step = "Cancelling..."
        logs.append(f"[{ts}] Cancellation requested by user...")
    row.logs_json = logs[-100:]
    db.commit()
    db.refresh(row)
    return _to_out(row)


class BatchTrainingJobIn(BaseModel):
    scanner_unit_id: int
    dataset_id: Optional[int] = None
    mode: str = "chained"  # "chained" (one-by-one) or "simultaneous" (parallel)
    max_epochs: int = Field(default=2, ge=1, le=50)
    limit_train_batches: int = Field(default=50, ge=5, le=2000)


@router.post("/batch", response_model=list[TrainingJobOut], status_code=201)
def start_batch_training(body: BatchTrainingJobIn, db: Session = Depends(get_db)) -> list[TrainingJobOut]:
    """Train all trainable Analysis Modules in a Scanner Unit (chained one-by-one or simultaneous)."""
    if body.mode not in ("chained", "simultaneous"):
        raise HTTPException(status_code=422, detail="mode must be 'chained' or 'simultaneous'")

    unit = db.get(ScannerUnit, body.scanner_unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Scanner Unit not found")

    trainable_keys = {"patchcore", "dinomaly", "omniposead", "anomalydino", "efficientad_small", "efficientad_medium"}
    mods = [m for m in unit.modules if m.model_key in trainable_keys]
    if not mods:
        raise HTTPException(status_code=422, detail=f"Scanner Unit '{unit.name}' has no trainable modules.")

    # Validate every module has an enabled model and valid dataset before launching
    prepared: list[tuple[AnalysisModule, DatasetRecord]] = []
    for mod in mods:
        cap = get_model_capability(mod.model_key)
        if cap is None or not cap.get("is_enabled", True):
            raise HTTPException(
                status_code=422,
                detail=f"Module '{mod.name}' uses '{mod.model_key}' which is disabled in Settings.",
            )
        eff_ds_id = mod.dataset_id or body.dataset_id
        if eff_ds_id is None:
            raise HTTPException(
                status_code=422,
                detail=f"Training issue: Module '{mod.name}' has no dataset assigned. Select or assign a dataset first.",
            )
        ds = db.get(DatasetRecord, eff_ds_id)
        if ds is None or ds.validation_status != "Validated" or ds.valid_image_count <= 0:
            raise HTTPException(
                status_code=422,
                detail=f"Training issue: Dataset for module '{mod.name}' is missing, empty, or invalid.",
            )
        prepared.append((mod, ds))

    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    is_busy = _train_lock.locked()
    runs: list[TrainingRun] = []
    for mod, ds in prepared:
        run = TrainingRun(
            scanner_unit_id=unit.id,
            module_id=mod.id,
            dataset_id=ds.id,
            model_key=mod.model_key,
            strategy="initial_training",
            status="Queued",
            progress_pct=0,
            current_step=f"Queued ({body.mode} · waiting)" if is_busy else f"Queued ({body.mode})",
            logs_json=[f"[{ts}] Queued ({body.mode}) for module '{mod.name}' with dataset '{ds.name}' ({ds.valid_image_count} images)."],
            max_epochs=body.max_epochs,
            limit_train_batches=body.limit_train_batches,
        )
        db.add(run)
        runs.append(run)
    db.commit()
    for r in runs:
        db.refresh(r)

    job_ids = [r.id for r in runs]
    _enqueue_training("chained" if body.mode == "chained" else "simultaneous", job_ids)
    return [_to_out(r) for r in runs]


@router.post("", response_model=TrainingJobOut, status_code=201)
def start_training_job(body: TrainingJobIn, db: Session = Depends(get_db)) -> TrainingJobOut:
    cap = get_model_capability(body.model_key)
    if cap is None:
        raise HTTPException(status_code=422, detail=f"Unknown model_key: {body.model_key}")
    if not cap.get("is_enabled", True):
        raise HTTPException(
            status_code=422,
            detail=f"Model '{cap['display_name']}' is currently disabled in Settings.",
        )
    if body.strategy not in cap["supported_training_strategies"]:
        raise HTTPException(
            status_code=422,
            detail=f"Model '{cap['display_name']}' does not support training strategy '{body.strategy}'.",
        )
    if body.model_key not in ("efficientad_small", "efficientad_medium", "patchcore", "dinomaly", "omniposead", "anomalydino"):
        raise HTTPException(
            status_code=422,
            detail="Training runner supports 'patchcore', 'dinomaly', 'omniposead', 'anomalydino', 'efficientad_small', and 'efficientad_medium'.",
        )

    # If training a specific Analysis Module, default to that module's dataset_id
    effective_dataset_id = body.dataset_id
    if body.module_id is not None:
        mod = db.get(AnalysisModule, body.module_id)
        if mod is None:
            raise HTTPException(status_code=404, detail="Analysis Module not found")
        if effective_dataset_id is None:
            effective_dataset_id = mod.dataset_id

    # Strict dataset check: reject missing, unvalidated, or empty ZIP/datasets
    if effective_dataset_id is None:
        raise HTTPException(
            status_code=422,
            detail="Training issue: No dataset uploaded or selected. Please upload a non-empty .zip or image dataset first.",
        )
    ds = db.get(DatasetRecord, effective_dataset_id)
    if ds is None:
        raise HTTPException(
            status_code=404,
            detail="Training issue: Selected dataset was not found.",
        )
    if ds.validation_status != "Validated" or ds.valid_image_count <= 0:
        raise HTTPException(
            status_code=422,
            detail=f"Training issue: Dataset '{ds.name}' is empty or failed validation ({ds.valid_image_count} valid images). Upload a valid non-empty .zip or image files.",
        )

    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    is_busy = _train_lock.locked()
    run = TrainingRun(
        scanner_unit_id=body.scanner_unit_id,
        module_id=body.module_id,
        dataset_id=effective_dataset_id,
        model_key=body.model_key,
        strategy=body.strategy,
        status="Queued",
        progress_pct=0,
        current_step="Queued (waiting in queue)" if is_busy else "Queued",
        logs_json=[f"[{ts}] Job queued for dataset '{ds.name}' ({ds.valid_image_count} images)."],
        max_epochs=body.max_epochs,
        limit_train_batches=body.limit_train_batches,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    _enqueue_training("single", run.id)
    return _to_out(run)
