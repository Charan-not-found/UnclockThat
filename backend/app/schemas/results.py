"""Standardized inspection and model result Pydantic contracts."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DefectDetectionSchema(BaseModel):
    """Single localized/classified defect entry."""

    defect_id: str
    type: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    severity: Optional[str] = None
    bbox: Optional[list[int]] = None
    mask_reference: Optional[str] = None


class ModelUsageSchema(BaseModel):
    """Model version metadata recorded per inspection."""

    model_id: str
    version: str


class InspectionResultSchema(BaseModel):
    """Unified inspection result contract."""

    inspection_id: str
    manufacturer_id: str
    product_id: str
    status: str
    anomaly_score: Optional[float] = None
    quality_score: Optional[float] = None
    defects: list[DefectDetectionSchema] = Field(default_factory=list)
    models_used: list[ModelUsageSchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
