"""AI model adapters for CLOCKIT inference."""

from backend.app.models.anomalib_adapter import AnomalibCheckpointAdapter
from backend.app.models.anomalydino_adapter import AnomalyDINOAdapter
from backend.app.models.efficientad_adapter import EfficientAdAdapter
from backend.app.models.omnipose_adapter import OmniPoseAdapter
from backend.app.models.yolo_adapter import YoloSegAdapter

__all__ = ["AnomalibCheckpointAdapter", "AnomalyDINOAdapter", "EfficientAdAdapter", "OmniPoseAdapter", "YoloSegAdapter"]
