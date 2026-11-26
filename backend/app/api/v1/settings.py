"""Application settings endpoints — global AI model enable/disable toggles."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.models.scanner import ModelToggleSetting
from backend.app.models.catalogue import get_model_capability, get_model_catalogue

router = APIRouter(prefix="/settings", tags=["settings"])


class ModelToggleOut(BaseModel):
    model_key: str
    display_name: str
    model_family: str
    task: str
    is_enabled: bool
    ready_for_inference: bool


@router.get("/models", response_model=list[ModelToggleOut])
def list_model_toggles() -> list[ModelToggleOut]:
    """List all AI models with their current global enable/disable toggle state."""
    return [
        ModelToggleOut(
            model_key=m["model_key"],
            display_name=m["display_name"],
            model_family=m["model_family"],
            task=m["task"],
            is_enabled=bool(m.get("is_enabled", True)),
            ready_for_inference=bool(m.get("ready_for_inference", False)),
        )
        for m in get_model_catalogue()
    ]


@router.patch("/models/{model_key}/toggle", response_model=ModelToggleOut)
def toggle_model_setting(model_key: str, db: Session = Depends(get_db)) -> ModelToggleOut:
    """Enable or disable an AI model globally across the application."""
    cap = get_model_capability(model_key)
    if cap is None:
        raise HTTPException(status_code=404, detail=f"Unknown model_key: {model_key}")

    row = db.get(ModelToggleSetting, model_key)
    if row is None:
        row = ModelToggleSetting(model_key=model_key, is_enabled=False)
        db.add(row)
    else:
        row.is_enabled = not row.is_enabled

    db.commit()
    db.refresh(row)

    return ModelToggleOut(
        model_key=cap["model_key"],
        display_name=cap["display_name"],
        model_family=cap["model_family"],
        task=cap["task"],
        is_enabled=row.is_enabled,
        ready_for_inference=bool(cap.get("ready_for_inference", False)),
    )
