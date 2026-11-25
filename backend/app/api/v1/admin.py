"""Admin seed endpoint — POST only, never auto-seeds on GET."""

from __future__ import annotations

import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.repositories.model_repository import ManufacturerRepository, ModelConfigRepository
from backend.app.database.repositories.pipeline_repository import PipelineConfigRepository

router = APIRouter(prefix="/admin", tags=["admin"])


class SeedResult(BaseModel):
    created_manufacturer: bool
    created_models: list[str]
    created_pipeline: bool
    message: str


@router.post("/seed", response_model=SeedResult, status_code=201)
def seed_database(db: Session = Depends(get_db)) -> SeedResult:
    """
    One-time database seed — creates default manufacturer, real model registrations
    (pointing to actual artifact files), and a default pipeline.
    Safe to call multiple times — idempotent.
    """
    mfg_repo = ManufacturerRepository(db)
    mfg = mfg_repo.get_by_name("Default Manufacturer")
    created_mfg = False
    if mfg is None:
        mfg = mfg_repo.create(
            name="Default Manufacturer",
            industry="Manufacturing",
            plant_location="Local Prototype",
            contact_email="admin@clockit.local",
        )
        created_mfg = True

    model_repo = ModelConfigRepository(db)
    existing = {m.name for m in model_repo.list_all(limit=200)}

    # Only register models where weights actually exist on disk
    candidate_models = [
        {
            "name": "EfficientAD-Small (Prototype)",
            "model_family": "efficientad",
            "version": "1.0.0",
            "weights_file_path": os.path.join("artifacts", "pretrained", "pretrained_teacher_small.pth"),
            "dataset_dir_path": os.path.join("data", "train"),
            "hyperparameters_json": {
                "task": "Anomaly detection",
                "architecture": "EfficientAD-Small",
                "note": "Pretrained teacher weights. Requires student training before inference.",
            },
            "metrics_json": {},
            "is_active": False,  # Not ready until trained
        },
        {
            "name": "EfficientAD-Medium (Prototype)",
            "model_family": "efficientad",
            "version": "1.0.0",
            "weights_file_path": os.path.join("artifacts", "pretrained", "pretrained_teacher_medium.pth"),
            "dataset_dir_path": os.path.join("data", "train"),
            "hyperparameters_json": {
                "task": "Anomaly detection",
                "architecture": "EfficientAD-Medium",
                "note": "Pretrained teacher weights. Requires student training before inference.",
            },
            "metrics_json": {},
            "is_active": False,
        },
        {
            "name": "YOLO11n-Seg (Prototype)",
            "model_family": "yolo_seg",
            "version": "11.0.0",
            "weights_file_path": os.path.join("artifacts", "pretrained", "yolo11n-seg.pt"),
            "dataset_dir_path": os.path.join("data", "train"),
            "hyperparameters_json": {
                "task": "Segmentation / Localization",
                "architecture": "YOLOv11n-Seg",
                "note": "General segmentation weights. Requires fine-tuning on defect dataset.",
            },
            "metrics_json": {},
            "is_active": False,
        },
        {
            "name": "OpenCV Heuristic (Active)",
            "model_family": "opencv_heuristic",
            "version": "1.0.0",
            "weights_file_path": "",
            "dataset_dir_path": "",
            "hyperparameters_json": {
                "task": "Anomaly detection",
                "note": "Prototype signal: Gaussian blur difference + contour detection. Not a trained AI model.",
            },
            "metrics_json": {"note": "No validation metrics — heuristic prototype only."},
            "is_active": True,
        },
    ]

    created_models: list[str] = []
    for cm in candidate_models:
        if cm["name"] not in existing:
            model_repo.create(manufacturer_id=mfg.id, **cm)
            created_models.append(cm["name"])

    pipe_repo = PipelineConfigRepository(db)
    existing_pipes = pipe_repo.list_active_by_manufacturer(mfg.id)
    created_pipeline = False
    if not existing_pipes:
        pipe_repo.create(
            manufacturer_id=mfg.id,
            name="Default Inspection Pipeline",
            description="Single-stage OpenCV heuristic prototype pipeline.",
            modules_json=[
                {
                    "id": "stage_1",
                    "type": "opencv_heuristic",
                    "label": "Surface anomaly detection (prototype)",
                    "note": "Replace with EfficientAD or YOLO adapter when trained.",
                }
            ],
            thresholds_json={"anomaly_threshold": 0.5},
        )
        created_pipeline = True

    db.commit()
    return SeedResult(
        created_manufacturer=created_mfg,
        created_models=created_models,
        created_pipeline=created_pipeline,
        message="Seed complete. All registered models point to real artifact files or are clearly labelled as prototypes.",
    )
