"""Shared Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: Literal["ok", "degraded"]
    app_name: str
    environment: str
    database_connected: bool
    timestamp: datetime


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: Optional[str] = None
