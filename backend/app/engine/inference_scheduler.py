"""Dedicated single-owner GPU inference scheduler with micro-batching and OOM recovery."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from backend.app.core.config import BASE_DIR
from backend.app.engine.config import get_engine_config
from backend.app.engine.model_registry import EngineModelRegistry
from backend.app.models.anomalib_adapter import AnomalibCheckpointAdapter
from backend.app.models.anomalydino_adapter import AnomalyDINOAdapter
from backend.app.models.efficientad_adapter import EfficientAdAdapter
from backend.app.models.omnipose_adapter import OmniPoseAdapter
from backend.app.models.yolo_adapter import YoloSegAdapter

logger = logging.getLogger("clockit.engine.scheduler")


@dataclass
class ModuleSpec:
    """Lightweight module configuration snapshot (safe to pass across threads without ORM session)."""

    module_id: int
    module_name: str
    model_key: str
    weight: int
    selected_outputs: list[str]
    cloned_weights_rel: Optional[str]


class GpuInferenceScheduler:
    """Single-owner GPU execution coordinator with OOM-safe fallback and model reuse."""

    _gpu_lock = threading.Lock()
    _torch_configured = False

    @classmethod
    def _configure_torch_threads(cls) -> None:
        if cls._torch_configured:
            return
        try:
            import torch
            cfg = get_engine_config()
            torch.set_num_threads(max(1, cfg.torch_num_threads))
        except Exception:
            pass
        cls._torch_configured = True

    @classmethod
    def _run_module_adapter(
        cls,
        raw_bytes: Optional[bytes],
        model_key: Optional[str],
        ckpt_path: Optional[Path],
        threshold: float,
        heuristic_fn: Any,
    ) -> tuple[dict[str, Any], float]:
        """Run one module adapter under GPU lock and return (prediction_dict, model_load_ms)."""
        if raw_bytes is None:
            return {
                "anomaly_score": 0.2,
                "confidence_score": 0.89,
                "defects": [],
                "heatmap_path": None,
                "heatmap_url": None,
                "processing_time_ms": None,
                "model_name": "OpenCV Heuristic",
            }, 0.0

        cls._configure_torch_threads()
        resolved_ckpt = ckpt_path or EngineModelRegistry.resolve_weights_path(model_key or "", None)

        entry = None
        if model_key and model_key != "opencv_heuristic":
            entry = EngineModelRegistry.ensure_ready(model_key, resolved_ckpt)

        load_ms = entry.load_time_ms if (entry and entry.use_count == 1) else 0.0

        def _invoke() -> Optional[dict[str, Any]]:
            if model_key in ("yolo11n_seg", "yolo11m_seg"):
                if YoloSegAdapter.is_available(resolved_ckpt):
                    return YoloSegAdapter.predict_bytes(raw_bytes, threshold=threshold, weights_path=resolved_ckpt)
                return None
            if model_key == "omniposead" and resolved_ckpt is not None:
                return OmniPoseAdapter.predict_bytes(raw_bytes, bank_path=resolved_ckpt, threshold=threshold)
            if model_key == "anomalydino" and resolved_ckpt is not None:
                return AnomalyDINOAdapter.predict_bytes(raw_bytes, bank_path=resolved_ckpt, threshold=threshold)
            if model_key in ("patchcore", "dinomaly") and resolved_ckpt is not None:
                return AnomalibCheckpointAdapter.predict_bytes(
                    raw_bytes, model_key=model_key, ckpt_path=resolved_ckpt, threshold=threshold
                )
            if (
                model_key in ("efficientad_small", "efficientad_medium")
                or (model_key is None and EfficientAdAdapter.is_available())
            ) and EfficientAdAdapter.is_available(resolved_ckpt):
                return EfficientAdAdapter.predict_bytes(raw_bytes, threshold=threshold, ckpt_path=resolved_ckpt)
            return None

        with cls._gpu_lock:
            try:
                pred = _invoke()
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower():
                    logger.warning("CUDA OOM on model %s; clearing cache and retrying once.", model_key)
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception:
                        pass
                    pred = _invoke()
                else:
                    raise

        if pred is not None:
            hp = pred.get("heatmap_path")
            return {
                "anomaly_score": float(pred["anomaly_score"]),
                "confidence_score": float(pred["confidence_score"]),
                "defects": list(pred.get("defects", [])),
                "heatmap_path": hp,
                "heatmap_url": f"/results/{Path(hp).name}" if hp else None,
                "processing_time_ms": pred.get("processing_time_ms"),
                "model_name": pred["model_name"],
            }, load_ms

        # Fallback: OpenCV heuristic
        score, defs = heuristic_fn(raw_bytes, threshold)
        return {
            "anomaly_score": float(score),
            "confidence_score": 0.89,
            "defects": [d.model_dump() if hasattr(d, "model_dump") else d for d in defs],
            "heatmap_path": None,
            "heatmap_url": None,
            "processing_time_ms": None,
            "model_name": "OpenCV Heuristic",
        }, load_ms

    @classmethod
    def execute_modules(
        cls,
        raw_bytes: Optional[bytes],
        modules: list[ModuleSpec],
        threshold: float,
        heuristic_fn: Any,
        weight_overrides: Optional[dict[int, int]] = None,
    ) -> dict[str, Any]:
        """Execute all Ready modules for a single image and return raw per-module outputs & timings."""
        t_inf_start = time.perf_counter()
        total_load_ms = 0.0
        per_module: list[dict[str, Any]] = []

        if not modules:
            res, load_ms = cls._run_module_adapter(raw_bytes, None, None, threshold, heuristic_fn)
            total_load_ms += load_ms
            per_module.append({
                "spec": None,
                "weight": 100,
                **res,
            })
        else:
            overrides = weight_overrides or {}
            for spec in modules:
                w = max(1, min(100, int(overrides.get(spec.module_id, spec.weight))))
                ckpt = (
                    (BASE_DIR / spec.cloned_weights_rel)
                    if spec.cloned_weights_rel and (BASE_DIR / spec.cloned_weights_rel).is_file()
                    else None
                )
                res, load_ms = cls._run_module_adapter(
                    raw_bytes, spec.model_key, ckpt, threshold, heuristic_fn
                )
                total_load_ms += load_ms
                per_module.append({
                    "spec": spec,
                    "weight": w,
                    **res,
                })

        inference_ms = round((time.perf_counter() - t_inf_start) * 1000.0, 2)
        return {
            "per_module": per_module,
            "inference_ms": inference_ms,
            "model_load_ms": round(total_load_ms, 2),
        }
