"""Pipeline configuration endpoints — list, get, create, toggle."""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.repositories.pipeline_repository import PipelineConfigRepository
from backend.app.database.repositories.model_repository import ManufacturerRepository

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class StageIn(BaseModel):
    id: str
    type: str
    model_id: Optional[str] = None
    params: Optional[dict[str, Any]] = None


class PipelineCreateIn(BaseModel):
    name: str
    description: Optional[str] = None
    manufacturer_name: str = "Default Manufacturer"
    industry: str = "Manufacturing"
    stages: list[StageIn] = []
    thresholds: Optional[dict[str, Any]] = None


class PipelineOut(BaseModel):
    id: str
    name: str
    version: str
    description: Optional[str]
    manufacturer: str
    is_active: bool
    state: str
    stages: list[dict]
    thresholds: Optional[dict]
    created_at: str


def _to_out(p, mfg_name: str) -> PipelineOut:
    state = "Ready" if p.is_active else "Disabled"
    return PipelineOut(
        id=str(p.id),
        name=p.name,
        version=p.version,
        description=p.description,
        manufacturer=mfg_name,
        is_active=p.is_active,
        state=state,
        stages=list(p.modules_json) if p.modules_json else [],
        thresholds=p.thresholds_json,
        created_at=p.created_at.isoformat(),
    )


@router.get("", response_model=list[PipelineOut])
def list_pipelines(db: Session = Depends(get_db)) -> list[PipelineOut]:
    """List all pipeline configurations. Pure read."""
    pipes = PipelineConfigRepository(db).list_all(limit=200)
    result = []
    for p in pipes:
        mfg = ManufacturerRepository(db).get_by_id(p.manufacturer_id)
        result.append(_to_out(p, mfg.name if mfg else "Unknown"))
    return result


@router.get("/{pipeline_id}", response_model=PipelineOut)
def get_pipeline(pipeline_id: int, db: Session = Depends(get_db)) -> PipelineOut:
    p = PipelineConfigRepository(db).get_by_id(pipeline_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    mfg = ManufacturerRepository(db).get_by_id(p.manufacturer_id)
    return _to_out(p, mfg.name if mfg else "Unknown")


@router.post("", response_model=PipelineOut, status_code=201)
def create_pipeline(body: PipelineCreateIn, db: Session = Depends(get_db)) -> PipelineOut:
    """Create a new pipeline configuration."""
    mfg_repo = ManufacturerRepository(db)
    mfg = mfg_repo.get_by_name(body.manufacturer_name)
    if mfg is None:
        mfg = mfg_repo.create(name=body.manufacturer_name, industry=body.industry)
    stages = [s.model_dump() for s in body.stages]
    p = PipelineConfigRepository(db).create(
        manufacturer_id=mfg.id,
        name=body.name,
        description=body.description,
        modules_json=stages,
        thresholds_json=body.thresholds,
    )
    db.commit()
    return _to_out(p, mfg.name)


@router.patch("/{pipeline_id}/toggle", response_model=PipelineOut)
def toggle_pipeline(pipeline_id: int, db: Session = Depends(get_db)) -> PipelineOut:
    repo = PipelineConfigRepository(db)
    p = repo.get_by_id(pipeline_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    updated = repo.update(p, is_active=not p.is_active)
    db.commit()
    mfg = ManufacturerRepository(db).get_by_id(updated.manufacturer_id)
    return _to_out(updated, mfg.name if mfg else "Unknown")
