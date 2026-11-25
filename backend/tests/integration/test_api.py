"""Integration tests for health endpoint handler and database repositories."""

from __future__ import annotations

from sqlalchemy import inspect

from backend.app.api.v1.health import health_check
from backend.app.database import (
    AnomalyResultRepository,
    InspectionRepository,
    ManufacturerRepository,
    ModelConfigRepository,
    PipelineConfigRepository,
    SessionLocal,
    SeverityScoreRepository,
    UserRepository,
    engine,
    session_scope,
)
from backend.app.main import app


def test_fastapi_app_routes_registered() -> None:
    paths = set(app.openapi()["paths"].keys())
    assert "/api/v1/health" in paths


def test_health_check_handler() -> None:
    db = SessionLocal()
    try:
        payload = health_check(db=db)
    finally:
        db.close()

    assert payload.status == "ok"
    assert payload.app_name == "CLOCKIT"
    assert payload.database_connected is True


def test_database_tables_and_repository_crud() -> None:
    tables = set(inspect(engine).get_table_names())
    expected = {
        "manufacturer_profiles",
        "users",
        "model_configs",
        "pipeline_configs",
        "inspection_records",
        "anomaly_results",
        "severity_scores",
    }
    assert expected.issubset(tables)

    with session_scope() as session:
        m = ManufacturerRepository(session).create(name="Test Mfg", industry="PCB")
        u = UserRepository(session).create(
            manufacturer_id=m.id,
            username="tester1",
            email="tester1@example.com",
            hashed_password="hash",
        )
        mc = ModelConfigRepository(session).create(
            manufacturer_id=m.id,
            name="EfficientAD-v1",
            model_family="efficientad",
            dataset_dir_path="data/raw/pcb",
            weights_file_path="artifacts/trained/efficientad/1.0.0/weights.pt",
        )
        pc = PipelineConfigRepository(session).create(
            manufacturer_id=m.id,
            name="Default-PCB",
            modules_json=[{"id": "anomaly_detection", "model_id": "efficientad"}],
        )
        ir = InspectionRepository(session).create(
            manufacturer_id=m.id,
            user_id=u.id,
            pipeline_config_id=pc.id,
            product_serial="SN-TEST-01",
            image_file_path="storage/uploads/sn_test_01.png",
            status="completed",
            overall_decision="REVIEW_REQUIRED",
            quality_score=0.72,
        )
        ar = AnomalyResultRepository(session).create(
            inspection_id=ir.id,
            model_config_id=mc.id,
            anomaly_score=0.88,
            confidence_score=0.92,
            is_anomalous=True,
            heatmap_file_path="storage/inspection_results/sn_test_01_heat.png",
        )
        SeverityScoreRepository(session).create(
            inspection_id=ir.id,
            anomaly_result_id=ar.id,
            severity_level="high",
            numeric_score=0.8,
            requires_human_review=True,
        )

        fetched = InspectionRepository(session).get_with_results(ir.id)
        assert fetched is not None
        assert len(fetched.anomaly_results) == 1
        assert len(fetched.severity_scores) == 1

        # Clean up test records via cascade delete
        ManufacturerRepository(session).delete(m)
