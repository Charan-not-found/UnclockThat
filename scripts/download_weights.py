"""Download all real model weights for CLOCKIT prototype."""
import urllib.request
import zipfile
import os
import sys
import shutil

dest = "artifacts/pretrained"
os.makedirs(dest, exist_ok=True)

# ── 1. EfficientAD pretrained teacher weights (from anomalib) ─────────────────
efficientad_zip = os.path.join(dest, "_efficientad_tmp.zip")
efficientad_url = (
    "https://github.com/open-edge-platform/anomalib/releases/download/"
    "efficientad_pretrained_weights/efficientad_pretrained_weights.zip"
)

small_dst = os.path.join(dest, "pretrained_teacher_small.pth")
medium_dst = os.path.join(dest, "pretrained_teacher_medium.pth")

if os.path.isfile(small_dst) and os.path.isfile(medium_dst):
    print(f"SKIP EfficientAD weights (already present)")
else:
    print(f"Downloading EfficientAD pretrained teacher weights...")
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                pct = count * block_size * 100 // total_size
                if count % 100 == 0:
                    print(f"  {pct}%", flush=True)

        urllib.request.urlretrieve(efficientad_url, efficientad_zip, reporthook)
        print(f"  Downloaded: {os.path.getsize(efficientad_zip):,} bytes")

        # Extract and find the .pth files
        with zipfile.ZipFile(efficientad_zip, "r") as z:
            names = z.namelist()
            print(f"  ZIP contents: {names}")
            z.extractall(dest)

        # Find extracted .pth files and rename to our expected names
        for root, dirs, files in os.walk(dest):
            for f in files:
                lower = f.lower()
                full = os.path.join(root, f)
                if full in (small_dst, medium_dst):
                    continue
                if "small" in lower and lower.endswith(".pth"):
                    print(f"  Renaming {f} -> pretrained_teacher_small.pth")
                    shutil.copy2(full, small_dst)
                elif "medium" in lower and lower.endswith(".pth"):
                    print(f"  Renaming {f} -> pretrained_teacher_medium.pth")
                    shutil.copy2(full, medium_dst)
                elif lower.endswith(".pth") and "teacher" in lower:
                    # Fallback: first .pth as small
                    if not os.path.isfile(small_dst):
                        print(f"  Using {f} as pretrained_teacher_small.pth")
                        shutil.copy2(full, small_dst)

        os.remove(efficientad_zip)

        for name, path in [("small", small_dst), ("medium", medium_dst)]:
            if os.path.isfile(path):
                print(f"  OK {name}: {os.path.getsize(path):,} bytes")
            else:
                print(f"  WARNING: {name} not found after extraction")

    except Exception as e:
        print(f"  ERROR downloading EfficientAD weights: {e}")
        if os.path.isfile(efficientad_zip):
            os.remove(efficientad_zip)

# ── 2. YOLO11n-Seg ─────────────────────────────────────────────────────────────
yolo_dst = os.path.join(dest, "yolo11n-seg.pt")
if os.path.isfile(yolo_dst) and os.path.getsize(yolo_dst) > 100_000:
    print(f"SKIP YOLO11n-seg (already present, {os.path.getsize(yolo_dst):,} bytes)")
else:
    print("Downloading YOLO11n-seg via Ultralytics...")
    try:
        from ultralytics import YOLO
        # This downloads and caches the model
        model = YOLO("yolo11n-seg.pt")
        # Find where ultralytics cached it
        candidates = []
        # Ultralytics usually puts it in the CWD or ~/.config/Ultralytics/
        for search_root in [".", os.path.expanduser("~"), os.path.expanduser("~/.config")]:
            for root, dirs, files in os.walk(search_root):
                for f in files:
                    if f == "yolo11n-seg.pt":
                        candidates.append(os.path.join(root, f))
                # Don't walk too deep
                if root.count(os.sep) - search_root.count(os.sep) > 4:
                    dirs.clear()

        # Also check default ultralytics weights dir
        import pathlib
        for candidate_path in [
            pathlib.Path("yolo11n-seg.pt"),
            pathlib.Path.home() / ".config" / "Ultralytics" / "yolo11n-seg.pt",
            pathlib.Path.home() / "yolo11n-seg.pt",
        ]:
            if candidate_path.is_file() and str(candidate_path) not in candidates:
                candidates.append(str(candidate_path))

        if candidates:
            best = max(candidates, key=lambda p: os.path.getsize(p))
            shutil.copy2(best, yolo_dst)
            print(f"  OK: Copied from {best} -> {yolo_dst}  ({os.path.getsize(yolo_dst):,} bytes)")
        else:
            print("  Could not locate downloaded yolo11n-seg.pt — copying from model object")
            # Try accessing via model.ckpt_path
            if hasattr(model, "ckpt_path") and model.ckpt_path:
                shutil.copy2(model.ckpt_path, yolo_dst)
                print(f"  OK via ckpt_path: {os.path.getsize(yolo_dst):,} bytes")

    except ImportError:
        print("  ultralytics not installed — trying direct download")
        try:
            yolo_url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-seg.pt"
            urllib.request.urlretrieve(yolo_url, yolo_dst)
            print(f"  OK: {os.path.getsize(yolo_dst):,} bytes")
        except Exception as e2:
            print(f"  ERROR: {e2}")
    except Exception as e:
        print(f"  ERROR: {e}")

# ── 3. Final summary ───────────────────────────────────────────────────────────
print("\n=== Artifact summary ===")
for name in ["pretrained_teacher_small.pth", "pretrained_teacher_medium.pth", "yolo11n-seg.pt"]:
    path = os.path.join(dest, name)
    if os.path.isfile(path):
        print(f"  ✓ {name}  {os.path.getsize(path):,} bytes")
    else:
        print(f"  ✗ {name}  MISSING")
