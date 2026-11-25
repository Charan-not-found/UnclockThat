"""Lazy-loading EfficientAD inference adapter backed by an anomalib checkpoint."""

from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from backend.app.core.config import get_settings


class EfficientAdAdapter:
    """Singleton-style lazy loader and predictor for trained EfficientAD checkpoints."""

    _lock = threading.Lock()
    _model: Any = None
    _loaded_ckpt: Optional[Path] = None

    @classmethod
    def default_checkpoint_path(cls) -> Path:
        settings = get_settings()
        return settings.artifact_root / "trained" / "efficientad_casting.ckpt"

    @classmethod
    def is_available(cls, ckpt_path: Optional[Path] = None) -> bool:
        path = ckpt_path or cls.default_checkpoint_path()
        return path.is_file()

    @classmethod
    def _get_model(cls, ckpt_path: Optional[Path] = None) -> Any:
        path = ckpt_path or cls.default_checkpoint_path()
        with cls._lock:
            if cls._model is not None and cls._loaded_ckpt == path:
                return cls._model

            settings = get_settings()
            tmp_mpl = settings.storage_root / "temporary" / "mpl"
            tmp_mpl.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("MPLCONFIGDIR", str(tmp_mpl))
            os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

            import torch
            from anomalib.models.image.efficient_ad.lightning_model import EfficientAd

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            aux_dir = settings.storage_root / "temporary" / "aux_imagenette"
            kwargs: dict[str, Any] = {"map_location": device}
            if aux_dir.is_dir():
                kwargs["imagenet_dir"] = str(aux_dir)

            model = EfficientAd.load_from_checkpoint(str(path), **kwargs)
            model.to(device)
            model.eval()
            cls._model = model
            cls._loaded_ckpt = path
            return cls._model

    @classmethod
    def predict_bytes(
        cls,
        raw_bytes: bytes,
        threshold: float = 0.5,
        ckpt_path: Optional[Path] = None,
    ) -> dict[str, Any]:
        """Run EfficientAD inference on raw image bytes and save a heatmap overlay."""
        import torch

        t0 = time.perf_counter()
        arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("Unable to decode uploaded image bytes")

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h_orig, w_orig = rgb.shape[:2]

        # Prepare float tensor in [0, 1], shape (1, 3, H, W)
        resized = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_AREA)
        tensor = torch.from_numpy(resized).permute(2, 0, 1).float().unsqueeze(0) / 255.0

        model = cls._get_model(ckpt_path)
        device = next(model.parameters()).device
        tensor = tensor.to(device)
        with torch.no_grad():
            if getattr(model, "pre_processor", None) is not None and callable(model.pre_processor):
                tensor_in = model.pre_processor(tensor)
            else:
                tensor_in = tensor
            out = model.model(tensor_in)
            if getattr(model, "post_processor", None) is not None and callable(model.post_processor):
                try:
                    out = model.post_processor(out)
                except Exception:
                    pass

        pred_score_t = getattr(out, "pred_score", None)
        if pred_score_t is None:
            anomaly_map_t = out.anomaly_map
            raw_score = float(anomaly_map_t.max().item())
        else:
            raw_score = float(pred_score_t.reshape(-1)[0].item())

        # Clamp to [0.0, 1.0] if post-processor normalized it, else squash via sigmoid-like scale
        if 0.0 <= raw_score <= 1.0:
            anomaly_score = round(raw_score, 4)
        else:
            anomaly_score = round(float(1.0 / (1.0 + np.exp(-raw_score))), 4)

        amap = out.anomaly_map.squeeze().detach().cpu().numpy()
        amap_min, amap_max = float(amap.min()), float(amap.max())
        if amap_max > amap_min:
            amap_norm = (amap - amap_min) / (amap_max - amap_min)
        else:
            amap_norm = np.zeros_like(amap, dtype=np.float32)

        amap_full = cv2.resize(amap_norm.astype(np.float32), (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)

        # Save heatmap overlay to storage/inspection_results/
        settings = get_settings()
        results_dir = settings.storage_root / "inspection_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        heatmap_file = results_dir / f"{uuid.uuid4().hex}_heatmap.png"

        heat_uint8 = np.uint8(np.clip(amap_full * 255.0, 0, 255))
        heat_color = cv2.applyColorMap(heat_uint8, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(bgr, 0.6, heat_color, 0.4, 0)
        cv2.imwrite(str(heatmap_file), overlay)

        # Extract defect boxes where normalized map exceeds threshold (only if anomalous)
        defects: list[dict[str, Any]] = []
        if anomaly_score >= threshold:
            mask = np.uint8(amap_full >= max(0.55, threshold)) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            total_area = max(1, h_orig * w_orig)
            for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
                area = cv2.contourArea(cnt)
                if area / total_area < 0.002:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                region_peak = float(amap_full[y : y + h, x : x + w].max()) if w > 0 and h > 0 else anomaly_score
                defects.append({
                    "type": "Surface Anomaly (EfficientAD)",
                    "severity": (
                        "Critical" if anomaly_score >= 0.85
                        else "Major" if anomaly_score >= 0.65
                        else "Minor"
                    ),
                    "confidence": round(min(0.99, 0.55 + anomaly_score * 0.44), 3),
                    "anomalyScore": round(max(anomaly_score, region_peak), 3),
                    "box": {
                        "x": int(x / w_orig * 100),
                        "y": int(y / h_orig * 100),
                        "w": max(4, int(w / w_orig * 100)),
                        "h": max(4, int(h / h_orig * 100)),
                    },
                })

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "anomaly_score": anomaly_score,
            "confidence_score": round(min(0.99, 0.6 + abs(anomaly_score - 0.5) * 0.7), 3),
            "defects": defects,
            "heatmap_path": str(heatmap_file),
            "processing_time_ms": elapsed_ms,
            "model_name": "EfficientAD-Small (Prototype)",
        }
