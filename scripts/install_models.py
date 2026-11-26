"""Download and verify all pretrained AI model weights for CLOCKIT."""

from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRETRAINED_DIR = ROOT / "models" / "base"


def _download_yolo(filename: str, fallback_url: str) -> bool:
    dst = PRETRAINED_DIR / filename
    if not dst.is_file():
        print(f"Downloading {filename}...")
        try:
            from ultralytics import YOLO
            YOLO(filename)
            local_pt = Path(filename)
            if local_pt.is_file():
                shutil.move(str(local_pt), str(dst))
        except Exception:
            urllib.request.urlretrieve(fallback_url, dst)
    return dst.is_file()


def install_all_models() -> dict[str, bool]:
    """Ensure all pretrained weights exist in artifacts/pretrained/ and backbone caches."""
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

    # 2. YOLO11n-Seg & YOLO11m-Seg (stronger medium detection/segmentation model)
    status["yolo11n-seg.pt"] = _download_yolo(
        "yolo11n-seg.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n-seg.pt",
    )
    status["yolo11m-seg.pt"] = _download_yolo(
        "yolo11m-seg.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11m-seg.pt",
    )

    # 3. Pre-cache PatchCore (wide_resnet50_2) and Dinomaly (DINOv2 ViT-B/14) backbones
    try:
        import timm
        print("Caching PatchCore backbone (wide_resnet50_2)...")
        timm.create_model("wide_resnet50_2", pretrained=True)
        status["patchcore_wide_resnet50_2 (timm cache)"] = True
    except Exception as exc:
        print(f"Warning caching wide_resnet50_2: {exc}")
        status["patchcore_wide_resnet50_2 (timm cache)"] = False

    try:
        from anomalib.models import Dinomaly
        print("Caching Dinomaly ViT-B/14 DINOv2 backbone...")
        Dinomaly()
        status["dinomaly_vit_base_dinov2 (cache)"] = True
    except Exception as exc:
        print(f"Warning caching Dinomaly: {exc}")
        status["dinomaly_vit_base_dinov2 (cache)"] = False

    print("\n=== CLOCKIT Pretrained Model Status ===")
    for name, ok in status.items():
        path = PRETRAINED_DIR / name
        if path.is_file():
            print(f"  [OK] {name} ({path.stat().st_size:,} bytes)")
        else:
            print(f"  [{'OK' if ok else 'MISSING'}] {name}")
    return status


if __name__ == "__main__":
    install_all_models()
