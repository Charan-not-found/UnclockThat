"""Inspection submission, listing, detail, and human review endpoints."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import BASE_DIR, get_settings
from backend.app.database.connection import get_db
from backend.app.database.models.scanner import CorrectionRecord, ScannerUnit
from backend.app.engine.inference_scheduler import GpuInferenceScheduler, ModuleSpec
from backend.app.engine.result_aggregator import aggregate_and_persist_result
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

# ---------------------------------------------------------------------------
# Spec-correct vocabulary
# ---------------------------------------------------------------------------
# Severity: Informational / Minor / Major / Critical  (not low/medium/high)
# Status: Completed / Needs review / Approved / Rejected / Failed

def _anomaly_to_severity(anomaly_score: float) -> str:
    if anomaly_score >= 0.85:
        return "Critical"
    if anomaly_score >= 0.65:
        return "Major"
    if anomaly_score >= 0.45:
        return "Minor"
    return "Informational"


def _decision_to_status(decision: str) -> str:
    mapping = {
        "PASS": "Completed",
        "FAIL": "Failed",
        "REVIEW_REQUIRED": "Needs review",
    }
    return mapping.get(decision, "Completed")


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------

class BoxOut(BaseModel):
    x: int
    y: int
    w: int
    h: int


class DefectOut(BaseModel):
    type: str
    severity: str         # Informational / Minor / Major / Critical
    confidence: float
    anomalyScore: float
    box: BoxOut


class AnomalyResultOut(BaseModel):
    id: str
    model_name: str
    anomaly_score: float
    confidence_score: float
    is_anomalous: bool
    severity: str
    defects: list[DefectOut]
    heatmap_path: Optional[str] = None
    heatmap_url: Optional[str] = None
    processing_time_ms: Optional[float] = None


class InspectionDetailOut(BaseModel):
    id: str
    date: str
    industry: str
    product: str
    station: str
    pipeline: str
    pipeline_id: Optional[str]
    status: str            # spec vocabulary
    overall_decision: str  # PASS / FAIL / REVIEW_REQUIRED
    quality_score: int
    severity: str          # top-level severity label
    image_path: str
    image_url: Optional[str] = None
    model_used: Optional[str] = None
    module_results: list["ModuleScanResultOut"] = []
    weighted_outputs: list["WeightedOutputOut"] = []
    distinct_outputs: dict[str, Any] = {}
    requires_review: bool
    review_note: Optional[str]
    anomaly_results: list[AnomalyResultOut]


class InspectionListItemOut(BaseModel):
    id: str
    date: str
    industry: str
    product: str
    station: str
    pipeline: str
    status: str
    quality_score: int
    severity: str
    defect_count: int
    requires_review: bool


class ModuleScanResultOut(BaseModel):
    module_id: int
    module_name: str
    model_key: str
    model_display_name: str
    weight: int
    weight_ratio: float
    selected_outputs: list[str] = []
    anomaly_score: float
    confidence_score: float
    defects: list[DefectOut] = []
    defect_classes: list[str] = []
    heatmap_url: Optional[str] = None
    processing_time_ms: Optional[float] = None


class WeightedOutputOut(BaseModel):
    output_key: str
    label: str
    weighted_value: float
    weights_used: list[dict[str, Any]] = []


class InspectionRunOut(BaseModel):
    inspectionId: str
    passed: bool
    quality_score: int
    status: str
    overall_decision: str
    severity: str
    defects: list[DefectOut]
    model_used: str = "OpenCV Heuristic"
    heatmap_url: Optional[str] = None
    module_results: list[ModuleScanResultOut] = []
    weighted_outputs: list[WeightedOutputOut] = []
    distinct_outputs: dict[str, Any] = {}
    # Legacy compat
    score: int
    isMock: bool = False


class ReviewIn(BaseModel):
    decision: str    # Approved / Rejected
    note: str
    feedback_category: str = "Correct detection"


class CorrectionOut(BaseModel):
    id: int
    inspection_id: str
    feedback_category: str
    original_decision: Optional[str]
    corrected_decision: str
    note: str
    saved_image_path: Optional[str]
    review_status: str
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
            modules_json=[{"id": "anomaly_detection", "type": "opencv_heuristic"}],
        )
        pipeline_id = pipe.id
    return mfg.id, pipeline_id


def _analyze_image_bytes(raw_bytes: bytes, threshold: float) -> tuple[float, list[DefectOut]]:
    """OpenCV heuristic prototype signal — clearly labelled, not a real AI model."""
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.25, []

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
        severity = _anomaly_to_severity(a_score)
        defects.append(
            DefectOut(
                type="Surface Irregularity",
                severity=severity,
                confidence=round(min(0.96, 0.65 + a_score * 0.3), 2),
                anomalyScore=a_score,
                box=box,
            )
        )

    max_anomaly = max(
        (d.anomalyScore for d in defects),
        default=round(float(diff.mean()) / 255.0, 2),
    )
    return max_anomaly, defects


def _build_detail(db: Session, inspection_id: int) -> Optional[InspectionDetailOut]:
    repo = InspectionRepository(db)
    rec = repo.get_with_results(inspection_id)
    if rec is None:
        return None

    mfg = ManufacturerRepository(db).get_by_id(rec.manufacturer_id)
    pipe = (
        PipelineConfigRepository(db).get_by_id(rec.pipeline_config_id)
        if rec.pipeline_config_id
        else None
    )

    top_sev = "Informational"
    requires_review = False
    review_note: Optional[str] = None
    for sev in rec.severity_scores:
        top_sev = sev.severity_level
        requires_review = sev.requires_human_review
        review_note = sev.rule_notes

    anomaly_outs: list[AnomalyResultOut] = []
    for ar in rec.anomaly_results:
        boxes = ar.bounding_boxes_json or []
        defects_out = []
        for d in boxes:
            defects_out.append(DefectOut(
                type=d.get("type", "Surface Irregularity"),
                severity=d.get("severity", "Informational"),
                confidence=d.get("confidence", 0.0),
                anomalyScore=d.get("anomalyScore", 0.0),
                box=BoxOut(**d["box"]) if "box" in d else BoxOut(x=0, y=0, w=10, h=10),
            ))
        model_name = "OpenCV Heuristic"
        if ar.model_config_id:
            mc = ModelConfigRepository(db).get_by_id(ar.model_config_id)
            if mc:
                model_name = mc.name

        heatmap_url = f"/results/{Path(ar.heatmap_file_path).name}" if ar.heatmap_file_path else None
        anomaly_outs.append(AnomalyResultOut(
            id=str(ar.id),
            model_name=model_name,
            anomaly_score=ar.anomaly_score,
            confidence_score=ar.confidence_score or 0.0,
            is_anomalous=ar.is_anomalous,
            severity=_anomaly_to_severity(ar.anomaly_score),
            defects=defects_out,
            heatmap_path=ar.heatmap_file_path,
            heatmap_url=heatmap_url,
            processing_time_ms=ar.processing_time_ms,
        ))

    norm_img_path = (rec.image_file_path or "").replace("\\", "/")
    if "/uploads/" in norm_img_path:
        img_url = "/uploads/" + norm_img_path.split("/uploads/", 1)[1]
    elif norm_img_path.startswith("uploads/"):
        img_url = "/" + norm_img_path
    elif norm_img_path:
        img_url = f"/uploads/{Path(norm_img_path).name}"
    else:
        img_url = None

    report_file = BASE_DIR / "outputs" / "reports" / f"INS-{rec.id}.json"
    report_data: dict[str, Any] = {}
    if report_file.is_file():
        try:
            report_data = json.loads(report_file.read_text(encoding="utf-8"))
        except Exception:
            report_data = {}

    model_used = report_data.get("model_used") or (
        " + ".join(a.model_name for a in anomaly_outs) if anomaly_outs else "OpenCV Heuristic"
    )
    mod_res = [ModuleScanResultOut(**m) for m in report_data.get("module_results", [])]
    w_outs = [WeightedOutputOut(**w) for w in report_data.get("weighted_outputs", [])]
    d_outs = report_data.get("distinct_outputs", {}) or {}

    decision = rec.overall_decision or "PASS"
    return InspectionDetailOut(
        id=f"INS-{rec.id}",
        date=rec.inspected_at.isoformat(),
        industry=mfg.industry if mfg else "Manufacturing",
        product=rec.product_serial,
        station=rec.station_name or "Web UI Station",
        pipeline=pipe.name if pipe else "Default",
        pipeline_id=str(rec.pipeline_config_id) if rec.pipeline_config_id else None,
        status=_decision_to_status(decision),
        overall_decision=decision,
        quality_score=int(round((rec.quality_score or 0.9) * 100)),
        severity=top_sev,
        image_path=rec.image_file_path,
        image_url=img_url,
        model_used=model_used,
        module_results=mod_res,
        weighted_outputs=w_outs,
        distinct_outputs=d_outs,
        requires_review=requires_review,
        review_note=review_note,
        anomaly_results=anomaly_outs,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[InspectionListItemOut])
def list_inspections(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[InspectionListItemOut]:
    """List inspection records. Server-side paginated, never creates records."""
    records = InspectionRepository(db).list_all(limit=limit)
    items: list[InspectionListItemOut] = []
    for rec in sorted(records, key=lambda r: r.inspected_at, reverse=True)[offset:offset + limit]:
        mfg = ManufacturerRepository(db).get_by_id(rec.manufacturer_id)
        pipe = (
            PipelineConfigRepository(db).get_by_id(rec.pipeline_config_id)
            if rec.pipeline_config_id
            else None
        )
        detailed = InspectionRepository(db).get_with_results(rec.id)
        if detailed is None:
            continue
        decision = (detailed.overall_decision or "PASS")
        item_status = _decision_to_status(decision)

        if status and item_status.lower().replace(" ", "_") != status.lower().replace(" ", "_"):
            continue

        top_sev = "Informational"
        requires_review = False
        for sev in detailed.severity_scores:
            top_sev = sev.severity_level
            requires_review = sev.requires_human_review

        defect_count = sum(len(ar.bounding_boxes_json or []) for ar in detailed.anomaly_results)
        items.append(InspectionListItemOut(
            id=f"INS-{detailed.id}",
            date=detailed.inspected_at.isoformat(),
            industry=mfg.industry if mfg else "Manufacturing",
            product=detailed.product_serial,
            station=detailed.station_name or "Web UI Station",
            pipeline=pipe.name if pipe else "Default",
            status=item_status,
            quality_score=int(round((detailed.quality_score or 0.9) * 100)),
            severity=top_sev,
            defect_count=defect_count,
            requires_review=requires_review,
        ))
    return items


@router.get("/review-queue", response_model=list[InspectionListItemOut])
def review_queue(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[InspectionListItemOut]:
    """Return inspections that require human review, ordered by severity then age."""
    sev_order = {"Critical": 0, "Major": 1, "Minor": 2, "Informational": 3}
    sev_records = SeverityScoreRepository(db).list_requiring_review(limit=limit * 2)
    seen: set[int] = set()
    items: list[InspectionListItemOut] = []
    for sev in sev_records:
        if sev.inspection_id in seen:
            continue
        seen.add(sev.inspection_id)
        detail = _build_detail(db, sev.inspection_id)
        if detail is None:
            continue
        items.append(InspectionListItemOut(
            id=detail.id,
            date=detail.date,
            industry=detail.industry,
            product=detail.product,
            station=detail.station,
            pipeline=detail.pipeline,
            status=detail.status,
            quality_score=detail.quality_score,
            severity=detail.severity,
            defect_count=sum(len(ar.defects) for ar in detail.anomaly_results),
            requires_review=detail.requires_review,
        ))
    items.sort(key=lambda i: (sev_order.get(i.severity, 99), i.date))
    return items[:limit]


@router.get("/corrections", response_model=list[CorrectionOut])
def list_corrections(limit: int = 100, db: Session = Depends(get_db)) -> list[CorrectionOut]:
    """List human feedback / false-positive correction records."""
    rows = db.scalars(
        select(CorrectionRecord).order_by(CorrectionRecord.created_at.desc()).limit(limit)
    ).all()
    return [
        CorrectionOut(
            id=r.id,
            inspection_id=f"INS-{r.inspection_id}",
            feedback_category=r.feedback_category,
            original_decision=r.original_decision,
            corrected_decision=r.corrected_decision,
            note=r.note,
            saved_image_path=r.saved_image_path,
            review_status=r.review_status,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/{inspection_id}", response_model=InspectionDetailOut)
def get_inspection(inspection_id: str, db: Session = Depends(get_db)) -> InspectionDetailOut:
    """Get full inspection detail including anomaly results and evidence."""
    numeric_id = int(inspection_id.replace("INS-", ""))
    detail = _build_detail(db, numeric_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return detail


def _run_single_module(
    raw_bytes: Optional[bytes],
    model_key: Optional[str],
    cloned_ckpt_path: Optional[Path],
    threshold: float,
) -> dict[str, Any]:
    """Execute one model adapter (or OpenCV fallback) on raw image bytes."""
    if raw_bytes is None:
        return {
            "anomaly_score": 0.2,
            "confidence_score": 0.89,
            "defects": [],
            "heatmap_path": None,
            "heatmap_url": None,
            "processing_time_ms": None,
            "model_name": "OpenCV Heuristic",
        }

    pred: Optional[dict[str, Any]] = None
    anomaly_score = 0.0
    defects: list[DefectOut] = []

    if model_key in ("yolo11n_seg", "yolo11m_seg"):
        default_yolo = BASE_DIR / "models" / "base" / (
            "yolo11m-seg.pt" if model_key == "yolo11m_seg" else "yolo11n-seg.pt"
        )
        w_path = cloned_ckpt_path or default_yolo
        if YoloSegAdapter.is_available(w_path):
            pred = YoloSegAdapter.predict_bytes(raw_bytes, threshold=threshold, weights_path=w_path)
        else:
            anomaly_score, defects = _analyze_image_bytes(raw_bytes, threshold)
    elif model_key == "omniposead" and cloned_ckpt_path is not None:
        pred = OmniPoseAdapter.predict_bytes(
            raw_bytes, bank_path=cloned_ckpt_path, threshold=threshold
        )
    elif model_key == "anomalydino" and cloned_ckpt_path is not None:
        pred = AnomalyDINOAdapter.predict_bytes(
            raw_bytes, bank_path=cloned_ckpt_path, threshold=threshold
        )
    elif model_key in ("patchcore", "dinomaly") and cloned_ckpt_path is not None:
        pred = AnomalibCheckpointAdapter.predict_bytes(
            raw_bytes, model_key=model_key, ckpt_path=cloned_ckpt_path, threshold=threshold
        )
    elif (
        model_key in ("efficientad_small", "efficientad_medium")
        or (model_key is None and EfficientAdAdapter.is_available())
    ) and EfficientAdAdapter.is_available(cloned_ckpt_path):
        pred = EfficientAdAdapter.predict_bytes(raw_bytes, threshold=threshold, ckpt_path=cloned_ckpt_path)
    else:
        anomaly_score, defects = _analyze_image_bytes(raw_bytes, threshold)

    if pred is not None:
        hp = pred["heatmap_path"]
        return {
            "anomaly_score": float(pred["anomaly_score"]),
            "confidence_score": float(pred["confidence_score"]),
            "defects": [DefectOut(**d) for d in pred["defects"]],
            "heatmap_path": hp,
            "heatmap_url": f"/results/{Path(hp).name}" if hp else None,
            "processing_time_ms": pred["processing_time_ms"],
            "model_name": pred["model_name"],
        }

    return {
        "anomaly_score": float(anomaly_score),
        "confidence_score": 0.89,
        "defects": defects,
        "heatmap_path": None,
        "heatmap_url": None,
        "processing_time_ms": None,
        "model_name": "OpenCV Heuristic",
    }


@router.post("", response_model=InspectionRunOut)
async def run_inspection(
    industry: str = Form("Automotive"),
    product: str = Form("Brake disc"),
    pipelineId: str = Form("p1"),
    scannerUnitId: Optional[int] = Form(None),
    threshold: float = Form(0.5),
    fileName: str = Form("upload.png"),
    moduleWeights: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
) -> InspectionRunOut:
    """Save uploaded image, run all Ready modules in Scanner Unit (or default), and aggregate results."""
    settings = get_settings()
    upload_dir = settings.storage_root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_ext = Path(fileName).suffix or ".png"
    stored_name = f"{uuid.uuid4().hex}{safe_ext}"
    stored_path = upload_dir / stored_name

    raw_bytes: Optional[bytes] = None
    if file is not None:
        raw_bytes = await file.read()
        stored_path.write_bytes(raw_bytes)

    weight_overrides: dict[int, int] = {}
    if moduleWeights:
        try:
            parsed = json.loads(moduleWeights)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    weight_overrides[int(k)] = max(1, min(100, int(v)))
        except (ValueError, TypeError):
            pass

    if scannerUnitId is None:
        raise HTTPException(status_code=422, detail="A Scanner Unit must be selected before running a scan.")

    unit = db.scalar(
        select(ScannerUnit)
        .options(selectinload(ScannerUnit.modules))
        .where(ScannerUnit.id == scannerUnitId)
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Scanner Unit not found")
    industry = unit.industry or industry
    product = unit.product_name or product
    pipelineId = unit.name
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

    exec_out = GpuInferenceScheduler.execute_modules(
        raw_bytes=raw_bytes,
        modules=specs,
        threshold=threshold,
        heuristic_fn=_analyze_image_bytes,
        weight_overrides=weight_overrides,
    )
    agg = aggregate_and_persist_result(
        db,
        scanner_unit_id=scannerUnitId,
        industry=industry,
        product=product,
        pipeline_name=pipelineId,
        stored_image_path=stored_path,
        threshold=threshold,
        execution_out=exec_out,
        station_name="Web UI Station",
    )
    return InspectionRunOut(
        inspectionId=agg["inspectionId"],
        passed=(agg["overall_decision"] == "PASS"),
        quality_score=agg["quality_score"],
        status=agg["status"],
        overall_decision=agg["overall_decision"],
        severity=agg["severity"],
        defects=[DefectOut(**d) for d in agg["defects"]],
        model_used=agg["model_used"],
        heatmap_url=agg["heatmap_url"],
        module_results=[ModuleScanResultOut(**r) for r in agg["module_results"]],
        weighted_outputs=[WeightedOutputOut(**w) for w in agg["weighted_outputs"]],
        distinct_outputs=agg["distinct_outputs"],
        score=agg["score"],
        isMock=False,
    )


@router.post("/{inspection_id}/review")
def review_inspection(
    inspection_id: str,
    body: ReviewIn,
    db: Session = Depends(get_db),
) -> dict:
    """Submit a human review decision (Approved / Rejected) and store correction feedback."""
    if body.decision not in ("Approved", "Rejected"):
        raise HTTPException(status_code=422, detail="decision must be 'Approved' or 'Rejected'")
    if not body.note.strip():
        raise HTTPException(status_code=422, detail="A review note is required")

    numeric_id = int(inspection_id.replace("INS-", ""))
    repo = InspectionRepository(db)
    insp = repo.get_with_results(numeric_id)
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    original_decision = insp.overall_decision
    new_decision = "PASS" if body.decision == "Approved" else "FAIL"
    insp.overall_decision = new_decision
    insp.status = "reviewed"

    for sev in insp.severity_scores:
        sev.requires_human_review = False
        sev.rule_notes = f"[{body.decision} · {body.feedback_category}] {body.note}"

    saved_fp_path: Optional[str] = None
    if body.feedback_category == "False positive" and Path(insp.image_file_path).is_file():
        fp_dir = BASE_DIR / "data" / "false_positives"
        fp_dir.mkdir(parents=True, exist_ok=True)
        src_p = Path(insp.image_file_path)
        dst_p = fp_dir / f"INS-{insp.id}_{src_p.name}"
        shutil.copy2(src_p, dst_p)
        saved_fp_path = str(dst_p.relative_to(BASE_DIR))

    corr = CorrectionRecord(
        inspection_id=insp.id,
        feedback_category=body.feedback_category,
        original_decision=original_decision,
        corrected_decision=new_decision,
        note=body.note.strip(),
        saved_image_path=saved_fp_path,
        review_status="Reviewed",
    )
    db.add(corr)
    db.commit()
    return {
        "status": body.decision,
        "inspectionId": inspection_id,
        "feedback_category": body.feedback_category,
        "saved_false_positive_path": saved_fp_path,
        "note": body.note,
    }


@router.post("/{inspection_id}/confirm")
def confirm_inspection(inspection_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    """Mark an inspection as human-reviewed (legacy compat endpoint)."""
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
