"""Model capability manifest catalogue driving Scanner Units, Datasets, and Training."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.core.config import BASE_DIR


def _file_exists(rel_path: str) -> bool:
    return bool(rel_path) and (BASE_DIR / rel_path).is_file()


def get_model_catalogue() -> list[dict[str, Any]]:
    """Return capability manifests for all known model adapters with live artifact checks."""
    efficientad_ckpt = "artifacts/trained/efficientad_casting.ckpt"
    efficientad_teacher_s = "artifacts/pretrained/pretrained_teacher_small.pth"
    efficientad_teacher_m = "artifacts/pretrained/pretrained_teacher_medium.pth"
    yolo_weights = "artifacts/pretrained/yolo11n-seg.pt"

    trained_efficientad = _file_exists(efficientad_ckpt)

    return [
        {
            "model_key": "efficientad_small",
            "display_name": "EfficientAD-Small",
            "model_family": "efficientad",
            "task": "Normal-only anomaly detection & localization",
            "integration_state": "available_integrated",
            "training_paradigm": "normal_only",
            "requires_dataset": True,
            "dataset_requirements": "Normal (defect-free) images for training; optional normal/abnormal test images for evaluation.",
            "supported_training_strategies": ["initial_training", "full_retraining"],
            "supported_outputs": [
                {
                    "key": "anomaly_score",
                    "label": "Anomaly score",
                    "description": "Image-level anomaly score (0.0–1.0).",
                },
                {
                    "key": "heatmap",
                    "label": "Anomaly heatmap",
                    "description": "Blended pixel-level anomaly localization overlay.",
                },
                {
                    "key": "bounding_boxes",
                    "label": "Anomaly bounding boxes",
                    "description": "Contours extracted from regions exceeding the anomaly threshold.",
                },
                {
                    "key": "confidence_score",
                    "label": "Model confidence",
                    "description": "Uncalibrated model confidence estimate.",
                },
            ],
            "limitations": "CPU training takes several minutes; learns normal appearance only (no defect class labels).",
            "pretrained_path": efficientad_teacher_s,
            "pretrained_present": _file_exists(efficientad_teacher_s),
            "trained_checkpoint_path": efficientad_ckpt if trained_efficientad else None,
            "ready_for_inference": trained_efficientad,
        },
        {
            "model_key": "opencv_heuristic",
            "display_name": "OpenCV Contrast Heuristic",
            "model_family": "opencv_heuristic",
            "task": "Deterministic surface contrast anomaly signal",
            "integration_state": "available_integrated",
            "training_paradigm": "heuristic_no_training",
            "requires_dataset": False,
            "dataset_requirements": "No dataset or training required. Deterministic Gaussian-blur difference.",
            "supported_training_strategies": [],
            "supported_outputs": [
                {
                    "key": "anomaly_score",
                    "label": "Anomaly score",
                    "description": "High-frequency contrast deviation score.",
                },
                {
                    "key": "bounding_boxes",
                    "label": "Contour bounding boxes",
                    "description": "Top contrast-deviation regions.",
                },
            ],
            "limitations": "Not a trained neural network; sensitive to lighting gradients and normal surface texture.",
            "pretrained_path": None,
            "pretrained_present": True,
            "trained_checkpoint_path": None,
            "ready_for_inference": True,
        },
        {
            "model_key": "efficientad_medium",
            "display_name": "EfficientAD-Medium",
            "model_family": "efficientad",
            "task": "Higher-capacity normal-only anomaly detection",
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
            "limitations": "Higher capacity than Small; slower on CPU without CUDA GPU.",
            "pretrained_path": efficientad_teacher_m,
            "pretrained_present": _file_exists(efficientad_teacher_m),
            "trained_checkpoint_path": trained_efficientad and efficientad_ckpt or None,
            "ready_for_inference": trained_efficientad,
        },
        {
            "model_key": "yolo11n_seg",
            "display_name": "YOLO11n-Seg",
            "model_family": "yolo_seg",
            "task": "Object & defect detection + segmentation",
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
            "pretrained_path": yolo_weights,
            "pretrained_present": _file_exists(yolo_weights),
            "trained_checkpoint_path": yolo_weights if _file_exists(yolo_weights) else None,
            "ready_for_inference": _file_exists(yolo_weights),
        },
    ]


def get_model_capability(model_key: str) -> dict[str, Any] | None:
    return next((m for m in get_model_catalogue() if m["model_key"] == model_key), None)
