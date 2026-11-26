"""PROMETHEUS-X Line Simulator (CLI).

Streams images from simulator/sample_data/ (or a custom folder) one by one
to the PROMETHEUS-X backend and receives True (PASS) / False (FAIL or REVIEW_REQUIRED)
for every inspection check.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import requests

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parent / "sample_data"


def list_scanner_units(base_url: str) -> list[dict[str, Any]]:
    resp = requests.get(f"{base_url.rstrip('/')}/scanner-units", timeout=10)
    resp.raise_for_status()
    return resp.json()


def check_image_sync(
    base_url: str,
    scanner_unit_id: int,
    image_path: Path,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Send one image synchronously to /inspections and return True/False result."""
    t0 = time.perf_counter()
    with image_path.open("rb") as f:
        resp = requests.post(
            f"{base_url.rstrip('/')}/inspections",
            data={
                "scannerUnitId": str(scanner_unit_id),
                "threshold": str(threshold),
                "fileName": image_path.name,
            },
            files={"file": (image_path.name, f, "application/octet-stream")},
            timeout=60,
        )
    resp.raise_for_status()
    data = resp.json()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    passed = bool(data.get("passed", data.get("overall_decision") == "PASS"))
    return {
        "file": image_path.name,
        "passed": passed,
        "decision": data.get("overall_decision", "UNKNOWN"),
        "score": data.get("quality_score", 0),
        "inspection_id": data.get("inspectionId", ""),
        "latency_ms": elapsed_ms,
    }


def check_image_async(
    base_url: str,
    scanner_unit_id: int,
    image_path: Path,
    threshold: float = 0.5,
    poll_interval: float = 0.15,
) -> dict[str, Any]:
    """Submit one image to /jobs (high-throughput queue) and poll until True/False is ready."""
    t0 = time.perf_counter()
    with image_path.open("rb") as f:
        sub = requests.post(
            f"{base_url.rstrip('/')}/jobs",
            data={
                "scanner_unit_id": str(scanner_unit_id),
                "threshold": str(threshold),
                "priority": "5",
            },
            files={"file": (image_path.name, f, "application/octet-stream")},
            timeout=15,
        )
    sub.raise_for_status()
    batch_id = sub.json()["batch_id"]

    while True:
        res = requests.get(f"{base_url.rstrip('/')}/batches/{batch_id}/results", timeout=10)
        res.raise_for_status()
        items = res.json().get("items", [])
        if items:
            item = items[0]
            if item["execution_status"] in ("COMPLETED", "FAILED", "CANCELLED"):
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
                passed = bool(item.get("passed", item.get("overall_decision") == "PASS"))
                return {
                    "file": image_path.name,
                    "passed": passed,
                    "decision": item.get("overall_decision") or item["execution_status"],
                    "score": item.get("quality_score") or 0,
                    "inspection_id": item.get("inspection_id") or "",
                    "latency_ms": elapsed_ms,
                }
        time.sleep(poll_interval)


def run_stream(
    base_url: str = "http://127.0.0.1:8000/api/v1",
    scanner_unit_id: int | None = None,
    folder: Path = DEFAULT_SAMPLE_DIR,
    threshold: float = 0.5,
    delay_ms: int = 200,
    mode: str = "sync",
) -> list[dict[str, Any]]:
    units = list_scanner_units(base_url)
    if not units:
        raise RuntimeError("No Scanner Units found on server. Create one in PROMETHEUS-X first.")
    unit_id = scanner_unit_id if scanner_unit_id is not None else int(units[0]["id"])

    images = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    if not images:
        raise RuntimeError(f"No images found in {folder}")

    results: list[dict[str, Any]] = []
    print(f"[Simulator] Streaming {len(images)} image(s) from {folder} to Scanner Unit #{unit_id} ({mode})...")
    for img in images:
        res = (
            check_image_async(base_url, unit_id, img, threshold=threshold)
            if mode == "async"
            else check_image_sync(base_url, unit_id, img, threshold=threshold)
        )
        results.append(res)
        print(
            f"  {res['file']:20s} -> passed={str(res['passed']):5s} "
            f"| decision={res['decision']:15s} | score={res['score']} | {res['latency_ms']} ms"
        )
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

    passed_n = sum(1 for r in results if r["passed"])
    print(f"[Simulator] Done: {passed_n} True (PASS), {len(results) - passed_n} False (FAIL/REVIEW)")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PROMETHEUS-X Image Stream Simulator")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1", help="Backend API v1 URL")
    parser.add_argument("--unit-id", type=int, default=None, help="Scanner Unit ID (defaults to first unit)")
    parser.add_argument("--folder", type=Path, default=DEFAULT_SAMPLE_DIR, help="Folder of images to stream")
    parser.add_argument("--threshold", type=float, default=0.5, help="Anomaly threshold (0.0 - 1.0)")
    parser.add_argument("--delay-ms", type=int, default=200, help="Delay between requests in ms")
    parser.add_argument("--mode", choices=["sync", "async"], default="sync", help="Endpoint mode: sync (/inspections) or async (/jobs)")
    args = parser.parse_args()
    run_stream(
        base_url=args.url,
        scanner_unit_id=args.unit_id,
        folder=args.folder,
        threshold=args.threshold,
        delay_ms=args.delay_ms,
        mode=args.mode,
    )
