"""Stage 6 benchmark script: measures 100-image throughput, P50/P95 latency, and peak RAM."""

from __future__ import annotations

import io
import sys
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np
from starlette.datastructures import UploadFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.api.v1.engine_api import _create_batch_and_jobs, engine_metrics, get_batch_status  # noqa: E402
from backend.app.api.v1.scanner_units import ModuleIn, ScannerUnitIn, add_module, create_scanner_unit, delete_scanner_unit  # noqa: E402
from backend.app.database.connection import SessionLocal, init_db  # noqa: E402
from backend.app.database.models.scanner import ModelToggleSetting  # noqa: E402
from backend.app.engine.worker import InspectionEngineWorker  # noqa: E402


def run_benchmark(num_images: int = 100) -> None:
    init_db()
    db = SessionLocal()
    prev_toggle = db.get(ModelToggleSetting, "opencv_heuristic")
    prev_enabled = prev_toggle.is_enabled if prev_toggle else True
    if prev_toggle:
        prev_toggle.is_enabled = True
        db.commit()

    unit_id = None
    try:
        unit = create_scanner_unit(
            ScannerUnitIn(name="Benchmark Unit", industry="Automotive", product_name="BenchPart"),
            db=db,
        )
        unit_id = unit.id
        add_module(
            unit_id,
            ModuleIn(name="Heuristic Bench", model_key="opencv_heuristic", selected_outputs=["anomaly_score"]),
            db=db,
        )

        img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        _, png_bytes = cv2.imencode(".png", img)
        raw = png_bytes.tobytes()

        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w") as zf:
            for i in range(num_images):
                zf.writestr(f"sample_{i:04d}.png", raw)
        zbuf.seek(0)

        t0 = time.perf_counter()
        sub = _create_batch_and_jobs(
            db,
            scanner_unit_id=unit_id,
            source_type="MASS_TEST",
            files=[UploadFile(filename="bench_100.zip", file=zbuf)],
            threshold=0.5,
            priority=5,
            idempotency_key=None,
            metadata_str=None,
        )
        while InspectionEngineWorker.process_next_job():
            pass
        elapsed = time.perf_counter() - t0
        st = get_batch_status(sub.batch_id, db=db)
        mt = engine_metrics()
        print(
            f"BENCHMARK {num_images} images: completed={st['completed_items']}, failed={st['failed_items']}, "
            f"elapsed={elapsed:.2f}s, throughput={num_images / elapsed * 60:.1f} img/min, "
            f"p50={mt['p50_latency_ms']}ms, p95={mt['p95_latency_ms']}ms, ram_mb={mt['ram_mb']}"
        )
    finally:
        if unit_id is not None:
            delete_scanner_unit(unit_id, db=db)
        if prev_toggle:
            prev_toggle.is_enabled = prev_enabled
            db.commit()
        db.close()


if __name__ == "__main__":
    run_benchmark(100)
