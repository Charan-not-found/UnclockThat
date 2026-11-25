"""Train EfficientAD on the casting dataset using local pretrained teacher weights."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

# Set writable cache dirs and ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TMP_DIR = ROOT / "storage" / "temporary"
TMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(TMP_DIR / "mpl"))
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import torch  # noqa: E402
from anomalib.data import Folder  # noqa: E402
from anomalib.engine import Engine  # noqa: E402
from anomalib.models.image.efficient_ad.lightning_model import (  # noqa: E402
    EfficientAd,
    get_pretrained_weights_dir,
)


def _prepare_local_teacher_weights() -> None:
    """Copy local pretrained_teacher_small.pth into anomalib's weights cache."""
    local_weights = ROOT / "artifacts" / "pretrained" / "pretrained_teacher_small.pth"
    if not local_weights.is_file():
        raise FileNotFoundError(f"Missing pretrained weights: {local_weights}")

    target_dir = get_pretrained_weights_dir() / "efficientad_pretrained_weights"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "pretrained_teacher_small.pth"
    if not target_file.is_file():
        shutil.copy2(local_weights, target_file)
        print(f"Copied local teacher weights -> {target_file}")


def _prepare_aux_imagenette_dir(aux_dir: Path, max_images: int = 120) -> Path:
    """Populate a local auxiliary folder so EfficientAd does not download 1.5GB Imagenette."""
    class_dir = aux_dir / "aux_class"
    if class_dir.is_dir() and len(list(class_dir.glob("*.*"))) >= 20:
        return aux_dir

    class_dir.mkdir(parents=True, exist_ok=True)
    src_dir = ROOT / "data" / "raw" / "pcb" / "Data_YOLO" / "images" / "train"
    if not src_dir.is_dir():
        src_dir = ROOT / "data" / "raw" / "casting" / "casting_data" / "casting_data" / "train" / "ok_front"

    copied = 0
    for img_path in sorted(src_dir.iterdir()):
        if img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
            shutil.copy2(img_path, class_dir / img_path.name)
            copied += 1
            if copied >= max_images:
                break
    print(f"Prepared {copied} local auxiliary images in {class_dir}")
    return aux_dir


def _update_db_model(ckpt_path: Path, metrics: dict) -> None:
    """Register the trained checkpoint and metrics in clockit.db."""
    from backend.app.database.connection import SessionLocal, init_db
    from backend.app.database.repositories.model_repository import ModelConfigRepository

    init_db()
    db = SessionLocal()
    try:
        repo = ModelConfigRepository(db)
        models = repo.list_all(limit=200)
        target = next((m for m in models if "EfficientAD-Small" in m.name), None)
        if target is not None:
            repo.update(
                target,
                weights_file_path=str(ckpt_path.relative_to(ROOT)),
                dataset_dir_path="data/raw/casting/casting_data/casting_data",
                metrics_json=metrics,
                is_active=True,
            )
            db.commit()
            print(f"Updated DB model ID={target.id} ({target.name}) -> active=True, weights={ckpt_path.relative_to(ROOT)}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train EfficientAD on casting dataset")
    parser.add_argument("--max-epochs", type=int, default=2, help="Max training epochs")
    parser.add_argument("--limit-train-batches", type=int, default=150, help="Batches per epoch (CPU-friendly)")
    parser.add_argument("--limit-val-batches", type=int, default=30, help="Validation batches")
    parser.add_argument("--limit-test-batches", type=int, default=30, help="Test batches")
    args = parser.parse_args()

    _prepare_local_teacher_weights()
    aux_dir = _prepare_aux_imagenette_dir(TMP_DIR / "aux_imagenette")

    dataset_root = ROOT / "data" / "raw" / "casting" / "casting_data" / "casting_data"
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"Casting dataset not found at {dataset_root}")

    datamodule = Folder(
        name="casting",
        root=dataset_root,
        normal_dir="train/ok_front",
        abnormal_dir="test/def_front",
        normal_test_dir="test/ok_front",
        train_batch_size=1,
        eval_batch_size=16,
        num_workers=0,
    )

    model = EfficientAd(
        model_size="small",
        imagenet_dir=str(aux_dir),
    )

    ckpt_dir = ROOT / "artifacts" / "checkpoints" / "efficientad_casting"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    engine = Engine(
        default_root_dir=str(ckpt_dir),
        max_epochs=args.max_epochs,
        limit_train_batches=args.limit_train_batches,
        limit_val_batches=args.limit_val_batches,
        limit_test_batches=args.limit_test_batches,
        accelerator="cpu",
        logger=False,
        enable_progress_bar=True,
    )

    print(f"Starting EfficientAD-Small training (epochs={args.max_epochs}, train_batches={args.limit_train_batches})...")
    engine.fit(model=model, datamodule=datamodule)

    print("Evaluating on held-out test split...")
    test_results = engine.test(model=model, datamodule=datamodule)
    metrics = {}
    if test_results:
        for k, v in test_results[0].items():
            metrics[k] = round(float(v), 4) if isinstance(v, (int, float)) else v
    print("Test metrics:", metrics)

    trained_dir = ROOT / "artifacts" / "trained"
    trained_dir.mkdir(parents=True, exist_ok=True)
    final_ckpt = trained_dir / "efficientad_casting.ckpt"

    best_ckpt = getattr(engine.trainer.checkpoint_callback, "best_model_path", "")
    if best_ckpt and Path(best_ckpt).is_file():
        shutil.copy2(best_ckpt, final_ckpt)
    else:
        engine.trainer.save_checkpoint(str(final_ckpt))
    print(f"Saved trained model -> {final_ckpt}")

    _update_db_model(final_ckpt, metrics)


if __name__ == "__main__":
    main()
