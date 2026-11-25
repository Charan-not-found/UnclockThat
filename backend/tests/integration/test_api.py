"""Integration tests covering core backend routes and DB operations."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.database.connection import SessionLocal, init_db
from backend.app.database.repositories.inspection_repository import InspectionRepository
from backend.app.database.repositories.model_repository import ManufacturerRepository, ModelConfigRepository
from backend.app.database.repositories.pipeline_repository import PipelineConfigRepository
from backend.app.api.v1.health import health_check


@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    init_db()
    yield


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def test_fastapi_app_routes_registered():
    """Verify all API route prefixes are present in the OpenAPI schema."""
    from backend.app.main import app
    paths = set(app.openapi()["paths"].keys())
    expected = [
        "/api/v1/health",
        "/api/v1/scanner-units",
        "/api/v1/model-catalogue",
        "/api/v1/datasets",
        "/api/v1/training-jobs",
        "/api/v1/inspections",
        "/api/v1/inspections/corrections",
        "/api/v1/models",
        "/api/v1/analytics/summary",
        "/api/v1/admin/seed",
    ]
    for path in expected:
        assert path in paths, f"Missing route: {path}"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check_handler():
    db = SessionLocal()
    try:
        result = health_check(db=db)
        assert result.status == "ok"
        assert result.database_connected is True
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Database CRUD and cascade
# ---------------------------------------------------------------------------

def test_database_tables_and_repository_crud():
    db = SessionLocal()
    try:
        # Verify all tables exist
        expected_tables = {
            "manufacturer_profiles", "users", "model_configs",
            "pipeline_configs", "inspection_records", "anomaly_results", "severity_scores",
        }
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        actual = {row[0] for row in result}
        assert expected_tables.issubset(actual), f"Missing tables: {expected_tables - actual}"

        # Create manufacturer with unique name to avoid conflicts across test runs
        import time
        unique_name = f"Test Manufacturer {int(time.time() * 1000)}"
        mfg_repo = ManufacturerRepository(db)
        mfg = mfg_repo.create(name=unique_name, industry="Testing")
        db.commit()
        assert mfg.id is not None

        # Create model config
        model_repo = ModelConfigRepository(db)
        mc = model_repo.create(
            manufacturer_id=mfg.id,
            name="Test Model",
            model_family="test",
            version="1.0.0",
            dataset_dir_path="data/test",
            weights_file_path="artifacts/test.pt",
            is_active=True,
        )
        db.commit()
        assert mc.id is not None
        assert mc.is_active is True

        # Toggle model
        updated = model_repo.update(mc, is_active=False)
        db.commit()
        assert updated.is_active is False

        # Create pipeline
        pipe_repo = PipelineConfigRepository(db)
        pipe = pipe_repo.create(
            manufacturer_id=mfg.id,
            name="Test Pipeline",
            modules_json=[{"id": "stage_1", "type": "test"}],
        )
        db.commit()
        assert pipe.id is not None

        # Create inspection
        from datetime import datetime, timezone
        insp_repo = InspectionRepository(db)
        insp = insp_repo.create(
            manufacturer_id=mfg.id,
            pipeline_config_id=pipe.id,
            product_serial="PART-TEST-001",
            station_name="Test Station",
            image_file_path="/tmp/test.png",
            status="completed",
            overall_decision="PASS",
            quality_score=0.95,
            inspected_at=datetime.now(timezone.utc),
        )
        db.commit()
        assert insp.id is not None

        # Verify cascade
        insp_detail = insp_repo.get_with_results(insp.id)
        assert insp_detail is not None
        assert insp_detail.product_serial == "PART-TEST-001"

    finally:
        db.close()


def test_analytics_routes_respond():
    """Test analytics endpoints return valid responses via direct function call."""
    from backend.app.api.v1.analytics import get_summary
    db = SessionLocal()
    try:
        result = get_summary(days=7, db=db)
        assert hasattr(result, "total_inspections")
        assert hasattr(result, "note")
        assert result.date_range_days == 7
    finally:
        db.close()


def test_pipelines_list_read_only():
    """GET /pipelines (direct call) must never create records."""
    from backend.app.api.v1.pipelines import list_pipelines
    db = SessionLocal()
    before = len(list(PipelineConfigRepository(db).list_all(limit=1000)))
    db.close()

    db = SessionLocal()
    try:
        list_pipelines(db=db)
        db.close()
    except Exception:
        db.close()

    db = SessionLocal()
    after = len(list(PipelineConfigRepository(db).list_all(limit=1000)))
    db.close()
    assert after == before, "GET /pipelines must not create records"


def test_models_list_read_only():
    """GET /models (direct call) must never create records."""
    from backend.app.api.v1.models import list_models
    db = SessionLocal()
    before = len(list(ModelConfigRepository(db).list_all(limit=1000)))
    db.close()

    db = SessionLocal()
    try:
        list_models(db=db)
        db.close()
    except Exception:
        db.close()

    db = SessionLocal()
    after = len(list(ModelConfigRepository(db).list_all(limit=1000)))
    db.close()
    assert after == before, "GET /models must not create records (spec violation fixed)"


def test_scanner_unit_and_module_crud():
    """Verify Scanner Unit + Analysis Module creation, capability validation, and cleanup."""
    from backend.app.api.v1.scanner_units import (
        ModuleIn,
        ScannerUnitIn,
        add_module,
        create_scanner_unit,
        delete_scanner_unit,
        list_model_catalogue,
    )
    catalogue = list_model_catalogue()
    assert any(c["model_key"] == "efficientad_small" for c in catalogue)

    db = SessionLocal()
    try:
        unit = create_scanner_unit(
            ScannerUnitIn(name="Test Casting Scanner", industry="Automotive", product_name="Brake disc"),
            db=db,
        )
        assert unit.id is not None
        assert unit.status == "Draft"

        mod = add_module(
            unit.id,
            ModuleIn(
                name="Surface Anomaly",
                model_key="opencv_heuristic",
                selected_outputs=["anomaly_score", "bounding_boxes"],
            ),
            db=db,
        )
        assert mod.state == "Ready"

        res = delete_scanner_unit(unit.id, db=db)
        assert res["status"] == "deleted"
    finally:
        db.close()


def test_training_rejects_missing_or_empty_dataset():
    """Verify training fails with a clear 'Training issue' when dataset is missing or empty."""
    from fastapi import HTTPException
    from backend.app.api.v1.training import TrainingJobIn, start_training_job
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc:
            start_training_job(TrainingJobIn(model_key="efficientad_small", dataset_id=None), db=db)
        assert exc.value.status_code == 422
        assert "Training issue" in exc.value.detail
    finally:
        db.close()


def test_zip_validator_and_480p_resizing(tmp_path):
    """Verify strict flat-image ZIP validation and 640x480 (480p) standardization."""
    import zipfile
    import cv2
    import numpy as np
    from fastapi import HTTPException
    from backend.app.api.v1.datasets import _validate_and_extract_zip

    # 1. Empty ZIP -> rejected
    empty_zip = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty_zip, "w"):
        pass
    out_dir = tmp_path / "out_empty"
    out_dir.mkdir()
    with pytest.raises(HTTPException) as exc:
        _validate_and_extract_zip(empty_zip, out_dir)
    assert exc.value.status_code == 422
    assert "empty" in exc.value.detail.lower()

    # 2. Subfolder in ZIP -> rejected
    sub_zip = tmp_path / "sub.zip"
    img = np.zeros((100, 120, 3), dtype=np.uint8)
    _, png_bytes = cv2.imencode(".png", img)
    with zipfile.ZipFile(sub_zip, "w") as zf:
        zf.writestr("nested/1.png", png_bytes.tobytes())
    out_sub = tmp_path / "out_sub"
    out_sub.mkdir()
    with pytest.raises(HTTPException) as exc:
        _validate_and_extract_zip(sub_zip, out_sub)
    assert exc.value.status_code == 422
    assert "subfolder" in exc.value.detail.lower()

    # 3. Non-image file in ZIP -> rejected
    txt_zip = tmp_path / "txt.zip"
    with zipfile.ZipFile(txt_zip, "w") as zf:
        zf.writestr("1.png", png_bytes.tobytes())
        zf.writestr("notes.txt", b"not an image")
    out_txt = tmp_path / "out_txt"
    out_txt.mkdir()
    with pytest.raises(HTTPException) as exc:
        _validate_and_extract_zip(txt_zip, out_txt)
    assert exc.value.status_code == 422
    assert "non-image" in exc.value.detail.lower()

    # 4. Valid flat image-only ZIP -> accepted & standardized to 640x480 (480p)
    good_zip = tmp_path / "good.zip"
    with zipfile.ZipFile(good_zip, "w") as zf:
        zf.writestr("1.png", png_bytes.tobytes())
        zf.writestr("2.png", png_bytes.tobytes())
    out_good = tmp_path / "out_good"
    out_good.mkdir()
    res = _validate_and_extract_zip(good_zip, out_good)
    assert res["valid_image_count"] == 2
    assert res["duplicate_count"] == 1
    assert res["resolution"] == "640x480 (480p)"
    saved = cv2.imread(str(out_good / "1.jpg"))
    assert saved is not None
    assert saved.shape[:2] == (480, 640)
