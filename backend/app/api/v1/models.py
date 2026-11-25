"""Model catalog and lifecycle endpoints — no business records created on GET."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.repositories.model_repository import ModelConfigRepository

router = APIRouter(prefix="/models", tags=["models"])

# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------

LIFECYCLE_STATES = {
    True: "Ready",
    False: "Disabled",
}


class ModelInfoOut(BaseModel):
    """Frontend-compatible model metadata with spec-correct lifecycle state."""

    id: str
    name: str
    task: str
    version: str
    state: str          # spec vocabulary: Draft / Configured / Ready / Disabled / etc.
    enabled: bool       # kept for backward compat
    model_family: str
    weights_path: str
    dataset_path: str
    has_weights_file: bool


def _to_model_info(m) -> ModelInfoOut:
    import os
    has_weights = bool(m.weights_file_path and os.path.isfile(m.weights_file_path))
    hyper = m.hyperparameters_json or {}
    state = LIFECYCLE_STATES.get(m.is_active, "Disabled")
    return ModelInfoOut(
        id=str(m.id),
        name=m.name,
        task=str(hyper.get("task", m.model_family)),
        version=m.version,
        state=state,
        enabled=m.is_active,
        model_family=m.model_family,
        weights_path=m.weights_file_path or "",
        dataset_path=m.dataset_dir_path or "",
        has_weights_file=has_weights,
    )


# ---------------------------------------------------------------------------
# Routes — GET never creates records
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ModelInfoOut])
def list_models(db: Session = Depends(get_db)) -> list[ModelInfoOut]:
    """List registered AI model configurations. Pure read — never creates records."""
    models = ModelConfigRepository(db).list_all(limit=200)
    return [_to_model_info(m) for m in models]


@router.get("/{model_id}", response_model=ModelInfoOut)
def get_model(model_id: int, db: Session = Depends(get_db)) -> ModelInfoOut:
    """Get a single model configuration by ID."""
    model = ModelConfigRepository(db).get_by_id(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return _to_model_info(model)


@router.patch("/{model_id}/toggle", response_model=ModelInfoOut)
def toggle_model(model_id: int, db: Session = Depends(get_db)) -> ModelInfoOut:
    """Enable or disable a registered model (toggle active state)."""
    repo = ModelConfigRepository(db)
    model = repo.get_by_id(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    updated = repo.update(model, is_active=not model.is_active)
    db.commit()
    return _to_model_info(updated)
