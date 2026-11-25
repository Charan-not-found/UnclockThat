"""YOLO11n-Seg inference adapter using ultralytics."""

from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from backend.app.core.config import BASE_DIR, get_settings


class YoloSegAdapter:
    """Lazy-loading predictor for YOLO11n-Seg weights."""

    _lock = threading.Lock()
    _models: dict[str, Any] = {}

    @classmethod
    def default_weights_path(cls) -> Path:
        settings = get_settings()
        return settings.artifact_root / "pretrained" / "yolo11n-seg.pt"

    @classmethod
    def is_available(cls, weights_path: Optional[Path] = None) -> bool:
        path = weights_path or cls.default_weights_path()
        return path.is_file()

    @classmethod
    def _get_model(cls, weights_path: Optional[Path] = None) -> Any:
        path = weights_path or cls.default_weights_path()
        key = str(path.resolve())
        with cls._lock:
            if key in cls._models:
                return cls._models[key]
            from ultralytics import YOLO
            model = YOLO(str(path))
            cls._models[key] = model
            return model

    @classmethod
    def predict_bytes(
        cls,
        raw_bytes: bytes,
        threshold: float = 0.25,
        weights_path: Optional[Path] = None,
    ) -> dict[str, Any]:
        """Run YOLO11n-Seg inference on raw image bytes and save annotated overlay."""
        import torch

        t0 = time.perf_counter()
        arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("Unable to decode uploaded image bytes")

        h_orig, w_orig = bgr.shape[:2]
        model = cls._get_model(weights_path)
        device = 0 if torch.cuda.is_available() else "cpu"

        results = model.predict(source=bgr, conf=max(0.1, min(0.95, threshold)), device=device, verbose=False)
        res = results[0]

        settings = get_settings()
        results_dir = settings.storage_root / "inspection_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        vis_file = results_dir / f"{uuid.uuid4().hex}_yolo.png"
        annotated = res.plot()
        cv2.imwrite(str(vis_file), annotated)

        # Also save to outputs/visualizations
        out_vis_dir = BASE_DIR / "outputs" / "visualizations"
        out_vis_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_vis_dir / vis_file.name), annotated)

        defects: list[dict[str, Any]] = []
        max_conf = 0.0
        if res.boxes is not None and len(res.boxes) > 0:
            names = res.names or {}
            for box in res.boxes:
                conf = float(box.conf[0].item())
                cls_id = int(box.cls[0].item())
                label = str(names.get(cls_id, f"class_{cls_id}"))
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                max_conf = max(max_conf, conf)
                sev = "Critical" if conf >= 0.85 else "Major" if conf >= 0.65 else "Minor"
                defects.append({
                    "type": f"{label} (YOLO11n-Seg)",
                    "severity": sev,
                    "confidence": round(conf, 3),
                    "anomalyScore": round(conf, 3),
                    "box": {
                        "x": max(0, int(x1 / max(1, w_orig) * 100)),
                        "y": max(0, int(y1 / max(1, h_orig) * 100)),
                        "w": max(4, int((x2 - x1) / max(1, w_orig) * 100)),
                        "h": max(4, int((y2 - y1) / max(1, h_orig) * 100)),
                    },
                })

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "anomaly_score": round(max_conf, 4),
            "confidence_score": round(max_conf if defects else 0.85, 3),
            "defects": defects,
            "heatmap_path": str(vis_file),
            "processing_time_ms": elapsed_ms,
            "model_name": "YOLO11n-Seg",
        }
