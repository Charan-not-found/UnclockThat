"""Inspection submission, listing, and human review confirmation endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.database.connection import get_db
from backend.app.database.repositories.inspection_repository import (
    AnomalyResultRepository,
    InspectionRepository,
    SeverityScoreRepository,
)
from backend.app.database.repositories.model_repository import (
    ManufacturerRepository,
    ModelConfigRepository,
)
from backend.app.database.repositories.pipeline_repository import PipelineConfigRepository

router = APIRouter(prefix="/inspections", tags=["inspections"])


class BoxOut(BaseModel):
    x: int
    y: int
    w: int
    h: int


class DefectOut(BaseModel):
    type: str
    severity: str
    confidence: float
    anomalyScore: float
    box: BoxOut


class InspectionListItemOut(BaseModel):
    id: str
    date: str
    industry: str
    product: str
    pipeline: str
    status: str
    score: int
    severity: str
    defects: int


class InspectionRunOut(BaseModel):
    inspectionId: str
    score: int
    status: str
    defects: list[DefectOut]
    isMock: bool = False


def _ensure_manufacturer_and_pipeline(
    db: Session, industry: str, pipeline_name: str
) -> tuple[int, int]:
    mfg_repo = ManufacturerRepository(db)
    mfg = mfg_repo.get_by_name(f"{industry} Plant") or mfg_repo.get_by_name("Default Manufacturer")
    if mfg is None:
        mfg = mfg_repo.create(name=f"{industry} Plant", industry=industry)

    pipe_repo = PipelineConfigRepository(db)
    pipes = pipe_repo.list_active_by_manufacturer(mfg.id)
    if pipes:
        pipeline_id = pipes[0].id
    else:
        pipe = pipe_repo.create(
            manufacturer_id=mfg.id,
            name=pipeline_name,
            modules_json=[{"id": "anomaly_detection", "model": "PatchCore-v2"}],
        )
        pipeline_id = pipe.id
    return mfg.id, pipeline_id


def _analyze_image_bytes(raw_bytes: bytes, threshold: float) -> tuple[float, list[DefectOut]]:
    """Run lightweight OpenCV image anomaly heuristic on uploaded bytes."""
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.25, []

    # High-frequency local contrast deviation as an interpretable prototype signal
    blur = cv2.GaussianBlur(img, (15, 15), 0)
    diff = cv2.absdiff(img, blur)
    _, thresh_mask = cv2.threshold(diff, int(max(15, (1.0 - threshold) * 60)), 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h_img, w_img = img.shape[:2]
    total_area = max(1, h_img * w_img)
    defects: list[DefectOut] = []

    significant = sorted(contours, key=cv2.contourArea, reverse=True)[:3]
    for cnt in significant:
        area = cv2.contourArea(cnt)
        if area / total_area < 0.002:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        box = BoxOut(
            x=int(x / w_img * 100),
            y=int(y / h_img * 100),
            w=max(4, int(w / w_img * 100)),
            h=max(4, int(h / h_img * 100)),
        )
        area_ratio = area / total_area
        a_score = min(0.99, round(0.45 + area_ratio * 8.0, 2))
        sev = "high" if a_score >= 0.8 else "medium" if a_score >= 0.6 else "low"
        defects.append(
            DefectOut(
                type="Surface Irregularity",
                severity=sev,
                confidence=round(min(0.96, 0.65 + a_score * 0.3), 2),
                anomalyScore=a_score,
                box=box,
            )
        )

    max_anomaly = max((d.anomalyScore for d in defects), default=round(float(diff.mean()) / 255.0, 2))
    return max_anomaly, defects


@router.get("", response_model=list[InspectionListItemOut])
def list_inspections(db: Session = Depends(get_db)) -> list[InspectionListItemOut]:
    """List inspection records stored in SQLite."""
    records = InspectionRepository(db).list_all(limit=100)
    items: list[InspectionListItemOut] = []
    for rec in sorted(records, key=lambda r: r.inspected_at, reverse=True):
        detailed = InspectionRepository(db).get_with_results(rec.id)
        if detailed is None:
            continue
        mfg = ManufacturerRepository(db).get_by_id(detailed.manufacturer_id)
        pipe = (
            PipelineConfigRepository(db).get_by_id(detailed.pipeline_config_id)
            if detailed.pipeline_config_id
            else None
        )
        decision = (detailed.overall_decision or "PASS").lower()
        status = "review" if "review" in decision else ("fail" if decision == "fail" else "pass")
        severity = (
            detailed.severity_scores[0].severity_level.lower()
            if detailed.severity_scores
            else "none"
        )
        defect_count = sum(
            len(ar.bounding_boxes_json or []) for ar in detailed.anomaly_results
        )
        items.append(
            InspectionListItemOut(
                id=f"INS-{detailed.id}",
                date=detailed.inspected_at.isoformat(),
                industry=mfg.industry if mfg else "Manufacturing",
                product=detailed.product_serial,
                pipeline=pipe.name if pipe else "Default",
                status=status,
                score=int(round((detailed.quality_score or 0.9) * 100)),
                severity=severity,
                defects=defect_count,
            )
        )
    return items


@router.post("", response_model=InspectionRunOut)
async def run_inspection(
    industry: str = Form("Automotive"),
    product: str = Form("Brake disc"),
    pipelineId: str = Form("p1"),
    threshold: float = Form(0.5),
    fileName: str = Form("upload.png"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
) -> InspectionRunOut:
    """Save uploaded image to local storage, run prototype inspection, and persist to SQLite."""
    settings = get_settings()
    upload_dir = settings.storage_root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_ext = Path(fileName).suffix or ".png"
    stored_name = f"{uuid.uuid4().hex}{safe_ext}"
    stored_path = upload_dir / stored_name

    if file is not None:
        raw_bytes = await file.read()
        stored_path.write_bytes(raw_bytes)
        anomaly_score, defects = _analyze_image_bytes(raw_bytes, threshold)
    else:
        anomaly_score, defects = 0.2, []

    if anomaly_score >= max(0.75, threshold + 0.2):
        status = "fail"
        decision = "FAIL"
    elif anomaly_score >= threshold or defects:
        status = "review"
        decision = "REVIEW_REQUIRED"
    else:
        status = "pass"
        decision = "PASS"

    quality_score = max(0.05, min(0.99, round(1.0 - anomaly_score * 0.65, 2)))
    mfg_id, pipe_id = _ensure_manufacturer_and_pipeline(db, industry, pipelineId)

    insp = InspectionRepository(db).create(
        manufacturer_id=mfg_id,
        pipeline_config_id=pipe_id,
        product_serial=product,
        station_name="Web UI Station",
        image_file_path=str(stored_path),
        status="completed",
        overall_decision=decision,
        quality_score=quality_score,
        inspected_at=datetime.now(timezone.utc),
    )

    active_models = ModelConfigRepository(db).list_active_by_manufacturer(mfg_id)
    model_cfg_id = active_models[0].id if active_models else None

    ar = AnomalyResultRepository(db).create(
        inspection_id=insp.id,
        model_config_id=model_cfg_id,
        anomaly_score=anomaly_score,
        confidence_score=0.89,
        is_anomalous=bool(defects or anomaly_score >= threshold),
        bounding_boxes_json=[d.model_dump() for d in defects],
    )

    top_sev = defects[0].severity if defects else ("low" if status == "review" else "none")
    SeverityScoreRepository(db).create(
        inspection_id=insp.id,
        anomaly_result_id=ar.id,
        severity_level=top_sev,
        numeric_score=anomaly_score,
        requires_human_review=(status == "review"),
    )
    db.commit()

    return InspectionRunOut(
        inspectionId=f"INS-{insp.id}",
        score=int(round(quality_score * 100)),
        status=status,
        defects=defects,
        isMock=False,
    )


@router.post("/{inspection_id}/confirm")
def confirm_inspection(inspection_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    """Mark an inspection as human-reviewed."""
    numeric_id = int(inspection_id.replace("INS-", ""))
    repo = InspectionRepository(db)
    insp = repo.get_with_results(numeric_id)
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    for sev in insp.severity_scores:
        sev.requires_human_review = False
        sev.rule_notes = "Confirmed by operator via Web UI"
    db.commit()
    return {"status": "confirmed", "inspectionId": inspection_id}
