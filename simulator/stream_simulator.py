"""PROMETHEUS-X Line Simulator (CLI + shared helpers).

Streams images from a ZIP archive in simulator/sample_data/ (or loose images in a folder)
one by one to the PROMETHEUS-X backend and receives True (PASS) / False (FAIL or REVIEW_REQUIRED)
for every inspection check.
"""

from __future__ import annotations

import argparse
import time
import zipfile
from pathlib import Path
from typing import Any

import requests

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parent / "sample_data"


def list_scanner_units(base_url: str) -> list[dict[str, Any]]:
    resp = requests.get(f"{base_url.rstrip('/')}/scanner-units", timeout=10)
    resp.raise_for_status()
    return resp.json()


def list_zip_archives(folder: Path = DEFAULT_SAMPLE_DIR) -> list[Path]:
    if not folder.is_dir():
        return []
    return [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() == ".zip"]


def list_images_in_zip(zip_path: Path) -> list[str]:
    if not zip_path.is_file():
        return []
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = [
            info.filename
            for info in zf.infolist()
            if not info.is_dir() and Path(info.filename).suffix.lower() in IMAGE_EXTS
        ]
    return sorted(members)


def read_image_bytes(source: Path, member_name: str) -> tuple[str, bytes]:
    """Read image bytes either from a ZIP archive member or a file inside a directory."""
    if source.is_file() and source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source, "r") as zf:
            return Path(member_name).name, zf.read(member_name)
    target = source / Path(member_name).name
    return target.name, target.read_bytes()


def check_bytes_sync(
    base_url: str,
    scanner_unit_id: int,
    filename: str,
    raw_bytes: bytes,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Send one image byte payload synchronously to /inspections and return True/False result."""
    t0 = time.perf_counter()
    resp = requests.post(
        f"{base_url.rstrip('/')}/inspections",
        data={
            "scannerUnitId": str(scanner_unit_id),
            "threshold": str(threshold),
            "fileName": filename,
        },
        files={"file": (filename, raw_bytes, "application/octet-stream")},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    passed = bool(data.get("passed", data.get("overall_decision") == "PASS"))
    return {
        "file": filename,
        "passed": passed,
        "decision": data.get("overall_decision", "UNKNOWN"),
        "score": data.get("quality_score", 0),
        "inspection_id": data.get("inspectionId", ""),
        "latency_ms": elapsed_ms,
    }


def check_bytes_async(
    base_url: str,
    scanner_unit_id: int,
    filename: str,
    raw_bytes: bytes,
    threshold: float = 0.5,
    poll_interval: float = 0.15,
) -> dict[str, Any]:
    """Submit one image byte payload to /jobs and poll until True/False is ready."""
    t0 = time.perf_counter()
    sub = requests.post(
        f"{base_url.rstrip('/')}/jobs",
        data={
            "scanner_unit_id": str(scanner_unit_id),
            "threshold": str(threshold),
            "priority": "5",
        },
        files={"file": (filename, raw_bytes, "application/octet-stream")},
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
                    "file": filename,
                    "passed": passed,
                    "decision": item.get("overall_decision") or item["execution_status"],
                    "score": item.get("quality_score") or 0,
                    "inspection_id": item.get("inspection_id") or "",
                    "latency_ms": elapsed_ms,
                }
        time.sleep(poll_interval)


def check_image_sync(
    base_url: str,
    scanner_unit_id: int,
    image_path: Path,
    threshold: float = 0.5,
) -> dict[str, Any]:
    return check_bytes_sync(base_url, scanner_unit_id, image_path.name, image_path.read_bytes(), threshold=threshold)


def check_image_async(
    base_url: str,
    scanner_unit_id: int,
    image_path: Path,
    threshold: float = 0.5,
    poll_interval: float = 0.15,
) -> dict[str, Any]:
    return check_bytes_async(
        base_url, scanner_unit_id, image_path.name, image_path.read_bytes(), threshold=threshold, poll_interval=poll_interval
    )


def run_stream(
    base_url: str = "http://127.0.0.1:8000/api/v1",
    scanner_unit_id: int | None = None,
    source: Path = DEFAULT_SAMPLE_DIR,
    threshold: float = 0.5,
    delay_ms: int = 200,
    mode: str = "sync",
) -> list[dict[str, Any]]:
    units = list_scanner_units(base_url)
    if not units:
        raise RuntimeError("No Scanner Units found on server. Create one in PROMETHEUS-X first.")
    unit_id = scanner_unit_id if scanner_unit_id is not None else int(units[0]["id"])

    if source.is_file() and source.suffix.lower() == ".zip":
        entries = list_images_in_zip(source)
    else:
        entries = [p.name for p in sorted(source.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    if not entries:
        raise RuntimeError(f"No images found in {source}")

    results: list[dict[str, Any]] = []
    print(f"[Simulator] Streaming {len(entries)} image(s) from {source} to Scanner Unit #{unit_id} ({mode})...")
    for entry in entries:
        fname, raw = read_image_bytes(source, entry)
        res = (
            check_bytes_async(base_url, unit_id, fname, raw, threshold=threshold)
            if mode == "async"
            else check_bytes_sync(base_url, unit_id, fname, raw, threshold=threshold)
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
    parser.add_argument("--source", type=Path, default=DEFAULT_SAMPLE_DIR, help="ZIP archive or folder of images")
    parser.add_argument("--threshold", type=float, default=0.5, help="Anomaly threshold (0.0 - 1.0)")
    parser.add_argument("--delay-ms", type=int, default=200, help="Delay between requests in ms")
    parser.add_argument("--mode", choices=["sync", "async"], default="sync", help="Endpoint mode: sync (/inspections) or async (/jobs)")
    args = parser.parse_args()
    run_stream(
        base_url=args.url,
        scanner_unit_id=args.unit_id,
        source=args.source,
        threshold=args.threshold,
        delay_ms=args.delay_ms,
        mode=args.mode,
    )
