"""Configurable concurrency, batching, and resource-limit settings for the inspection engine."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class EngineConfig:
    """Initial hardware-tuned concurrency & safety limits (16 GB RAM, RTX 3050, 4-core CPU)."""

    gpu_workers: int = int(os.getenv("CLOCKIT_GPU_WORKERS", "1"))
    cpu_prep_workers: int = int(os.getenv("CLOCKIT_CPU_PREP_WORKERS", "2"))
    prep_thread_pool_size: int = int(os.getenv("CLOCKIT_PREP_THREADS", "4"))
    micro_batch_size: int = int(os.getenv("CLOCKIT_MICRO_BATCH_SIZE", "4"))
    max_batch_wait_ms: int = int(os.getenv("CLOCKIT_MAX_BATCH_WAIT_MS", "50"))
    max_queue_size: int = int(os.getenv("CLOCKIT_MAX_QUEUE_SIZE", "2000"))
    max_retries: int = int(os.getenv("CLOCKIT_MAX_RETRIES", "2"))
    max_upload_mb: int = int(os.getenv("CLOCKIT_MAX_UPLOAD_MB", "50"))
    max_zip_mb: int = int(os.getenv("CLOCKIT_MAX_ZIP_MB", "500"))
    max_zip_entries: int = int(os.getenv("CLOCKIT_MAX_ZIP_ENTRIES", "10000"))
    max_image_pixels: int = int(os.getenv("CLOCKIT_MAX_IMAGE_PIXELS", "40000000"))
    min_free_disk_mb: int = int(os.getenv("CLOCKIT_MIN_FREE_DISK_MB", "256"))
    api_rate_limit_per_min: int = int(os.getenv("CLOCKIT_API_RATE_LIMIT", "600"))
    torch_num_threads: int = int(os.getenv("CLOCKIT_TORCH_THREADS", "2"))


@lru_cache
def get_engine_config() -> EngineConfig:
    """Return cached EngineConfig."""
    return EngineConfig()
