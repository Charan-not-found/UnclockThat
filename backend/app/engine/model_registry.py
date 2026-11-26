"""Central Model Registry & Loader with lifecycle states, key-based reuse, and OOM-safe device management."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from backend.app.core.config import BASE_DIR
from backend.app.models.anomalib_adapter import AnomalibCheckpointAdapter
from backend.app.models.anomalydino_adapter import AnomalyDINOAdapter
from backend.app.models.efficientad_adapter import EfficientAdAdapter
from backend.app.models.omnipose_adapter import OmniPoseAdapter
from backend.app.models.yolo_adapter import YoloSegAdapter

logger = logging.getLogger("clockit.engine.model_registry")


class ModelState(str, Enum):
    UNLOADED = "UNLOADED"
    LOADING = "LOADING"
    READY = "READY"
    ERROR = "ERROR"
    UNLOADING = "UNLOADING"


@dataclass
class LoadedModelEntry:
    instance_key: str
    model_key: str
    weights_path: Optional[str]
    device: str
    state: ModelState = ModelState.UNLOADED
    load_time_ms: float = 0.0
    loaded_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    use_count: int = 0
    error_message: Optional[str] = None


class EngineModelRegistry:
    """Thread-safe registry tracking loaded model instances, lifecycle states, and load timings."""

    _lock = threading.Lock()
    _entries: dict[str, LoadedModelEntry] = {}

    @staticmethod
    def build_instance_key(model_key: str, weights_path: Optional[Path], device: str = "auto") -> str:
        resolved_w = str(weights_path.resolve()) if weights_path is not None else "default"
        return f"{model_key}::{resolved_w}::{device}"

    @staticmethod
    def resolve_weights_path(model_key: str, cloned_rel_path: Optional[str]) -> Optional[Path]:
        if cloned_rel_path:
            p = BASE_DIR / cloned_rel_path
            if p.is_file():
                return p
        if model_key in ("yolo11n_seg", "yolo11m_seg"):
            fname = "yolo11m-seg.pt" if model_key == "yolo11m_seg" else "yolo11n-seg.pt"
            p = BASE_DIR / "models" / "base" / fname
            if p.is_file():
                return p
        return None

    @classmethod
    def ensure_ready(
        cls,
        model_key: str,
        weights_path: Optional[Path] = None,
        device: str = "auto",
    ) -> LoadedModelEntry:
        """Ensure the requested model adapter is ready and track its load time and reuse count."""
        key = cls.build_instance_key(model_key, weights_path, device)
        with cls._lock:
            existing = cls._entries.get(key)
            if existing is not None and existing.state == ModelState.READY:
                existing.last_used_at = time.time()
                existing.use_count += 1
                return existing

            entry = LoadedModelEntry(
                instance_key=key,
                model_key=model_key,
                weights_path=str(weights_path) if weights_path else None,
                device=device,
                state=ModelState.LOADING,
            )
            cls._entries[key] = entry

        t0 = time.perf_counter()
        try:
            # Trigger adapter-level lazy initialization only when needed
            if model_key in ("yolo11n_seg", "yolo11m_seg"):
                if weights_path is not None and not YoloSegAdapter.is_available(weights_path):
                    raise FileNotFoundError(f"Missing YOLO weights: {weights_path}")
                if YoloSegAdapter.is_available(weights_path):
                    YoloSegAdapter._get_model(weights_path)
            elif model_key in ("patchcore", "dinomaly") and weights_path is not None:
                AnomalibCheckpointAdapter._get_model(model_key, weights_path)
            elif model_key in ("efficientad_small", "efficientad_medium") and EfficientAdAdapter.is_available(weights_path):
                EfficientAdAdapter._get_model(weights_path)
            elif model_key == "omniposead" and weights_path is not None:
                if not weights_path.is_file():
                    raise FileNotFoundError(f"Missing OmniPoseAD bank: {weights_path}")
                OmniPoseAdapter._get_backbone()
            elif model_key == "anomalydino" and weights_path is not None:
                if not weights_path.is_file():
                    raise FileNotFoundError(f"Missing AnomalyDINO bank: {weights_path}")
                AnomalyDINOAdapter._get_backbone()

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            with cls._lock:
                entry.state = ModelState.READY
                entry.load_time_ms = elapsed_ms
                entry.last_used_at = time.time()
                entry.use_count += 1
            logger.info("Model ready: %s (load_ms=%.2f)", key, elapsed_ms)
            return entry
        except Exception as exc:
            with cls._lock:
                entry.state = ModelState.ERROR
                entry.error_message = str(exc)
            logger.error("Model load failed for %s: %s", key, exc)
            raise

    @classmethod
    def unload(cls, instance_key: str) -> bool:
        """Mark a model entry unloaded and clear adapter cache if applicable."""
        with cls._lock:
            entry = cls._entries.get(instance_key)
            if entry is None:
                return False
            entry.state = ModelState.UNLOADING
            cls._entries.pop(instance_key, None)
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        logger.info("Unloaded model entry: %s", instance_key)
        return True

    @classmethod
    def list_entries(cls) -> list[dict[str, Any]]:
        """Return safe status metadata for all tracked model entries (no raw absolute paths)."""
        with cls._lock:
            return [
                {
                    "instance_key": e.instance_key.split("::")[0],
                    "model_key": e.model_key,
                    "device": e.device,
                    "state": e.state.value,
                    "load_time_ms": e.load_time_ms,
                    "use_count": e.use_count,
                    "error_message": e.error_message,
                }
                for e in cls._entries.values()
            ]
