"""AI model adapters for CLOCKIT inference."""

from backend.app.models.efficientad_adapter import EfficientAdAdapter
from backend.app.models.yolo_adapter import YoloSegAdapter

__all__ = ["EfficientAdAdapter", "YoloSegAdapter"]
