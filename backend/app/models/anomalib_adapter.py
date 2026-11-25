"""Unified inference adapter for trained Anomalib checkpoints (PatchCore, Dinomaly, EfficientAD)."""

from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from backend.app.core.config import BASE_DIR, get_settings


class AnomalibCheckpointAdapter:
    """Thread-safe lazy loader and predictor for trained Anomalib Lightning checkpoints."""

    _lock = threading.Lock()
    _models: dict[str, Any] = {}

    @classmethod
    def _get_model(cls, model_key: str, ckpt_path: Path) -> Any:
        cache_key = f"{model_key}:{ckpt_path.resolve()}"
        with cls._lock:
            if cache_key in cls._models:
                return cls._models[cache_key]

            settings = get_settings()
            tmp_mpl = settings.storage_root / "temporary" / "mpl"
            tmp_mpl.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("MPLCONFIGDIR", str(tmp_mpl))
            os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

            import torch
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            if model_key == "patchcore":
                from anomalib.models import Patchcore
                model = Patchcore.load_from_checkpoint(str(ckpt_path), map_location=device)
            elif model_key == "dinomaly":
                from anomalib.models import Dinomaly
                model = Dinomaly.load_from_checkpoint(str(ckpt_path), map_location=device)
            else:
                from anomalib.models.image.efficient_ad.lightning_model import EfficientAd
                aux_dir = settings.storage_root / "temporary" / "aux_imagenette"
                kwargs: dict[str, Any] = {"map_location": device}
                if aux_dir.is_dir():
                    kwargs["imagenet_dir"] = str(aux_dir)
                model = EfficientAd.load_from_checkpoint(str(ckpt_path), **kwargs)

            model.to(device)
            model.eval()
            cls._models[cache_key] = model
            return model

    @classmethod
    def predict_bytes(
        cls,
        raw_bytes: bytes,
        model_key: str,
        ckpt_path: Path,
        threshold: float = 0.5,
    ) -> dict[str, Any]:
        """Run inference with a trained Anomalib checkpoint and save a heatmap overlay."""
        import torch

        t0 = time.perf_counter()
        arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("Unable to decode uploaded image bytes")

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h_orig, w_orig = rgb.shape[:2]

        target_hw = (392, 392) if model_key == "dinomaly" else (256, 256)
        resized = cv2.resize(rgb, target_hw, interpolation=cv2.INTER_AREA)
        tensor = torch.from_numpy(resized).permute(2, 0, 1).float().unsqueeze(0) / 255.0

        model = cls._get_model(model_key, ckpt_path)
        device = next(model.parameters()).device
        tensor = tensor.to(device)

        with torch.no_grad():
            tensor_in = (
                model.pre_processor(tensor)
                if getattr(model, "pre_processor", None) is not None and callable(model.pre_processor)
                else tensor
            )
            out = model.model(tensor_in)
            if getattr(model, "post_processor", None) is not None and callable(model.post_processor):
                try:
                    out = model.post_processor(out)
                except Exception:
                    pass

        pred_score_t = getattr(out, "pred_score", None)
        if pred_score_t is None:
            raw_score = float(out.anomaly_map.max().item())
        else:
            raw_score = float(pred_score_t.reshape(-1)[0].item())

        anomaly_score = round(raw_score, 4) if 0.0 <= raw_score <= 1.0 else round(float(1.0 / (1.0 + np.exp(-raw_score))), 4)

        amap = out.anomaly_map.squeeze().detach().cpu().numpy()
        amap_min, amap_max = float(amap.min()), float(amap.max())
        amap_norm = (amap - amap_min) / (amap_max - amap_min) if amap_max > amap_min else np.zeros_like(amap, dtype=np.float32)
        amap_full = cv2.resize(amap_norm.astype(np.float32), (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)

        settings = get_settings()
        results_dir = settings.storage_root / "inspection_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        heatmap_file = results_dir / f"{uuid.uuid4().hex}_{model_key}_heatmap.png"

        heat_uint8 = np.uint8(np.clip(amap_full * 255.0, 0, 255))
        heat_color = cv2.applyColorMap(heat_uint8, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(bgr, 0.6, heat_color, 0.4, 0)
        cv2.imwrite(str(heatmap_file), overlay)

        out_vis_dir = BASE_DIR / "outputs" / "visualizations"
        out_vis_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_vis_dir / heatmap_file.name), overlay)

        display_names = {
            "patchcore": "PatchCore (WideResNet-50)",
            "dinomaly": "Dinomaly (DINOv2 ViT)",
            "efficientad_medium": "EfficientAD-Medium",
            "efficientad_small": "EfficientAD-Small",
        }
        model_label = display_names.get(model_key, model_key)

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
                    "type": f"Surface Anomaly ({model_label})",
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
            "model_name": model_label,
        }
