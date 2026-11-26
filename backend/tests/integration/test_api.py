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
        "/api/v1/settings/models",
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

        # Clean up test records so Test Model never leaks into AI Models UI
        mfg_repo.delete(mfg)
        db.commit()

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
    from backend.app.database.models.scanner import ModelToggleSetting
    catalogue = list_model_catalogue()
    assert any(c["model_key"] == "efficientad_small" for c in catalogue)

    db = SessionLocal()
    prev_toggle = db.get(ModelToggleSetting, "opencv_heuristic")
    prev_enabled = prev_toggle.is_enabled if prev_toggle else True
    if prev_toggle:
        prev_toggle.is_enabled = True
        db.commit()
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
        if prev_toggle:
            prev_toggle.is_enabled = prev_enabled
            db.commit()
        db.close()


def test_training_rejects_missing_or_empty_dataset():
    """Verify training fails with a clear 'Training issue' when dataset is missing or empty."""
    from fastapi import HTTPException
    from backend.app.api.v1.training import TrainingJobIn, start_training_job
    from backend.app.database.models.scanner import ModelToggleSetting
    db = SessionLocal()
    prev_toggle = db.get(ModelToggleSetting, "efficientad_small")
    prev_enabled = prev_toggle.is_enabled if prev_toggle else True
    if prev_toggle:
        prev_toggle.is_enabled = True
        db.commit()
    try:
        with pytest.raises(HTTPException) as exc:
            start_training_job(TrainingJobIn(model_key="efficientad_small", dataset_id=None), db=db)
        assert exc.value.status_code == 422
        assert "Training issue" in exc.value.detail
    finally:
        if prev_toggle:
            prev_toggle.is_enabled = prev_enabled
            db.commit()
        db.close()


def test_zip_validator_and_480p_resizing(tmp_path):
    """Verify strict flat-image ZIP validation and 640x480 (480p) standardization."""
    import zipfile
    import cv2
    import numpy as np
    from sqlalchemy import select
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


def test_settings_model_toggle_persists():
    """Verify global AI model toggle in Settings persists and restores original state."""
    from backend.app.api.v1.settings import list_model_toggles, toggle_model_setting
    db = SessionLocal()
    try:
        items = list_model_toggles()
        target = next((i for i in items if i.model_key == "patchcore"), None)
        assert target is not None
        before = target.is_enabled

        res1 = toggle_model_setting("patchcore", db=db)
        assert res1.is_enabled is (not before)

        # Toggle back to restore original state
        res2 = toggle_model_setting("patchcore", db=db)
        assert res2.is_enabled is before
    finally:
        db.close()


def test_multi_module_weighted_inspection():
    """Verify multi-module Scanner Unit runs all Ready modules, computes weighted averages, and keeps distinct outputs."""
    import json
    import cv2
    import numpy as np
    from backend.app.api.v1.inspections import run_inspection
    from backend.app.api.v1.scanner_units import (
        ModuleIn,
        ScannerUnitIn,
        add_module,
        create_scanner_unit,
        delete_scanner_unit,
    )
    from backend.app.database.models.scanner import ModelToggleSetting

    db = SessionLocal()
    prev_toggle = db.get(ModelToggleSetting, "opencv_heuristic")
    prev_enabled = prev_toggle.is_enabled if prev_toggle else True
    if prev_toggle:
        prev_toggle.is_enabled = True
        db.commit()

    unit_id = None
    try:
        unit = create_scanner_unit(
            ScannerUnitIn(name="Multi-Mod Test Unit", industry="Automotive", product_name="Rotor"),
            db=db,
        )
        unit_id = unit.id
        mod1 = add_module(
            unit_id,
            ModuleIn(
                name="Mod A",
                model_key="opencv_heuristic",
                selected_outputs=["anomaly_score", "bounding_boxes"],
                weight=80,
            ),
            db=db,
        )
        mod2 = add_module(
            unit_id,
            ModuleIn(
                name="Mod B",
                model_key="opencv_heuristic",
                selected_outputs=["anomaly_score"],
                weight=20,
            ),
            db=db,
        )
        assert mod1.weight == 80
        assert mod2.weight == 20

        img = np.zeros((120, 160, 3), dtype=np.uint8)
        _, png_bytes = cv2.imencode(".png", img)

        class _DummyUpload:
            async def read(self):
                return png_bytes.tobytes()

        coro = run_inspection(
            industry="Automotive",
            product="Rotor",
            pipelineId="Multi-Mod Test Unit",
            scannerUnitId=unit_id,
            threshold=0.5,
            fileName="test.png",
            moduleWeights=json.dumps({str(mod1.id): 60, str(mod2.id): 40}),
            file=_DummyUpload(),
            db=db,
        )
        try:
            coro.send(None)
            raise AssertionError("Expected run_inspection coroutine to complete synchronously")
        except StopIteration as stop:
            res = stop.value

        assert len(res.module_results) == 2
        ratios = {r.module_id: r.weight_ratio for r in res.module_results}
        assert abs(ratios[mod1.id] - 0.6) < 1e-3
        assert abs(ratios[mod2.id] - 0.4) < 1e-3
        assert len(res.weighted_outputs) == 2
        assert "unique_module_outputs" in res.distinct_outputs
        distinct_keys = [u["output_key"] for u in res.distinct_outputs["unique_module_outputs"]]
        assert "bounding_boxes" in distinct_keys
    finally:
        from sqlalchemy import select
        from backend.app.database.models.inspection import InspectionRecord
        from backend.app.database.models.pipeline import PipelineConfig
        if unit_id is not None:
            for r in db.scalars(select(InspectionRecord).where(InspectionRecord.scanner_unit_id == unit_id)).all():
                db.delete(r)
            for p in db.scalars(select(PipelineConfig).where(PipelineConfig.name == "Multi-Mod Test Unit")).all():
                db.delete(p)
            db.commit()
            delete_scanner_unit(unit_id, db=db)
        if prev_toggle:
            prev_toggle.is_enabled = prev_enabled
            db.commit()
        db.close()


def test_training_queue_and_cancel():
    """Verify training queue accepts jobs while lock is held and allows cancelling Queued jobs."""
    from fastapi import HTTPException
    from backend.app.api.v1 import training as tr_mod
    from backend.app.database.models.scanner import DatasetRecord, ModelToggleSetting, TrainingRun

    db = SessionLocal()
    prev_toggle = db.get(ModelToggleSetting, "efficientad_small")
    prev_enabled = prev_toggle.is_enabled if prev_toggle else True
    if prev_toggle:
        prev_toggle.is_enabled = True
        db.commit()

    ds = DatasetRecord(
        name="Queue Test DS",
        category="normal",
        industry="General",
        source_filename="q.zip",
        archive_path="data/datasets/nonexistent_q.zip",
        extracted_path="data/datasets/nonexistent_q",
        file_count=5,
        valid_image_count=5,
        invalid_file_count=0,
        duplicate_count=0,
        validation_status="Validated",
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    job_id = None
    acquired = tr_mod._train_lock.acquire(blocking=False)
    try:
        out = tr_mod.start_training_job(
            tr_mod.TrainingJobIn(model_key="efficientad_small", dataset_id=ds.id),
            db=db,
        )
        job_id = out.id
        assert out.status == "Queued"

        cancelled = tr_mod.cancel_training_job(job_id, db=db)
        assert cancelled.status == "Cancelled"

        with pytest.raises(HTTPException) as exc:
            tr_mod.cancel_training_job(job_id, db=db)
        assert exc.value.status_code == 422
    finally:
        if acquired:
            tr_mod._train_lock.release()
        with tr_mod._queue_lock:
            tr_mod._train_queue.clear()
        if job_id is not None:
            row = db.get(TrainingRun, job_id)
            if row:
                db.delete(row)
        db.delete(ds)
        if prev_toggle:
            prev_toggle.is_enabled = prev_enabled
        db.commit()
        db.close()


def test_anomalydino_catalogue_and_pipeline(tmp_path, monkeypatch):
    """Verify AnomalyDINO is in the catalogue and its PCA-masked cosine-NN + top-1% pipeline works end-to-end."""
    import cv2
    import numpy as np
    from backend.app.models.catalogue import get_model_capability
    from backend.app.models.anomalydino_adapter import AnomalyDINOAdapter

    cap = get_model_capability("anomalydino")
    assert cap is not None
    assert cap["display_name"] == "AnomalyDINO (DINOv2 Few-Shot)"
    assert cap["training_paradigm"] == "few_shot_patch_nn"

    # Deterministic synthetic 37x37x16 L2-normalized patch embeddings (object center vs background border)
    def fake_extract(bgr):
        patches = np.zeros((37, 37, 16), dtype=np.float32)
        patches[:, :, 0] = 1.0  # background direction
        patches[10:27, 10:27, 0] = 0.0
        patches[10:27, 10:27, 1] = 1.0  # foreground direction
        if int(bgr.mean()) > 100:
            # Anomalous bright patch in center
            patches[16:20, 16:20, 1] = 0.0
            patches[16:20, 16:20, 2] = 1.0
        return patches.reshape(-1, 16)

    monkeypatch.setattr(AnomalyDINOAdapter, "_extract_patches", staticmethod(fake_extract))

    ds_dir = tmp_path / "normal_ds"
    ds_dir.mkdir()
    normal_img = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.imwrite(str(ds_dir / "ok_1.png"), normal_img)

    bank_path = tmp_path / "anomalydino_bank.pt"
    metrics = AnomalyDINOAdapter.fit_dataset(ds_dir, bank_path)
    assert metrics["few_shot_augmented"] is True
    assert metrics["pca_masking_enabled"] is True
    assert bank_path.is_file()

    _, ok_bytes = cv2.imencode(".png", normal_img)
    ok_res = AnomalyDINOAdapter.predict_bytes(ok_bytes.tobytes(), bank_path, threshold=0.5)
    assert ok_res["anomaly_score"] == 0.0
    assert ok_res["defects"] == []

    anom_img = np.full((64, 64, 3), 200, dtype=np.uint8)
    _, anom_bytes = cv2.imencode(".png", anom_img)
    anom_res = AnomalyDINOAdapter.predict_bytes(anom_bytes.tobytes(), bank_path, threshold=0.5)
    assert anom_res["anomaly_score"] > ok_res["anomaly_score"]
    assert anom_res["model_name"] == "AnomalyDINO (DINOv2 Few-Shot)"


def test_inspection_requires_scanner_unit():
    """Verify scan is rejected with 422 when no Scanner Unit is selected."""
    from fastapi import HTTPException
    from backend.app.api.v1.inspections import run_inspection

    db = SessionLocal()
    try:
        coro = run_inspection(
            scannerUnitId=None,
            fileName="test.png",
            moduleWeights=None,
            file=None,
            db=db,
        )
        with pytest.raises(HTTPException) as exc:
            coro.send(None)
        assert exc.value.status_code == 422
        assert "Scanner Unit" in exc.value.detail
    finally:
        db.close()


def test_high_throughput_engine_lifecycle_recovery_and_security(tmp_path):
    """Stage 6 test: ZIP security, bulk ingestion, worker execution, corrupt handling, cancel, and restart recovery."""
    import io
    import zipfile
    import cv2
    import numpy as np
    from sqlalchemy import select
    from starlette.datastructures import UploadFile
    from backend.app.api.v1.engine_api import (
        _create_batch_and_jobs,
        cancel_batch,
        engine_metrics,
        engine_status,
        get_batch_results,
        get_batch_status,
    )
    from backend.app.api.v1.scanner_units import ModuleIn, ScannerUnitIn, add_module, create_scanner_unit, delete_scanner_unit
    from backend.app.database.models.engine_jobs import InspectionJob, JobBatch
    from backend.app.database.models.scanner import ModelToggleSetting
    from backend.app.engine.worker import InspectionEngineWorker

    db = SessionLocal()
    prev_toggle = db.get(ModelToggleSetting, "opencv_heuristic")
    prev_enabled = prev_toggle.is_enabled if prev_toggle else True
    if prev_toggle:
        prev_toggle.is_enabled = True
        db.commit()

    unit_id = None
    batch_uid = None
    try:
        unit = create_scanner_unit(
            ScannerUnitIn(name="Engine Test Unit", industry="Automotive", product_name="Gear"),
            db=db,
        )
        unit_id = unit.id
        add_module(
            unit_id,
            ModuleIn(name="Heuristic", model_key="opencv_heuristic", selected_outputs=["anomaly_score"]),
            db=db,
        )

        # Build a ZIP containing: 2 valid images, 1 corrupt image, 1 traversal entry, 1 unsupported txt
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        _, png_bytes = cv2.imencode(".png", img)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("ok_1.png", png_bytes.tobytes())
            zf.writestr("ok_2.png", png_bytes.tobytes())
            zf.writestr("corrupt.png", b"not-a-valid-png")
            zf.writestr("../escape.png", png_bytes.tobytes())
            zf.writestr("readme.txt", b"ignored")
        zip_buf.seek(0)

        import uuid
        idem_k = f"idem-test-{uuid.uuid4().hex[:8]}"
        up = UploadFile(filename="batch.zip", file=zip_buf)
        sub = _create_batch_and_jobs(
            db,
            scanner_unit_id=unit_id,
            source_type="MASS_TEST",
            files=[up],
            threshold=0.5,
            priority=5,
            idempotency_key=idem_k,
            metadata_str=None,
        )
        batch_uid = sub.batch_id
        assert sub.total_items == 3  # ok_1, ok_2, corrupt
        assert len(sub.rejected_files) == 2  # traversal + txt

        # Idempotency check returns same batch without duplicating jobs
        sub2 = _create_batch_and_jobs(
            db,
            scanner_unit_id=unit_id,
            source_type="MASS_TEST",
            files=[],
            threshold=0.5,
            priority=5,
            idempotency_key=idem_k,
            metadata_str=None,
        )
        assert sub2.batch_id == batch_uid

        # Process 1st job synchronously via worker (or live background worker)
        InspectionEngineWorker.process_next_job()
        db.expire_all()
        st = get_batch_status(batch_uid, db=db)
        assert st["completed_items"] + st["failed_items"] + st["processing_items"] >= 1

        # Simulate interrupted job + restart recovery on a fresh queued job if one remains
        batch_row = db.scalar(select(JobBatch).where(JobBatch.batch_uid == batch_uid))
        next_job = db.scalar(
            select(InspectionJob).where(InspectionJob.batch_id == batch_row.id, InspectionJob.status == "QUEUED")
        )
        if next_job is not None:
            next_job.status = "PROCESSING"
            db.commit()
            recovered = InspectionEngineWorker.recover_interrupted_jobs()
            assert recovered >= 1
            db.expire_all()
            assert db.get(InspectionJob, next_job.id).status in ("QUEUED", "COMPLETED", "PROCESSING")

        # Process remaining jobs (ok_2 + corrupt) and wait briefly if a live server worker is finishing one
        import time
        for _ in range(30):
            while InspectionEngineWorker.process_next_job():
                pass
            db.expire_all()
            st_final = get_batch_status(batch_uid, db=db)
            if st_final["completed_items"] + st_final["failed_items"] >= 3:
                break
            time.sleep(0.2)

        assert st_final["completed_items"] == 2
        assert st_final["failed_items"] == 1  # corrupt.png failed cleanly, not false PASS

        res_page = get_batch_results(
            batch_uid,
            limit=50,
            offset=0,
            job_status=None,
            decision=None,
            severity=None,
            db=db,
        )
        assert res_page["total"] == 3
        completed_item = next(i for i in res_page["items"] if i["inspection_id"])
        from backend.app.api.v1.inspections import get_inspection
        detail = get_inspection(completed_item["inspection_id"], db=db)
        assert detail.image_url is not None
        assert detail.image_url.startswith("/uploads/batches/")

        # Cancel test on a fresh batch
        zip_buf.seek(0)
        up2 = UploadFile(filename="batch2.zip", file=zip_buf)
        sub_cancel = _create_batch_and_jobs(
            db,
            scanner_unit_id=unit_id,
            source_type="API",
            files=[up2],
            threshold=0.5,
            priority=5,
            idempotency_key=None,
            metadata_str=None,
        )
        cancelled = cancel_batch(sub_cancel.batch_id, db=db)
        assert cancelled["cancelled_items"] == 3
        assert cancelled["status"] == "CANCELLED"

        # Monitoring endpoints
        es = engine_status()
        em = engine_metrics()
        assert "queue_depth" in es
        assert em["completed_jobs"] >= 2
    finally:
        from sqlalchemy import select
        from backend.app.database.models.inspection import InspectionRecord
        from backend.app.database.models.pipeline import PipelineConfig
        if unit_id is not None:
            for r in db.scalars(select(InspectionRecord).where(InspectionRecord.scanner_unit_id == unit_id)).all():
                db.delete(r)
            for p in db.scalars(select(PipelineConfig).where(PipelineConfig.name == "Multi-Mod Test Unit")).all():
                db.delete(p)
            db.commit()
            delete_scanner_unit(unit_id, db=db)
        if prev_toggle:
            prev_toggle.is_enabled = prev_enabled
            db.commit()
        db.close()


def test_training_queue_and_cancel():
    """Verify training queue accepts jobs while lock is held and allows cancelling Queued jobs."""
    from fastapi import HTTPException
    from backend.app.api.v1 import training as tr_mod
    from backend.app.database.models.scanner import DatasetRecord, ModelToggleSetting, TrainingRun

    db = SessionLocal()
    prev_toggle = db.get(ModelToggleSetting, "efficientad_small")
    prev_enabled = prev_toggle.is_enabled if prev_toggle else True
    if prev_toggle:
        prev_toggle.is_enabled = True
        db.commit()

    ds = DatasetRecord(
        name="Queue Test DS",
        category="normal",
        industry="General",
        source_filename="q.zip",
        archive_path="data/datasets/nonexistent_q.zip",
        extracted_path="data/datasets/nonexistent_q",
        file_count=5,
        valid_image_count=5,
        invalid_file_count=0,
        duplicate_count=0,
        validation_status="Validated",
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    job_id = None
    acquired = tr_mod._train_lock.acquire(blocking=False)
    try:
        out = tr_mod.start_training_job(
            tr_mod.TrainingJobIn(model_key="efficientad_small", dataset_id=ds.id),
            db=db,
        )
        job_id = out.id
        assert out.status == "Queued"

        cancelled = tr_mod.cancel_training_job(job_id, db=db)
        assert cancelled.status == "Cancelled"

        with pytest.raises(HTTPException) as exc:
            tr_mod.cancel_training_job(job_id, db=db)
        assert exc.value.status_code == 422
    finally:
        if acquired:
            tr_mod._train_lock.release()
        with tr_mod._queue_lock:
            tr_mod._train_queue.clear()
        if job_id is not None:
            row = db.get(TrainingRun, job_id)
            if row:
                db.delete(row)
        db.delete(ds)
        if prev_toggle:
            prev_toggle.is_enabled = prev_enabled
        db.commit()
        db.close()
