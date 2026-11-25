# CLOCKIT / PROMETHEUS-X — Completed Project Details

**Last updated:** 2026-11-25  
**Architecture reference:** `agents/CLOCKIT_Technical_Architecture.md`  
**Database file:** `clockit.db` (SQLite, auto-initialized at repository root)

---

## 1. Repository Layout & Configuration

### Top-Level Files & Directories
- `.gitignore`: Excludes Python caches, `.venv/`, `.env`, `node_modules/`, `dist/`, model weights (`*.pt`, `*.pth`, `*.onnx`, `*.ckpt`, `*.safetensors`, `*.engine`), datasets (`data/*/*`), artifacts (`artifacts/*/*`), runtime storage (`storage/*/*`), and local databases (`*.db`, `*.sqlite`, `*.sqlite3`), while preserving `.gitkeep` files.
- `.env.example`: Default environment template (`APP_NAME=CLOCKIT`, `APP_ENV=development`, `APP_DEBUG=true`, `API_V1_PREFIX=/api/v1`, `DATABASE_URL=sqlite:///./clockit.db`, `DATA_ROOT=./data`, `ARTIFACT_ROOT=./artifacts`, `STORAGE_ROOT=./storage`, `DEFAULT_DEVICE=auto`, `LOG_LEVEL=INFO`, `MAX_UPLOAD_MB=50`).
- `requirements.txt`: Python dependencies including `numpy==2.5.5`, `opencv-python==5.1.0.95`, `sqlalchemy>=2.0`, `alembic>=1.13` (plus `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `pyyaml`, `pytest`, `httpx` installed in `.venv`).
- `configs/`:
  - `configs/hardware.yaml`: `device: auto`, `inference_mode: sequential`, `max_concurrent_inspections: 1`, `max_concurrent_training_jobs: 1`, `reserve_vram_mb: 768`, `lazy_model_loading: true`, `unload_after_stage: true`.
  - `configs/inference.yaml`: `batch_size: 1`, `image_size: 512`, `precision: auto`, model flags (`efficientad`, `yolo11n_seg`, `mobilenet_v3` enabled; `patchcore` disabled).
  - `configs/training.yaml`: `max_concurrent_jobs: 1`, `checkpoint_interval_epochs: 5`, `auto_deploy: false`, `mixed_precision: true`.
- Runtime storage directories (with `.gitkeep` placeholders):
  - `data/`: `raw/`, `processed/`, `train/`, `validation/`, `test/`
  - `artifacts/`: `pretrained/`, `trained/`, `checkpoints/`, `feature_banks/`, `calibration/`, `evaluations/`
  - `storage/`: `uploads/`, `inspection_results/`, `reports/`, `temporary/`
- `agents/`: Modular agent specifications (`platform-api.md`, `data-intelligence.md`, `anomaly-detection-localization.md`, `severity-confidence-shift.md`, `workflow-execution-engine.md`, `decision-aggregation-review.md`, `frontend-management-ui.md`, `infra-observability.md`), `CLOCKIT_Technical_Architecture.md`, and `completed.md`.

---

## 2. Backend (`backend/app/`)

### Core & Application Entry (`backend/app/core/`, `backend/app/main.py`)
- `backend/app/core/config.py`: `Settings` (`pydantic_settings.BaseSettings`) loading `.env` and exposing `get_settings()` (cached via `@lru_cache`).
- `backend/app/core/logging.py`: `setup_logging(level)` configuring stdout logging format.
- `backend/app/main.py`: `create_app()` creates the FastAPI app with:
  - `lifespan` handler calling `setup_logging()`, `init_db()` (creates runtime dirs and SQLite tables).
  - `CORSMiddleware` allowing `http://localhost:5173`, `http://127.0.0.1:5173`, and `http://localhost:3000`.
  - `api_router` mounted at `/api/v1`.

### Database Layer (`backend/app/database/`)
Built with portable SQLAlchemy 2.0 ORM types (`Integer`, `String`, `Text`, `Float`, `Boolean`, `DateTime(timezone=True)`, `JSON`) so `DATABASE_URL` can switch from SQLite to PostgreSQL or MySQL without rewriting models or repositories.
- `backend/app/database/base.py`: `Base(DeclarativeBase)`.
- `backend/app/database/connection.py`:
  - `engine` created from `settings.database_url` (only applies `check_same_thread=False` and `PRAGMA foreign_keys=ON` when `DATABASE_URL` starts with `sqlite`).
  - `SessionLocal`, `ensure_runtime_dirs()`, `init_db()`, `get_db()`, `session_scope()`.
- `backend/app/database/models/` (7 tables in `clockit.db`):
  1. `manufacturer_profiles` (`ManufacturerProfile` in `manufacturer.py`): `id`, `name`, `industry`, `plant_location`, `contact_email`, `metadata_json`, `created_at`, `updated_at`.
  2. `users` (`User` in `manufacturer.py`): `id`, `manufacturer_id` (FK), `username`, `email`, `hashed_password`, `role`, `is_active`, `created_at`.
  3. `model_configs` (`ModelConfig` in `model_config.py`): `id`, `manufacturer_id` (FK), `name`, `model_family`, `version`, `dataset_dir_path`, `weights_file_path`, `hyperparameters_json`, `metrics_json`, `is_active`, `created_at`.
  4. `pipeline_configs` (`PipelineConfig` in `pipeline.py`): `id`, `manufacturer_id` (FK), `name`, `version`, `description`, `modules_json`, `thresholds_json`, `is_active`, `created_at`.
  5. `inspection_records` (`InspectionRecord` in `inspection.py`): `id`, `manufacturer_id` (FK), `user_id` (FK), `pipeline_config_id` (FK), `product_serial`, `station_name`, `image_file_path`, `status`, `overall_decision`, `quality_score`, `inspected_at`.
  6. `anomaly_results` (`AnomalyResult` in `inspection.py`): `id`, `inspection_id` (FK), `model_config_id` (FK), `anomaly_score`, `confidence_score`, `is_anomalous`, `heatmap_file_path`, `mask_file_path`, `bounding_boxes_json`, `processing_time_ms`, `created_at`.
  7. `severity_scores` (`SeverityScore` in `inspection.py`): `id`, `inspection_id` (FK), `anomaly_result_id` (FK), `severity_level`, `numeric_score`, `affected_area_ratio`, `rule_notes`, `requires_human_review`, `created_at`.
- `backend/app/database/repositories/`:
  - `base.py`: `BaseRepository` (`create`, `get_by_id`, `list_all`, `update`, `delete`).
  - `model_repository.py`: `ManufacturerRepository`, `UserRepository`, `ModelConfigRepository`.
  - `pipeline_repository.py`: `PipelineConfigRepository`.
  - `inspection_repository.py`: `InspectionRepository` (includes `get_with_results`, `list_by_manufacturer`), `AnomalyResultRepository`, `SeverityScoreRepository` (includes `list_requiring_review`).

### Pydantic Schemas (`backend/app/schemas/`)
- `common.py`: `HealthResponse`, `MessageResponse`.
- `results.py`: `DefectDetectionSchema`, `ModelUsageSchema`, `InspectionResultSchema`.

### API Endpoints (`backend/app/api/`)
Registered in `backend/app/api/router.py` under `/api/v1`:
- `GET /api/v1/health` (`v1/health.py`): Executes `SELECT 1` against SQLite and returns `HealthResponse` (`status`, `app_name`, `environment`, `database_connected`, `timestamp`).
- `GET /api/v1/inspections` (`v1/inspections.py`): Returns persisted inspections ordered by `inspected_at` descending (`id` as `INS-<id>`, `date`, `industry`, `product`, `pipeline`, `status`, `score`, `severity`, `defects`).
- `POST /api/v1/inspections` (`v1/inspections.py`): Accepts multipart form (`industry`, `product`, `pipelineId`, `threshold`, `fileName`, `file`), saves the uploaded image to `storage/uploads/<uuid><ext>`, runs OpenCV Gaussian-blur contrast/contour analysis (`_analyze_image_bytes`), and persists `InspectionRecord`, `AnomalyResult`, and `SeverityScore` in SQLite.
- `POST /api/v1/inspections/{inspection_id}/confirm` (`v1/inspections.py`): Marks `requires_human_review = False` and records operator review note.
- `GET /api/v1/models` (`v1/models.py`): Lists registered `ModelConfig` entries; auto-seeds `Default Manufacturer` and 3 default models (`PatchCore-v2`, `DefectNet`, `SegLocalizer`) if the table is empty.
- `PATCH /api/v1/models/{model_id}/toggle` (`v1/models.py`): Toggles `is_active` in SQLite and returns updated `ModelInfoOut`.

---

## 3. Frontend (`frontend/`)

- **Stack:** React 18, TypeScript, Vite 5, Tailwind CSS, React Router v6, Axios, Recharts, Lucide React (`node_modules` installed via `npm.cmd --prefix frontend install`).
- **API Integration:**
  - `frontend/src/services/api.ts`: `USE_MOCK = false`, `baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'`.
  - `frontend/vite.config.ts`: Configured `/api` dev proxy to `http://127.0.0.1:8000`.
  - `frontend/src/vite-env.d.ts`: Added Vite client types for `import.meta.env`.
  - `frontend/src/services/inspectionService.ts`: `listInspections()`, `runInspection(req, file?)` sending `FormData` to `POST /inspections`, and `confirmInspection(id)`.
  - `frontend/src/services/modelService.ts`: `listModels()` and `toggleModel(id)` calling `PATCH /models/{id}/toggle`.
- **Connected Pages:**
  - `frontend/src/pages/Dashboard/Dashboard.tsx`: Fetches live inspections, handles empty state (`0` inspections without `NaN`), and displays summary cards, charts, and recent inspections.
  - `frontend/src/pages/Inspection/Inspection.tsx`: Uploads image via `FormData`, displays bounding boxes/heatmap overlay and scores returned by FastAPI, and persists confirmation via `confirmInspection`.
  - `frontend/src/pages/InspectionHistory/InspectionHistory.tsx`: Fetches live inspection history with search, status/industry/severity filters, detail drawer, and CSV export.
  - `frontend/src/pages/Models/Models.tsx`: Lists models from SQLite and persists Enable/Disable toggles via `toggleModel`.
  - `frontend/src/pages/Placeholder/Placeholder.tsx`: Placeholder routes for `/pipelines`, `/datasets`, `/training`, `/analytics`, and `/settings`.

---

## 4. Verification & How to Run

### Verified Checks
- **Backend tests:** `.\.venv\Scripts\python.exe -m pytest backend/tests -v` → **3 passed** (`test_fastapi_app_routes_registered`, `test_health_check_handler`, `test_database_tables_and_repository_crud`).
- **Frontend build:** `npm.cmd --prefix frontend run build` (`tsc && vite build`) → **built cleanly** into `frontend/dist/` (`15.46s`).

### Run Locally
1. **Backend:**
   ```powershell
   .\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --port 8000
   ```
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - Health: `http://127.0.0.1:8000/api/v1/health`
2. **Frontend:**
   ```powershell
   npm.cmd --prefix frontend run dev
   ```
   - Web UI: `http://localhost:5173`

---

## 5. Remaining Work (Not Yet Implemented)
- **AI Model Subsystem (`backend/app/models/`):** `BaseModel` interface, `ModelRegistry`, `ModelLoader`, and adapters for `EfficientAD`, `PatchCore`, `YOLO11n-seg`, `MobileNetV3`, `Severity`, and `Confidence` calibration (currently using the OpenCV heuristic in `v1/inspections.py`).
- **Model Weights (`artifacts/`):** Only `.gitkeep` placeholders exist; no `.pt`/`.pth` weights are downloaded or trained yet.
- **Additional ORM Entities & Subsystems:** `industry`, `product`, `dataset`, `training_job`, `model_version`, `feedback`, orchestration engine, training pipeline, evaluation metrics, and result fusion (Phases 2–7 of `CLOCKIT_Technical_Architecture.md`).
