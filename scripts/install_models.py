"""Download and verify all missing pretrained AI model weights for CLOCKIT."""

from __future__ import annotations

import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRETRAINED_DIR = ROOT / "artifacts" / "pretrained"


def install_all_models() -> dict[str, bool]:
    """Ensure all required pretrained weights exist in artifacts/pretrained/."""
    PRETRAINED_DIR.mkdir(parents=True, exist_ok=True)
    status: dict[str, bool] = {}

    # 1. EfficientAD-Small & Medium teacher weights
    small_dst = PRETRAINED_DIR / "pretrained_teacher_small.pth"
    medium_dst = PRETRAINED_DIR / "pretrained_teacher_medium.pth"
    if not (small_dst.is_file() and medium_dst.is_file()):
        tmp_zip = PRETRAINED_DIR / "_efficientad_tmp.zip"
        url = (
            "https://github.com/open-edge-platform/anomalib/releases/download/"
            "efficientad_pretrained_weights/efficientad_pretrained_weights.zip"
        )
        print("Downloading EfficientAD pretrained teacher weights...")
        urllib.request.urlretrieve(url, tmp_zip)
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                fname = Path(member.filename).name.lower()
                if fname == "pretrained_teacher_small.pth":
                    small_dst.write_bytes(zf.read(member))
                elif fname == "pretrained_teacher_medium.pth":
                    medium_dst.write_bytes(zf.read(member))
        tmp_zip.unlink(missing_ok=True)

    status["pretrained_teacher_small.pth"] = small_dst.is_file()
    status["pretrained_teacher_medium.pth"] = medium_dst.is_file()

    # 2. YOLO11n-Seg weights
    yolo_seg_dst = PRETRAINED_DIR / "yolo11n-seg.pt"
    if not yolo_seg_dst.is_file():
        print("Downloading YOLO11n-Seg weights...")
        try:
            from ultralytics import YOLO
            YOLO("yolo11n-seg.pt")
            local_pt = Path("yolo11n-seg.pt")
            if local_pt.is_file():
                shutil.move(str(local_pt), str(yolo_seg_dst))
        except Exception:
            urllib.request.urlretrieve(
                "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n-seg.pt",
                yolo_seg_dst,
            )

    status["yolo11n-seg.pt"] = yolo_seg_dst.is_file()

    print("\n=== CLOCKIT Pretrained Model Status ===")
    for name, ok in status.items():
        size = (PRETRAINED_DIR / name).stat().st_size if ok else 0
        print(f"  {'[OK]' if ok else '[MISSING]'} {name} ({size:,} bytes)")
    return status


if __name__ == "__main__":
    install_all_models()
