"""Shared result aggregation and idempotent persistence for single, Mass Test, and API inspections."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.app.core.config import BASE_DIR
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


def _ensure_manufacturer_and_pipeline(db: Session, industry: str, pipeline_name: str) -> tuple[int, int]:
    mfg_repo = ManufacturerRepository(db)
    mfg = mfg_repo.get_by_name(industry) or mfg_repo.get_by_name("Default Manufacturer")
    if mfg is None:
        mfg = mfg_repo.create(name=industry or "Default Manufacturer", industry=industry or "General")

    pipe_repo = PipelineConfigRepository(db)
    pipes = pipe_repo.list_active_by_manufacturer(mfg.id)
    matched = next((p for p in pipes if p.name == pipeline_name), None)
    if matched is None:
        matched = pipe_repo.create(
            manufacturer_id=mfg.id,
            name=pipeline_name,
            modules_json=[{"id": "anomaly_detection", "type": "opencv_heuristic"}],
        )
    return mfg.id, matched.id


def _decision_to_status(decision: str) -> str:
    return {"PASS": "Completed", "FAIL": "Failed", "REVIEW_REQUIRED": "Needs review"}.get(
        decision, "Completed"
    )


def aggregate_and_persist_result(
    db: Session,
    *,
    scanner_unit_id: Optional[int],
    industry: str,
    product: str,
    pipeline_name: str,
    stored_image_path: Path,
    threshold: float,
    execution_out: dict[str, Any],
    station_name: str = "Web UI Station",
    existing_inspection_id: Optional[int] = None,
) -> dict[str, Any]:
    """Aggregate multi-module outputs (weighted avg + distinct) and persist to inspection tables."""
    t_agg_start = time.perf_counter()
    per_module = execution_out["per_module"]
    has_modules = per_module and per_module[0]["spec"] is not None

    module_results: list[dict[str, Any]] = []
    weighted_outputs: list[dict[str, Any]] = []
    distinct_outputs: dict[str, Any] = {}

    if has_modules:
        raw_weights = [item["weight"] for item in per_module]
        total_weight = sum(raw_weights) or 1

        for item in per_module:
            spec = item["spec"]
            w = item["weight"]
            ratio = round(w / total_weight, 4)
            defects_list = item["defects"]
            defect_classes = sorted({d["type"] for d in defects_list if d.get("type")})
            module_results.append({
                "module_id": spec.module_id,
                "module_name": spec.module_name,
                "model_key": spec.model_key,
                "model_display_name": item["model_name"],
                "weight": w,
                "weight_ratio": ratio,
                "selected_outputs": list(spec.selected_outputs),
                "anomaly_score": round(item["anomaly_score"], 4),
                "confidence_score": round(item["confidence_score"], 4),
                "defects": defects_list,
                "defect_classes": defect_classes,
                "heatmap_url": item["heatmap_url"],
                "processing_time_ms": item["processing_time_ms"],
            })

        if len(module_results) >= 2:
            anomaly_score = round(
                sum(r["anomaly_score"] * (w / total_weight) for r, w in zip(module_results, raw_weights)),
                4,
            )
            confidence_score = round(
                sum(r["confidence_score"] * (w / total_weight) for r, w in zip(module_results, raw_weights)),
                4,
            )
            weighted_outputs = [
                {
                    "output_key": "anomaly_score",
                    "label": "Anomaly Score (Weighted Avg)",
                    "weighted_value": anomaly_score,
                    "weights_used": [
                        {
                            "module_id": r["module_id"],
                            "module_name": r["module_name"],
                            "weight": r["weight"],
                            "ratio": r["weight_ratio"],
                            "value": r["anomaly_score"],
                        }
                        for r in module_results
                    ],
                },
                {
                    "output_key": "confidence_score",
                    "label": "Confidence Score (Weighted Avg)",
                    "weighted_value": confidence_score,
                    "weights_used": [
                        {
                            "module_id": r["module_id"],
                            "module_name": r["module_name"],
                            "weight": r["weight"],
                            "ratio": r["weight_ratio"],
                            "value": r["confidence_score"],
                        }
                        for r in module_results
                    ],
                },
            ]
        else:
            anomaly_score = module_results[0]["anomaly_score"]
            confidence_score = module_results[0]["confidence_score"]

        defects = [d for r in module_results for d in r["defects"]]
        all_defect_classes = sorted({c for r in module_results for c in r["defect_classes"]})
        heatmaps = [
            {"module_id": r["module_id"], "module_name": r["module_name"], "heatmap_url": r["heatmap_url"]}
            for r in module_results
            if r["heatmap_url"]
        ]

        output_counts: dict[str, int] = {}
        for r in module_results:
            for out_k in r["selected_outputs"]:
                output_counts[out_k] = output_counts.get(out_k, 0) + 1

        unique_outputs = []
        for r in module_results:
            for out_k in r["selected_outputs"]:
                if output_counts.get(out_k, 0) == 1 or out_k in (
                    "defect_class",
                    "segmentation_mask",
                    "bounding_boxes",
                    "heatmap",
                ):
                    if out_k == "defect_class":
                        summary = ", ".join(r["defect_classes"]) if r["defect_classes"] else "None detected"
                    elif out_k in ("segmentation_mask", "bounding_boxes"):
                        summary = f"{len(r['defects'])} region(s)"
                    elif out_k == "heatmap":
                        summary = "Heatmap generated" if r["heatmap_url"] else "No heatmap"
                    elif out_k == "anomaly_score":
                        summary = f"{r['anomaly_score']:.3f}"
                    elif out_k == "confidence_score":
                        summary = f"{r['confidence_score']:.3f}"
                    else:
                        summary = out_k
                    unique_outputs.append({
                        "module_id": r["module_id"],
                        "module_name": r["module_name"],
                        "output_key": out_k,
                        "summary": summary,
                        "shared": output_counts.get(out_k, 0) > 1,
                    })

        distinct_outputs = {
            "defect_classes": all_defect_classes,
            "heatmaps": heatmaps,
            "bounding_boxes_count": len(defects),
            "unique_module_outputs": unique_outputs,
        }
        heatmap_url = next((r["heatmap_url"] for r in module_results if r["heatmap_url"]), None)
        used_model_name = (
            f"Multi-Module ({len(module_results)}): " + " + ".join(r["model_display_name"] for r in module_results)
            if len(module_results) > 1
            else module_results[0]["model_display_name"]
        )
    else:
        single = per_module[0]
        anomaly_score = single["anomaly_score"]
        confidence_score = single["confidence_score"]
        defects = single["defects"]
        heatmap_url = single["heatmap_url"]
        used_model_name = single["model_name"]

    if anomaly_score >= max(0.75, threshold + 0.2):
        decision = "FAIL"
    elif anomaly_score >= threshold or defects:
        decision = "REVIEW_REQUIRED"
    else:
        decision = "PASS"

    quality_score = max(0.05, min(0.99, round(1.0 - anomaly_score * 0.65, 2)))
    top_severity = (
        defects[0]["severity"]
        if defects
        else ("Minor" if decision == "REVIEW_REQUIRED" else "Informational")
    )
    analysis_ms = round((time.perf_counter() - t_agg_start) * 1000.0, 2)

    t_persist_start = time.perf_counter()
    # Idempotency guard for restart recovery
    insp = InspectionRepository(db).get_by_id(existing_inspection_id) if existing_inspection_id else None
    if insp is None:
        mfg_id, pipe_id = _ensure_manufacturer_and_pipeline(db, industry, pipeline_name)
        insp = InspectionRepository(db).create(
            manufacturer_id=mfg_id,
            pipeline_config_id=pipe_id,
            scanner_unit_id=scanner_unit_id,
            product_serial=product,
            station_name=station_name,
            image_file_path=str(stored_image_path),
            status="completed",
            overall_decision=decision,
            quality_score=quality_score,
            inspected_at=datetime.now(timezone.utc),
        )
        active_models = ModelConfigRepository(db).list_active_by_manufacturer(mfg_id)
        primary_ar = None
        for item in per_module:
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
                bounding_boxes_json=item["defects"],
            )
            if primary_ar is None:
                primary_ar = ar_row

        SeverityScoreRepository(db).create(
            inspection_id=insp.id,
            anomaly_result_id=primary_ar.id if primary_ar else None,
            severity_level=top_severity,
            numeric_score=anomaly_score,
            requires_human_review=(decision == "REVIEW_REQUIRED"),
        )
        db.commit()

        reports_dir = BASE_DIR / "outputs" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_payload = {
            "inspection_id": f"INS-{insp.id}",
            "scanner_unit_id": scanner_unit_id,
            "industry": industry,
            "product": product,
            "model_used": used_model_name,
            "overall_decision": decision,
            "quality_score": int(round(quality_score * 100)),
            "anomaly_score": anomaly_score,
            "severity": top_severity,
            "defects": defects,
            "module_results": module_results,
            "weighted_outputs": weighted_outputs,
            "distinct_outputs": distinct_outputs,
            "timestamp": insp.inspected_at.isoformat(),
        }
        (reports_dir / f"INS-{insp.id}.json").write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    persistence_ms = round((time.perf_counter() - t_persist_start) * 1000.0, 2)
    return {
        "inspection_db_id": insp.id,
        "inspectionId": f"INS-{insp.id}",
        "quality_score": int(round(quality_score * 100)),
        "status": _decision_to_status(decision),
        "overall_decision": decision,
        "severity": top_severity,
        "defects": defects,
        "model_used": used_model_name,
        "heatmap_url": heatmap_url,
        "module_results": module_results,
        "weighted_outputs": weighted_outputs,
        "distinct_outputs": distinct_outputs,
        "score": int(round(quality_score * 100)),
        "isMock": False,
        "analysis_ms": analysis_ms,
        "persistence_ms": persistence_ms,
    }
