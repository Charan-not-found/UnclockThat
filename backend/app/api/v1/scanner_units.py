"""Scanner Unit and Analysis Module management endpoints + Model Catalogue."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import BASE_DIR
from backend.app.database.connection import get_db
from backend.app.database.models.model_config import ModelConfig
from backend.app.database.models.scanner import AnalysisModule, DatasetRecord, ScannerUnit
from backend.app.database.repositories.model_repository import ManufacturerRepository
from backend.app.models.catalogue import get_model_capability, get_model_catalogue

router = APIRouter(tags=["scanner-units"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ModuleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    purpose: Optional[str] = None
    model_key: str
    dataset_id: Optional[int] = None
    selected_outputs: list[str] = Field(default_factory=list)
    weight: int = Field(default=100, ge=1, le=100)
    config: Optional[dict[str, Any]] = None


class ModuleOut(BaseModel):
    id: int
    scanner_unit_id: int
    name: str
    description: Optional[str]
    purpose: Optional[str]
    model_key: str
    model_display_name: str
    dataset_id: Optional[int]
    dataset_name: Optional[str]
    dataset_validation_status: Optional[str]
    selected_outputs: list[str]
    weight: int
    config: Optional[dict[str, Any]]
    state: str
    created_at: str
    updated_at: str


class ScannerUnitIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    industry: str = "Manufacturing"
    product_name: Optional[str] = None


class ScannerUnitPatchIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    product_name: Optional[str] = None


class ScannerUnitOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    industry: str
    product_name: Optional[str]
    status: str
    module_count: int
    modules: list[ModuleOut]
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_module_state(
    cap: dict[str, Any],
    dataset: Optional[DatasetRecord],
) -> str:
    if cap["integration_state"] != "available_integrated":
        return "Draft"
    if not cap["requires_dataset"]:
        return "Ready" if cap["ready_for_inference"] else "Draft"
    if cap["ready_for_inference"] and dataset is None:
        # Pre-trained checkpoint already exists (e.g. EfficientAD-Small)
        return "Ready"
    if dataset is None:
        return "Needs dataset"
    if dataset.validation_status != "Validated":
        return "Needs dataset"
    return "Ready" if cap["ready_for_inference"] else "Draft"


def _compute_unit_status(modules: list[AnalysisModule]) -> str:
    if not modules:
        return "Draft"
    if any(m.state == "Failed" for m in modules):
        return "Failed"
    if any(m.state == "Training" for m in modules):
        return "Training"
    if all(m.state == "Ready" for m in modules):
        return "Ready"
    return "Draft"


def _module_to_out(db: Session, m: AnalysisModule) -> ModuleOut:
    cap = get_model_capability(m.model_key)
    ds = db.get(DatasetRecord, m.dataset_id) if m.dataset_id else None
    return ModuleOut(
        id=m.id,
        scanner_unit_id=m.scanner_unit_id,
        name=m.name,
        description=m.description,
        purpose=m.purpose,
        model_key=m.model_key,
        model_display_name=cap["display_name"] if cap else m.model_key,
        dataset_id=m.dataset_id,
        dataset_name=ds.name if ds else None,
        dataset_validation_status=ds.validation_status if ds else None,
        selected_outputs=list(m.selected_outputs_json or []),
        weight=int((m.config_json or {}).get("weight", 100)),
        config=m.config_json,
        state=m.state,
        created_at=m.created_at.isoformat(),
        updated_at=m.updated_at.isoformat(),
    )


def _unit_to_out(db: Session, u: ScannerUnit) -> ScannerUnitOut:
    mods = [_module_to_out(db, m) for m in u.modules]
    return ScannerUnitOut(
        id=u.id,
        name=u.name,
        description=u.description,
        industry=u.industry,
        product_name=u.product_name,
        status=u.status,
        module_count=len(mods),
        modules=mods,
        created_at=u.created_at.isoformat(),
        updated_at=u.updated_at.isoformat(),
    )


def _validate_module_payload(body: ModuleIn, db: Session) -> tuple[dict[str, Any], Optional[DatasetRecord], list[str]]:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Module name cannot be blank")

    cap = get_model_capability(body.model_key)
    if cap is None:
        raise HTTPException(status_code=422, detail=f"Unknown model_key: {body.model_key}")
    if cap["integration_state"] != "available_integrated":
        raise HTTPException(
            status_code=422,
            detail=f"Model '{cap['display_name']}' is not integrated for execution yet.",
        )

    allowed_outputs = {o["key"] for o in cap["supported_outputs"]}
    invalid_outputs = [o for o in body.selected_outputs if o not in allowed_outputs]
    if invalid_outputs:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported outputs for {cap['display_name']}: {invalid_outputs}",
        )
    if not body.selected_outputs:
        raise HTTPException(status_code=422, detail="Select at least one supported output.")

    ds: Optional[DatasetRecord] = None
    if body.dataset_id is not None:
        ds = db.get(DatasetRecord, body.dataset_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="Selected dataset not found")

    return cap, ds, body.selected_outputs


# ---------------------------------------------------------------------------
# Model capability catalogue
# ---------------------------------------------------------------------------

@router.get("/model-catalogue")
def list_model_catalogue() -> list[dict[str, Any]]:
    """Return capability manifests for all models with live artifact availability."""
    return get_model_catalogue()


# ---------------------------------------------------------------------------
# Scanner Units CRUD
# ---------------------------------------------------------------------------

@router.get("/scanner-units", response_model=list[ScannerUnitOut])
def list_scanner_units(db: Session = Depends(get_db)) -> list[ScannerUnitOut]:
    stmt = (
        select(ScannerUnit)
        .options(selectinload(ScannerUnit.modules))
        .order_by(ScannerUnit.updated_at.desc())
    )
    units = db.scalars(stmt).all()
    return [_unit_to_out(db, u) for u in units]


@router.post("/scanner-units", response_model=ScannerUnitOut, status_code=201)
def create_scanner_unit(body: ScannerUnitIn, db: Session = Depends(get_db)) -> ScannerUnitOut:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Scanner Unit name cannot be blank")

    unit = ScannerUnit(
        name=name,
        description=body.description.strip() if body.description else None,
        industry=body.industry.strip() or "Manufacturing",
        product_name=body.product_name.strip() if body.product_name else None,
        status="Draft",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return _unit_to_out(db, unit)


@router.get("/scanner-units/{unit_id}", response_model=ScannerUnitOut)
def get_scanner_unit(unit_id: int, db: Session = Depends(get_db)) -> ScannerUnitOut:
    stmt = (
        select(ScannerUnit)
        .options(selectinload(ScannerUnit.modules))
        .where(ScannerUnit.id == unit_id)
    )
    unit = db.scalar(stmt)
    if unit is None:
        raise HTTPException(status_code=404, detail="Scanner Unit not found")
    return _unit_to_out(db, unit)


@router.patch("/scanner-units/{unit_id}", response_model=ScannerUnitOut)
def update_scanner_unit(
    unit_id: int, body: ScannerUnitPatchIn, db: Session = Depends(get_db)
) -> ScannerUnitOut:
    stmt = (
        select(ScannerUnit)
        .options(selectinload(ScannerUnit.modules))
        .where(ScannerUnit.id == unit_id)
    )
    unit = db.scalar(stmt)
    if unit is None:
        raise HTTPException(status_code=404, detail="Scanner Unit not found")

    if body.name is not None:
        cleaned = body.name.strip()
        if not cleaned:
            raise HTTPException(status_code=422, detail="Scanner Unit name cannot be blank")
        unit.name = cleaned
    if body.description is not None:
        unit.description = body.description.strip() or None
    if body.industry is not None:
        unit.industry = body.industry.strip() or unit.industry
    if body.product_name is not None:
        unit.product_name = body.product_name.strip() or None

    db.commit()
    db.refresh(unit)
    return _unit_to_out(db, unit)


@router.delete("/scanner-units/{unit_id}")
def delete_scanner_unit(unit_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    unit = db.get(ScannerUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Scanner Unit not found")
    db.delete(unit)
    db.commit()
    return {"status": "deleted", "id": str(unit_id)}


# ---------------------------------------------------------------------------
# Analysis Modules CRUD (within a Scanner Unit)
# ---------------------------------------------------------------------------

@router.post("/scanner-units/{unit_id}/modules", response_model=ModuleOut, status_code=201)
def add_module(unit_id: int, body: ModuleIn, db: Session = Depends(get_db)) -> ModuleOut:
    stmt = (
        select(ScannerUnit)
        .options(selectinload(ScannerUnit.modules))
        .where(ScannerUnit.id == unit_id)
    )
    unit = db.scalar(stmt)
    if unit is None:
        raise HTTPException(status_code=404, detail="Scanner Unit not found")

    cap, ds, outputs = _validate_module_payload(body, db)
    state = _compute_module_state(cap, ds)

    mod = AnalysisModule(
        scanner_unit_id=unit.id,
        name=body.name.strip(),
        description=body.description.strip() if body.description else None,
        purpose=body.purpose.strip() if body.purpose else None,
        model_key=body.model_key,
        dataset_id=body.dataset_id,
        selected_outputs_json=outputs,
        config_json=dict(body.config or {}),
        state=state,
    )
    db.add(mod)
    db.flush()

    # Clone a dedicated ModelConfig for this module so training & weights stay isolated
    mfg_repo = ManufacturerRepository(db)
    mfg = mfg_repo.get_by_name(unit.industry) or mfg_repo.get_by_name("Default Manufacturer")
    if mfg is None:
        mfg = mfg_repo.create(name=unit.industry or "Default Manufacturer", industry=unit.industry or "General")

    trained_dir = BASE_DIR / "models" / "custom"
    trained_dir.mkdir(parents=True, exist_ok=True)
    ext = ".pt" if body.model_key in ("yolo11n_seg", "yolo11m_seg", "omniposead", "anomalydino") else ".ckpt"
    cloned_rel = f"models/custom/module_{mod.id}_{body.model_key}{ext}"
    cloned_abs = BASE_DIR / cloned_rel

    src_weights = cap.get("trained_checkpoint_path") or cap.get("pretrained_path")
    if src_weights and (BASE_DIR / src_weights).is_file() and body.model_key in ("yolo11n_seg", "yolo11m_seg"):
        shutil.copy2(BASE_DIR / src_weights, cloned_abs)

    mc = ModelConfig(
        manufacturer_id=mfg.id,
        name=f"{unit.name} — {mod.name}",
        model_family=cap["model_family"],
        version="1.0.0",
        dataset_dir_path=ds.extracted_path if ds else "",
        weights_file_path=cloned_rel if body.model_key != "opencv_heuristic" else "",
        hyperparameters_json={"task": cap["task"], "model_key": body.model_key, "module_id": mod.id},
        metrics_json={},
        is_active=(state == "Ready"),
    )
    db.add(mc)
    db.flush()

    cfg = dict(mod.config_json or {})
    cfg["weight"] = body.weight
    cfg["cloned_model_config_id"] = mc.id
    cfg["cloned_weights_path"] = cloned_rel if body.model_key != "opencv_heuristic" else None
    mod.config_json = cfg

    db.refresh(unit)
    unit.status = _compute_unit_status(unit.modules)
    db.commit()
    db.refresh(mod)
    return _module_to_out(db, mod)


@router.patch("/scanner-units/{unit_id}/modules/{module_id}", response_model=ModuleOut)
def update_module(
    unit_id: int, module_id: int, body: ModuleIn, db: Session = Depends(get_db)
) -> ModuleOut:
    mod = db.get(AnalysisModule, module_id)
    if mod is None or mod.scanner_unit_id != unit_id:
        raise HTTPException(status_code=404, detail="Analysis Module not found")

    cap, ds, outputs = _validate_module_payload(body, db)
    mod.name = body.name.strip()
    mod.description = body.description.strip() if body.description else None
    mod.purpose = body.purpose.strip() if body.purpose else None
    mod.model_key = body.model_key
    mod.dataset_id = body.dataset_id
    mod.selected_outputs_json = outputs
    existing_cfg = dict(mod.config_json or {})
    if body.config:
        existing_cfg.update(body.config)
    existing_cfg["weight"] = body.weight
    mod.config_json = existing_cfg
    mod.state = _compute_module_state(cap, ds)

    stmt = (
        select(ScannerUnit)
        .options(selectinload(ScannerUnit.modules))
        .where(ScannerUnit.id == unit_id)
    )
    unit = db.scalar(stmt)
    if unit:
        unit.status = _compute_unit_status(unit.modules)

    db.commit()
    db.refresh(mod)
    return _module_to_out(db, mod)


@router.delete("/scanner-units/{unit_id}/modules/{module_id}")
def delete_module(unit_id: int, module_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    mod = db.get(AnalysisModule, module_id)
    if mod is None or mod.scanner_unit_id != unit_id:
        raise HTTPException(status_code=404, detail="Analysis Module not found")

    cfg = mod.config_json or {}
    mc_id = cfg.get("cloned_model_config_id")
    if mc_id:
        mc = db.get(ModelConfig, mc_id)
        if mc:
            db.delete(mc)
    cloned_w = cfg.get("cloned_weights_path")
    if cloned_w:
        (BASE_DIR / cloned_w).unlink(missing_ok=True)

    db.delete(mod)
    db.flush()

    stmt = (
        select(ScannerUnit)
        .options(selectinload(ScannerUnit.modules))
        .where(ScannerUnit.id == unit_id)
    )
    unit = db.scalar(stmt)
    if unit:
        unit.status = _compute_unit_status(unit.modules)

    db.commit()
    return {"status": "deleted", "id": str(module_id)}
