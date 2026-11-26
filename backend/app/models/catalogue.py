"""Model capability manifest catalogue driving Scanner Units, Datasets, and Training."""

from __future__ import annotations

from typing import Any

from backend.app.core.config import BASE_DIR


def _file_exists(rel_path: str) -> bool:
    return bool(rel_path) and (BASE_DIR / rel_path).is_file()


def _get_disabled_model_keys() -> set[str]:
    """Read disabled model_key toggles from SQLite without failing if DB isn't initialized."""
    try:
        from sqlalchemy import select
        from backend.app.database.connection import SessionLocal
        from backend.app.database.models.scanner import ModelToggleSetting

        db = SessionLocal()
        try:
            rows = db.scalars(
                select(ModelToggleSetting).where(ModelToggleSetting.is_enabled.is_(False))
            ).all()
            return {r.model_key for r in rows}
        finally:
            db.close()
    except Exception:
        return set()


def get_model_catalogue() -> list[dict[str, Any]]:
    """Return capability manifests for all integrated AI models with live artifact & toggle checks."""
    efficientad_ckpt = "models/custom/efficientad_casting.ckpt"
    efficientad_teacher_s = "models/base/pretrained_teacher_small.pth"
    efficientad_teacher_m = "models/base/pretrained_teacher_medium.pth"
    yolo_n_weights = "models/base/yolo11n-seg.pt"
    yolo_m_weights = "models/base/yolo11m-seg.pt"

    trained_efficientad = _file_exists(efficientad_ckpt)
    disabled_keys = _get_disabled_model_keys()

    items = [
        {
            "model_key": "patchcore",
            "display_name": "PatchCore (WideResNet-50)",
            "model_family": "patchcore",
            "task": "Medium Speed · High-accuracy normal-only surface & structural anomaly detection (WideResNet-50 coreset memory bank)",
            "integration_state": "available_integrated",
            "training_paradigm": "normal_only",
            "requires_dataset": True,
            "dataset_requirements": "Normal (defect-free) images. Fits coreset memory bank in seconds on GPU without gradient epochs.",
            "supported_training_strategies": ["initial_training", "full_retraining"],
            "supported_outputs": [
                {"key": "anomaly_score", "label": "Anomaly score", "description": "Image-level nearest-neighbor distance score."},
                {"key": "heatmap", "label": "Anomaly heatmap", "description": "Patch-level anomaly localization overlay."},
                {"key": "bounding_boxes", "label": "Anomaly bounding boxes", "description": "Thresholded anomaly contours."},
                {"key": "confidence_score", "label": "Model confidence", "description": "Uncalibrated confidence estimate."},
            ],
            "limitations": "Requires training on a normal dataset for your product before running inference.",
            "pretrained_path": None,
            "pretrained_present": True,
            "trained_checkpoint_path": None,
            "ready_for_inference": False,
        },
        {
            "model_key": "dinomaly",
            "display_name": "Dinomaly (DINOv2 ViT-B/14)",
            "model_family": "dinomaly",
            "task": "Low Speed · High-precision Vision Transformer normal-only anomaly detection & fine defect localization",
            "integration_state": "available_integrated",
            "training_paradigm": "normal_only",
            "requires_dataset": True,
            "dataset_requirements": "Normal (defect-free) images for Vision Transformer reconstruction training.",
            "supported_training_strategies": ["initial_training", "full_retraining"],
            "supported_outputs": [
                {"key": "anomaly_score", "label": "Anomaly score", "description": "Image-level ViT reconstruction score."},
                {"key": "heatmap", "label": "Anomaly heatmap", "description": "High-resolution ViT anomaly map."},
                {"key": "bounding_boxes", "label": "Anomaly bounding boxes", "description": "Thresholded anomaly contours."},
                {"key": "confidence_score", "label": "Model confidence", "description": "Uncalibrated confidence estimate."},
            ],
            "limitations": "Uses DINOv2 ViT-B/14 (~340 MB); recommended to train on GPU (RTX 3050).",
            "pretrained_path": None,
            "pretrained_present": True,
            "trained_checkpoint_path": None,
            "ready_for_inference": False,
        },
        {
            "model_key": "efficientad_medium",
            "display_name": "EfficientAD-Medium",
            "model_family": "efficientad",
            "task": "Medium-High Speed · Balanced normal-only surface anomaly detection & pixel localization",
            "integration_state": "available_integrated",
            "training_paradigm": "normal_only",
            "requires_dataset": True,
            "dataset_requirements": "Normal (defect-free) images for training.",
            "supported_training_strategies": ["initial_training", "full_retraining"],
            "supported_outputs": [
                {"key": "anomaly_score", "label": "Anomaly score", "description": "Image-level score."},
                {"key": "heatmap", "label": "Anomaly heatmap", "description": "Pixel-level map."},
                {"key": "bounding_boxes", "label": "Anomaly bounding boxes", "description": "Thresholded anomaly contours."},
                {"key": "confidence_score", "label": "Model confidence", "description": "Uncalibrated confidence estimate."},
            ],
            "limitations": "Higher capacity than Small; requires training on your dataset.",
            "pretrained_path": efficientad_teacher_m,
            "pretrained_present": _file_exists(efficientad_teacher_m),
            "trained_checkpoint_path": efficientad_ckpt if trained_efficientad else None,
            "ready_for_inference": trained_efficientad,
        },
        {
            "model_key": "efficientad_small",
            "display_name": "EfficientAD-Small",
            "model_family": "efficientad",
            "task": "High Speed · Real-time normal-only surface anomaly detection & heatmap localization",
            "integration_state": "available_integrated",
            "training_paradigm": "normal_only",
            "requires_dataset": True,
            "dataset_requirements": "Normal (defect-free) images for training.",
            "supported_training_strategies": ["initial_training", "full_retraining"],
            "supported_outputs": [
                {"key": "anomaly_score", "label": "Anomaly score", "description": "Image-level anomaly score (0.0–1.0)."},
                {"key": "heatmap", "label": "Anomaly heatmap", "description": "Blended pixel-level anomaly localization overlay."},
                {"key": "bounding_boxes", "label": "Anomaly bounding boxes", "description": "Contours extracted from regions exceeding the threshold."},
                {"key": "confidence_score", "label": "Model confidence", "description": "Uncalibrated model confidence estimate."},
            ],
            "limitations": "Learns normal appearance only (no defect class labels).",
            "pretrained_path": efficientad_teacher_s,
            "pretrained_present": _file_exists(efficientad_teacher_s),
            "trained_checkpoint_path": efficientad_ckpt if trained_efficientad else None,
            "ready_for_inference": trained_efficientad,
        },
        {
            "model_key": "yolo11m_seg",
            "display_name": "YOLO11m-Seg (Medium)",
            "model_family": "yolo_seg",
            "task": "Medium Speed · High-accuracy supervised object/defect bounding-box detection & instance segmentation",
            "integration_state": "available_integrated",
            "training_paradigm": "supervised_masks",
            "requires_dataset": False,
            "dataset_requirements": "Runs pretrained inference immediately; optional labelled YOLO dataset for fine-tuning.",
            "supported_training_strategies": ["fine_tuning"],
            "supported_outputs": [
                {"key": "bounding_boxes", "label": "Bounding boxes", "description": "Predicted detection boxes."},
                {"key": "defect_class", "label": "Defect class", "description": "Predicted object/defect category."},
                {"key": "segmentation_mask", "label": "Segmentation mask", "description": "Pixel-level segmentation overlay."},
                {"key": "confidence_score", "label": "Detection confidence", "description": "Per-box detection confidence."},
            ],
            "limitations": "Higher accuracy than YOLO11n-Seg (~40 MB); pretrained on COCO until fine-tuned.",
            "pretrained_path": yolo_m_weights,
            "pretrained_present": _file_exists(yolo_m_weights),
            "trained_checkpoint_path": yolo_m_weights if _file_exists(yolo_m_weights) else None,
            "ready_for_inference": _file_exists(yolo_m_weights),
        },
        {
            "model_key": "yolo11n_seg",
            "display_name": "YOLO11n-Seg (Nano)",
            "model_family": "yolo_seg",
            "task": "High Speed · Real-time lightweight supervised object/defect detection & segmentation masks",
            "integration_state": "available_integrated",
            "training_paradigm": "supervised_masks",
            "requires_dataset": False,
            "dataset_requirements": "Runs pretrained inference immediately; optional labelled YOLO dataset for fine-tuning.",
            "supported_training_strategies": ["fine_tuning"],
            "supported_outputs": [
                {"key": "bounding_boxes", "label": "Bounding boxes", "description": "Predicted detection boxes."},
                {"key": "defect_class", "label": "Defect class", "description": "Predicted object/defect category."},
                {"key": "segmentation_mask", "label": "Segmentation mask", "description": "Pixel-level segmentation overlay."},
                {"key": "confidence_score", "label": "Detection confidence", "description": "Per-box detection confidence."},
            ],
            "limitations": "Pretrained on COCO classes; fine-tuning requires YOLO-format labels.",
            "pretrained_path": yolo_n_weights,
            "pretrained_present": _file_exists(yolo_n_weights),
            "trained_checkpoint_path": yolo_n_weights if _file_exists(yolo_n_weights) else None,
            "ready_for_inference": _file_exists(yolo_n_weights),
        },
        {
            "model_key": "opencv_heuristic",
            "display_name": "OpenCV Contrast Heuristic",
            "model_family": "opencv_heuristic",
            "task": "Ultra-High Speed · Deterministic contrast-deviation & edge irregularity detection (non-AI fallback)",
            "integration_state": "available_integrated",
            "training_paradigm": "heuristic_no_training",
            "requires_dataset": False,
            "dataset_requirements": "No dataset or training required.",
            "supported_training_strategies": [],
            "supported_outputs": [
                {"key": "anomaly_score", "label": "Anomaly score", "description": "High-frequency contrast deviation score."},
                {"key": "bounding_boxes", "label": "Contour bounding boxes", "description": "Top contrast-deviation regions."},
            ],
            "limitations": "Not a trained neural network; sensitive to lighting gradients.",
            "pretrained_path": None,
            "pretrained_present": True,
            "trained_checkpoint_path": None,
            "ready_for_inference": True,
        },
        {
            "model_key": "omniposead",
            "display_name": "OmniPoseAD (Pose-Agnostic 3D)",
            "model_family": "omniposead",
            "task": "Low Speed · Pose-agnostic multi-view anomaly detection (DINOv2 viewpoint retrieval + homography alignment)",
            "integration_state": "available_integrated",
            "training_paradigm": "multi_view_pose_agnostic",
            "requires_dataset": True,
            "dataset_requirements": "Normal images across viewpoints. Builds a pose-aligned DINOv2 reference bank.",
            "supported_training_strategies": ["initial_training", "full_retraining"],
            "supported_outputs": [
                {"key": "anomaly_score", "label": "Anomaly score", "description": "Pose-aligned image-level anomaly score."},
                {"key": "heatmap", "label": "Pixel difference map", "description": "View-aligned patch-cosine anomaly heatmap."},
                {"key": "bounding_boxes", "label": "Anomaly bounding boxes", "description": "Thresholded pose-aligned anomaly contours."},
                {"key": "confidence_score", "label": "Viewpoint confidence", "description": "Nearest-viewpoint similarity confidence."},
            ],
            "limitations": "Requires training on normal reference viewpoints; slower than single-view models due to viewpoint alignment.",
            "pretrained_path": None,
            "pretrained_present": True,
            "trained_checkpoint_path": None,
            "ready_for_inference": False,
        },
        {
            "model_key": "anomalydino",
            "display_name": "AnomalyDINO (DINOv2 Few-Shot)",
            "model_family": "anomalydino",
            "task": "High Speed (Inference) · Few-shot & training-free DINOv2 patch-NN anomaly detection (PCA patch masking + cosine distance + mean top-1% aggregation)",
            "integration_state": "available_integrated",
            "training_paradigm": "few_shot_patch_nn",
            "requires_dataset": True,
            "dataset_requirements": "Few-shot or full normal (defect-free) images. Automatically augments <=16 images and builds a PCA-masked DINOv2 patch memory bank.",
            "supported_training_strategies": ["initial_training", "full_retraining"],
            "supported_outputs": [
                {"key": "anomaly_score", "label": "Anomaly score", "description": "Mean top-1% cosine-NN tail anomaly score (0.0–1.0)."},
                {"key": "heatmap", "label": "Anomaly heatmap", "description": "PCA-masked DINOv2 patch distance overlay."},
                {"key": "bounding_boxes", "label": "Anomaly bounding boxes", "description": "Thresholded anomaly contours."},
                {"key": "confidence_score", "label": "Model confidence", "description": "Patch-distance separation confidence."},
            ],
            "limitations": "Custom WACV 2025 implementation using frozen DINOv2 ViT-B/14; requires building the normal memory bank on your dataset first.",
            "pretrained_path": None,
            "pretrained_present": True,
            "trained_checkpoint_path": None,
            "ready_for_inference": False,
        },
    ]

    for item in items:
        enabled = item["model_key"] not in disabled_keys
        item["is_enabled"] = enabled
        if not enabled:
            item["integration_state"] = "disabled_by_admin"
    return items


def get_model_capability(model_key: str) -> dict[str, Any] | None:
    return next((m for m in get_model_catalogue() if m["model_key"] == model_key), None)
