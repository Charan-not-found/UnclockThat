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
from backend.app.models.anomalib_adapter import AnomalibCheckpointAdapter
from backend.app.models.anomalydino_adapter import AnomalyDINOAdapter
from backend.app.models.efficientad_adapter import EfficientAdAdapter
from backend.app.models.omnipose_adapter import OmniPoseAdapter
from backend.app.models.yolo_adapter import YoloSegAdapter
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

        anomaly_outs.append(AnomalyResultOut(
            id=str(ar.id),
            model_name=model_name,
            anomaly_score=ar.anomaly_score,
            confidence_score=ar.confidence_score or 0.0,
            is_anomalous=ar.is_anomalous,
            severity=_anomaly_to_severity(ar.anomaly_score),
            defects=defects_out,
            heatmap_path=ar.heatmap_file_path,
            processing_time_ms=ar.processing_time_ms,
        ))

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
        default_yolo = BASE_DIR / "artifacts" / "pretrained" / (
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

    module_results: list[ModuleScanResultOut] = []
    weighted_outputs: list[WeightedOutputOut] = []
    distinct_outputs: dict[str, Any] = {}
    per_module_persist: list[dict[str, Any]] = []

    if ready_mods:
        raw_weights = [
            max(1, min(100, int(weight_overrides.get(m.id, (m.config_json or {}).get("weight", 100)))))
            for m in ready_mods
        ]
        total_weight = sum(raw_weights) or 1

        for mod, w in zip(ready_mods, raw_weights):
            cfg = mod.config_json or {}
            cw = cfg.get("cloned_weights_path")
            ckpt_path = (BASE_DIR / cw) if cw and (BASE_DIR / cw).is_file() else None
            res = _run_single_module(raw_bytes, mod.model_key, ckpt_path, threshold)
            ratio = round(w / total_weight, 4)
            defect_classes = sorted({d.type for d in res["defects"] if d.type})
            selected_outputs = list(mod.selected_outputs_json or [])
            mod_out = ModuleScanResultOut(
                module_id=mod.id,
                module_name=mod.name,
                model_key=mod.model_key,
                model_display_name=res["model_name"],
                weight=w,
                weight_ratio=ratio,
                selected_outputs=selected_outputs,
                anomaly_score=round(res["anomaly_score"], 4),
                confidence_score=round(res["confidence_score"], 4),
                defects=res["defects"],
                defect_classes=defect_classes,
                heatmap_url=res["heatmap_url"],
                processing_time_ms=res["processing_time_ms"],
            )
            module_results.append(mod_out)
            per_module_persist.append({**res, "module": mod})

        if len(module_results) >= 2:
            anomaly_score = round(
                sum(r.anomaly_score * (w / total_weight) for r, w in zip(module_results, raw_weights)),
                4,
            )
            confidence_score = round(
                sum(r.confidence_score * (w / total_weight) for r, w in zip(module_results, raw_weights)),
                4,
            )
            weighted_outputs = [
                WeightedOutputOut(
                    output_key="anomaly_score",
                    label="Anomaly Score (Weighted Avg)",
                    weighted_value=anomaly_score,
                    weights_used=[
                        {
                            "module_id": r.module_id,
                            "module_name": r.module_name,
                            "weight": r.weight,
                            "ratio": r.weight_ratio,
                            "value": r.anomaly_score,
                        }
                        for r in module_results
                    ],
                ),
                WeightedOutputOut(
                    output_key="confidence_score",
                    label="Confidence Score (Weighted Avg)",
                    weighted_value=confidence_score,
                    weights_used=[
                        {
                            "module_id": r.module_id,
                            "module_name": r.module_name,
                            "weight": r.weight,
                            "ratio": r.weight_ratio,
                            "value": r.confidence_score,
                        }
                        for r in module_results
                    ],
                ),
            ]
        else:
            anomaly_score = module_results[0].anomaly_score
            confidence_score = module_results[0].confidence_score

        # Combine defects across all modules (deduplicated/tagged) and collect distinct outputs as-is
        defects = []
        for r in module_results:
            for d in r.defects:
                defects.append(d)

        all_defect_classes = sorted({c for r in module_results for c in r.defect_classes})
        heatmaps = [
            {"module_id": r.module_id, "module_name": r.module_name, "heatmap_url": r.heatmap_url}
            for r in module_results
            if r.heatmap_url
        ]
        # Identify non-shared / distinct outputs from selected_outputs
        output_counts: dict[str, int] = {}
        for r in module_results:
            for out_k in r.selected_outputs:
                output_counts[out_k] = output_counts.get(out_k, 0) + 1
        unique_outputs = []
        for r in module_results:
            for out_k in r.selected_outputs:
                if output_counts.get(out_k, 0) == 1 or out_k in (
                    "defect_class",
                    "segmentation_mask",
                    "bounding_boxes",
                    "heatmap",
                ):
                    if out_k == "defect_class":
                        summary = ", ".join(r.defect_classes) if r.defect_classes else "None detected"
                    elif out_k in ("segmentation_mask", "bounding_boxes"):
                        summary = f"{len(r.defects)} region(s)"
                    elif out_k == "heatmap":
                        summary = "Heatmap generated" if r.heatmap_url else "No heatmap"
                    elif out_k == "anomaly_score":
                        summary = f"{r.anomaly_score:.3f}"
                    elif out_k == "confidence_score":
                        summary = f"{r.confidence_score:.3f}"
                    else:
                        summary = out_k
                    unique_outputs.append(
                        {
                            "module_id": r.module_id,
                            "module_name": r.module_name,
                            "output_key": out_k,
                            "summary": summary,
                            "shared": output_counts.get(out_k, 0) > 1,
                        }
                    )

        distinct_outputs = {
            "defect_classes": all_defect_classes,
            "heatmaps": heatmaps,
            "bounding_boxes_count": len(defects),
            "unique_module_outputs": unique_outputs,
        }
        heatmap_path = next((p["heatmap_path"] for p in per_module_persist if p["heatmap_path"]), None)
        heatmap_url = next((r.heatmap_url for r in module_results if r.heatmap_url), None)
        processing_time_ms = sum((r.processing_time_ms or 0.0) for r in module_results) or None
        used_model_name = (
            f"Multi-Module ({len(module_results)}): " + " + ".join(r.model_display_name for r in module_results)
            if len(module_results) > 1
            else module_results[0].model_display_name
        )
    else:
        single = _run_single_module(raw_bytes, None, None, threshold)
        anomaly_score = single["anomaly_score"]
        confidence_score = single["confidence_score"]
        defects = single["defects"]
        heatmap_path = single["heatmap_path"]
        heatmap_url = single["heatmap_url"]
        processing_time_ms = single["processing_time_ms"]
        used_model_name = single["model_name"]
        per_module_persist.append({**single, "module": None})

    if anomaly_score >= max(0.75, threshold + 0.2):
        decision = "FAIL"
    elif anomaly_score >= threshold or defects:
        decision = "REVIEW_REQUIRED"
    else:
        decision = "PASS"

    quality_score = max(0.05, min(0.99, round(1.0 - anomaly_score * 0.65, 2)))
    mfg_id, pipe_id = _ensure_manufacturer_and_pipeline(db, industry, pipelineId)

    insp = InspectionRepository(db).create(
        manufacturer_id=mfg_id,
        pipeline_config_id=pipe_id,
        scanner_unit_id=scannerUnitId,
        product_serial=product,
        station_name="Web UI Station",
        image_file_path=str(stored_path),
        status="completed",
        overall_decision=decision,
        quality_score=quality_score,
        inspected_at=datetime.now(timezone.utc),
    )

    active_models = ModelConfigRepository(db).list_active_by_manufacturer(mfg_id)
    primary_ar = None
    for item in per_module_persist:
        model_cfg_id = None
        m_name = item["model_name"]
        if m_name:
            matched = next((m for m in active_models if m.name == m_name), None)
            if matched:
                model_cfg_id = matched.id
        if model_cfg_id is None and active_models:
            model_cfg_id = active_models[0].id

        ar_row = AnomalyResultRepository(db).create(
            inspection_id=insp.id,
            model_config_id=model_cfg_id,
            anomaly_score=item["anomaly_score"],
            confidence_score=item["confidence_score"],
            is_anomalous=bool(item["defects"] or item["anomaly_score"] >= threshold),
            heatmap_file_path=item["heatmap_path"],
            processing_time_ms=item["processing_time_ms"],
            bounding_boxes_json=[d.model_dump() for d in item["defects"]],
        )
        if primary_ar is None:
            primary_ar = ar_row

    ar = primary_ar

    top_severity = defects[0].severity if defects else (
        "Minor" if decision == "REVIEW_REQUIRED" else "Informational"
    )
    SeverityScoreRepository(db).create(
        inspection_id=insp.id,
        anomaly_result_id=ar.id,
        severity_level=top_severity,
        numeric_score=anomaly_score,
        requires_human_review=(decision == "REVIEW_REQUIRED"),
    )
    db.commit()

    # Save standardized JSON inspection report to outputs/reports/
    reports_dir = BASE_DIR / "outputs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_payload = {
        "inspection_id": f"INS-{insp.id}",
        "scanner_unit_id": scannerUnitId,
        "industry": industry,
        "product": product,
        "model_used": used_model_name,
        "overall_decision": decision,
        "quality_score": int(round(quality_score * 100)),
        "anomaly_score": anomaly_score,
        "severity": top_severity,
        "defects": [d.model_dump() for d in defects],
        "module_results": [r.model_dump() for r in module_results],
        "weighted_outputs": [w.model_dump() for w in weighted_outputs],
        "distinct_outputs": distinct_outputs,
        "timestamp": insp.inspected_at.isoformat(),
    }
    (reports_dir / f"INS-{insp.id}.json").write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    status_label = _decision_to_status(decision)
    return InspectionRunOut(
        inspectionId=f"INS-{insp.id}",
        quality_score=int(round(quality_score * 100)),
        status=status_label,
        overall_decision=decision,
        severity=top_severity,
        defects=defects,
        model_used=used_model_name,
        heatmap_url=heatmap_url,
        module_results=module_results,
        weighted_outputs=weighted_outputs,
        distinct_outputs=distinct_outputs,
        score=int(round(quality_score * 100)),
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
