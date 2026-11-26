"""Bounded CPU preprocessing & image content validation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from backend.app.engine.config import get_engine_config


@dataclass
class PreparedImage:
    """Validated and decoded image payload ready for inference scheduling."""

    raw_bytes: bytes
    width: int
    height: int
    channels: int
    preprocess_ms: float


_prep_executor: Optional[ThreadPoolExecutor] = None


def get_prep_executor() -> ThreadPoolExecutor:
    """Return bounded CPU preprocessing ThreadPoolExecutor."""
    global _prep_executor
    if _prep_executor is None:
        cfg = get_engine_config()
        _prep_executor = ThreadPoolExecutor(
            max_workers=max(1, cfg.prep_thread_pool_size),
            thread_name_prefix="clockit-prep",
        )
    return _prep_executor


def validate_and_prepare_image(image_path: Path) -> PreparedImage:
    """Read image bytes from managed storage, validate content & dimensions, and return metadata."""
    import time

    t0 = time.perf_counter()
    cfg = get_engine_config()

    if not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path.name}")

    size_bytes = image_path.stat().st_size
    if size_bytes == 0:
        raise ValueError("Empty image file (0 bytes)")
    if size_bytes > cfg.max_upload_mb * 1024 * 1024:
        raise ValueError(f"Image exceeds max upload size ({cfg.max_upload_mb} MB)")

    raw_bytes = image_path.read_bytes()
    arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Corrupt or unsupported image format")

    h, w = bgr.shape[:2]
    c = bgr.shape[2] if bgr.ndim == 3 else 1
    if w <= 0 or h <= 0:
        raise ValueError("Invalid image dimensions")
    if w * h > cfg.max_image_pixels:
        raise ValueError(f"Image pixel count ({w * h}) exceeds limit ({cfg.max_image_pixels})")

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return PreparedImage(
        raw_bytes=raw_bytes,
        width=w,
        height=h,
        channels=c,
        preprocess_ms=elapsed_ms,
    )
