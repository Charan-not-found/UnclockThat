"""Model catalog and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.repositories.model_repository import (
    ManufacturerRepository,
    ModelConfigRepository,
)

router = APIRouter(prefix="/models", tags=["models"])


class ModelInfoOut(BaseModel):
    """Frontend-compatible model metadata."""

    id: str
    name: str
    task: str
    version: str
    enabled: bool
    accuracy: float


def _to_model_info(m) -> ModelInfoOut:
    metrics = m.metrics_json or {}
    hyper = m.hyperparameters_json or {}
    return ModelInfoOut(
        id=str(m.id),
        name=m.name,
        task=str(hyper.get("task", m.model_family)),
        version=m.version,
        enabled=m.is_active,
        accuracy=float(metrics.get("accuracy", 90.0)),
    )


def _ensure_default_models(db: Session) -> None:
    """Seed default manufacturer and model configs if none exist yet."""
    mfg_repo = ManufacturerRepository(db)
    mfg = mfg_repo.get_by_name("Default Manufacturer")
    if mfg is None:
        mfg = mfg_repo.create(
            name="Default Manufacturer",
            industry="Automotive",
            plant_location="Local Prototype",
        )

    model_repo = ModelConfigRepository(db)
    if not model_repo.list_all(limit=1):
        defaults = [
            {
                "name": "PatchCore-v2",
                "model_family": "patchcore",
                "version": "2.1.0",
                "dataset_dir_path": "data/raw/default",
                "weights_file_path": "artifacts/pretrained/patchcore_v2.pt",
                "hyperparameters_json": {"task": "Anomaly detection"},
                "metrics_json": {"accuracy": 96.4},
                "is_active": True,
            },
            {
                "name": "DefectNet",
                "model_family": "mobilenet",
                "version": "1.4.2",
                "dataset_dir_path": "data/raw/default",
                "weights_file_path": "artifacts/pretrained/defectnet.pt",
                "hyperparameters_json": {"task": "Defect classification"},
                "metrics_json": {"accuracy": 92.1},
                "is_active": True,
            },
            {
                "name": "SegLocalizer",
                "model_family": "yolo_seg",
                "version": "0.9.0",
                "dataset_dir_path": "data/raw/default",
                "weights_file_path": "artifacts/pretrained/seglocalizer.pt",
                "hyperparameters_json": {"task": "Localization"},
                "metrics_json": {"accuracy": 88.7},
                "is_active": False,
            },
        ]
        for item in defaults:
            model_repo.create(manufacturer_id=mfg.id, **item)
        db.commit()


@router.get("", response_model=list[ModelInfoOut])
def list_models(db: Session = Depends(get_db)) -> list[ModelInfoOut]:
    """List registered AI models."""
    _ensure_default_models(db)
    models = ModelConfigRepository(db).list_all(limit=100)
    return [_to_model_info(m) for m in models]


@router.patch("/{model_id}/toggle", response_model=ModelInfoOut)
def toggle_model(model_id: int, db: Session = Depends(get_db)) -> ModelInfoOut:
    """Enable or disable a registered model."""
    repo = ModelConfigRepository(db)
    model = repo.get_by_id(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    updated = repo.update(model, is_active=not model.is_active)
    db.commit()
    return _to_model_info(updated)
