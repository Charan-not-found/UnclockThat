# CLOCKIT — Application Overview & Feature Reference

**CLOCKIT** (PROMETHEUS-X) is an industrial visual quality-inspection platform built as a modular monolith with a **FastAPI + SQLite/SQLAlchemy** backend, a **React + TypeScript + Vite** frontend, and **Anomalib (EfficientAD)** + **OpenCV** for defect/anomaly detection.

---

## 1. How the Application Works (End-to-End Flow)

```text
User (React UI)
   │  Uploads image + selects Industry, Product, Threshold
   ▼
POST /api/v1/inspections  (FastAPI: backend/app/api/v1/inspections.py)
   │
   ├─► 1. Saves raw image to storage/uploads/<uuid>.<ext>
   │
   ├─► 2. Runs Inference:
   │      ├─ If artifacts/trained/efficientad_casting.ckpt exists:
   │      │     EfficientAdAdapter.predict_bytes()
   │      │     • Resizes to 256×256, runs EfficientAD model
   │      │     • Generates blended heatmap overlay -> storage/inspection_results/<uuid>_heatmap.png
   │      │     • Extracts defect bounding boxes above threshold
   │      └─ Otherwise (fallback):
   │            OpenCV Gaussian-blur absdiff + contour heuristic
   │
   ├─► 3. Computes Quality Decision & Severity:
   │      • Decision: PASS ("Completed"), REVIEW_REQUIRED ("Needs review"), or FAIL ("Failed")
   │      • Severity: Informational, Minor, Major, or Critical
   │      • Quality Score: 5–99 scale derived from anomaly score
   │
   └─► 4. Persists to SQLite (clockit.db):
          • inspection_records  (metadata + image_file_path)
          • anomaly_results     (scores, bounding boxes, heatmap_file_path, processing_time_ms)
          • severity_scores     (severity_level, requires_human_review flag)
```

---

## 2. Core System Layers

### Backend (`backend/app/`)
- **Entry Point (`backend/app/main.py`):** Initializes logging, creates runtime storage directories (`uploads`, `inspection_results`, `reports`, `temporary`), initializes SQLite tables, mounts `/api/v1`, and serves static image/heatmap files at `/uploads` and `/results`.
- **Configuration (`backend/app/core/config.py`):** Typed `Settings` via `pydantic-settings` reading `.env` (`DATABASE_URL`, `STORAGE_ROOT`, `ARTIFACT_ROOT`, `DATA_ROOT`, `DEFAULT_DEVICE`, `MAX_UPLOAD_MB`).
- **API Routers (`backend/app/api/v1/`):**
  - `health.py` — Database connectivity & service health (`GET /api/v1/health`)
  - `inspections.py` — Inspection execution, listing, detail retrieval, review queue, and human review submission
  - `models.py` — Read-only model listing, detail lookup, and active/disabled toggling
  - `pipelines.py` — Pipeline configuration listing, creation, and toggling
  - `analytics.py` — Server-side aggregated KPIs, daily trends, severity distribution, and status distribution
  - `admin.py` — Idempotent database seeding (`POST /api/v1/admin/seed`)

### Database Layer (`backend/app/database/`)
- **Engine & Session (`connection.py`):** SQLAlchemy 2.x with `Base(DeclarativeBase)`. Defaults to local SQLite (`clockit.db`) and can be switched to PostgreSQL or MySQL via `DATABASE_URL` without rewriting queries.
- **7 ORM Tables:**
  1. `manufacturer_profiles` — Tenant/plant metadata (`ManufacturerProfile`)
  2. `users` — Platform users per manufacturer (`User`)
  3. `model_configs` — Registered AI models, artifact file paths, hyperparameters, metrics, active flag (`ModelConfig`)
  4. `pipeline_configs` — Ordered inspection pipeline stage definitions and thresholds (`PipelineConfig`)
  5. `inspection_records` — Product serial, station, image path, decision, quality score, timestamp (`InspectionRecord`)
  6. `anomaly_results` — Anomaly/confidence scores, bounding boxes JSON, heatmap/mask paths, latency (`AnomalyResult`)
  7. `severity_scores` — Severity level, numeric score, human-review flag, review notes (`SeverityScore`)
- **Repositories (`repositories/`):** `BaseRepository[T]` plus `ManufacturerRepository`, `UserRepository`, `ModelConfigRepository`, `PipelineConfigRepository`, `InspectionRepository`, `AnomalyResultRepository`, and `SeverityScoreRepository`.

### AI Model Subsystem (`backend/app/models/` & `scripts/`)
- **`EfficientAdAdapter` (`backend/app/models/efficientad_adapter.py`):** Thread-safe lazy loader for trained Anomalib EfficientAD checkpoints (`artifacts/trained/efficientad_casting.ckpt`). Generates heatmap overlays and defect bounding boxes.
- **Training Script (`scripts/train_efficientad.py`):** Trains EfficientAD-Small on local normal/defective datasets (e.g., `data/raw/casting/casting_data/casting_data/`) using local pretrained teacher weights (`artifacts/pretrained/pretrained_teacher_small.pth`), evaluates on the held-out test split, saves the checkpoint, and updates `clockit.db`.
- **Weight Downloader (`scripts/download_weights.py`):** Downloads official EfficientAD teacher weights (`pretrained_teacher_small.pth`, `pretrained_teacher_medium.pth`) and `yolo11n-seg.pt` into `artifacts/pretrained/`.

### Frontend (`frontend/src/`)
- **Stack:** React 18, TypeScript, Vite 5, Tailwind CSS, React Router v6, Axios, Recharts, Lucide icons.
- **Design System (`styles/globals.css`):** CSS design tokens (`--color-*`, `--space-*`, `--radius-*`, `--shadow-*`), light/dark theme support, tabular numerals for tables, and spec-compliant status/severity badges (`StatusBadge.tsx`).
- **API Client (`services/api.ts`):** Centralized Axios client (`VITE_API_URL ?? http://localhost:8000/api/v1`) with structured error classification (`NETWORK_UNAVAILABLE`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_FAILED`, `SERVER_ERROR`). Never substitutes mock data on failure.

---

## 3. Complete Feature Breakdown

### 1. Overview Dashboard (`/`)
- Displays live KPI cards computed from persisted records: **Total Inspections**, **Pass Rate (30d)**, **Anomaly Rate (30d)**, and **Awaiting Review**.
- **7-Day Inspection Trend** line chart (total inspections, anomalies/fails, needs review).
- **Severity Distribution (30d)** donut chart sourced from `severity_scores`.
- **Recent Inspections** table with clickable links directly to each inspection's detail page.

### 2. New Inspection (`/inspect`)
- Select **Industry** (Automotive, Electronics, Textile, Aerospace, Manufacturing) and **Product**.
- Adjust **Anomaly Threshold** (`0.00` to `1.00`).
- Upload an image (`JPG`, `PNG`, up to 50 MB) with instant preview.
- Runs real inference (`EfficientAD-Small` when trained checkpoint exists, or OpenCV heuristic fallback).
- Displays side-by-side original image and localization overlay with severity-labeled bounding boxes, quality score, status badge, and defect table.
- Includes an inline **Submit Human Review** modal (`Approved` / `Rejected` + mandatory note).

### 3. Inspection History (`/history`)
- Lists persisted inspection records from SQLite with **ID**, **Product**, **Industry**, **Station**, **Status**, **Severity**, **Quality Score**, **Defect Count**, and **Date**.
- Filterable by status (`Completed`, `Failed`, `Needs review`) and searchable by inspection ID or product name.

### 4. Inspection Detail (`/inspections/:id`)
- **Evidence Viewer:** Displays the stored uploaded image served from `/uploads/<filename>` with a toggle to show/hide defect bounding-box overlays.
- **Model Stage Results:** Shows per-stage model name, anomaly score, confidence score, processing time (ms), and individual defect bounding-box table.
- **Evidence Provenance:** Displays pipeline name, pipeline ID, overall decision, and stored image path.
- **Human Review Panel:** Shows existing review decision/note or allows submitting an `Approved`/`Rejected` decision with a mandatory reason.

### 5. Review Queue (`/review`)
- Dedicated work queue (`GET /api/v1/inspections/review-queue`) listing only inspections where `requires_human_review = True`.
- Automatically ordered by **severity** (`Critical` → `Major` → `Minor` → `Informational`) and then **age** (oldest first), with direct links to review each item.

### 6. Pipelines (`/pipelines`)
- Lists all inspection pipeline configurations with version, manufacturer, stage count, state (`Ready` / `Disabled`), and creation date.
- Expandable **Pipeline Stage Details** cards showing configured stages.
- **New Pipeline** modal to create pipelines (`POST /api/v1/pipelines`) and one-click **Enable / Disable** toggling (`PATCH /api/v1/pipelines/{id}/toggle`).

### 7. AI Models (`/models`)
- Lifecycle-aware model registry (`GET /api/v1/models` — pure read, never auto-creates records).
- Shows model **Name**, **Family** (EfficientAD, YOLO-Seg, PatchCore, MobileNet, OpenCV Heuristic), **Task**, **Version**, **State** (`Ready` / `Disabled`), and live **on-disk weight file verification** (`✓ Present` / `✗ Missing`).
- Allows enabling/disabling models (`PATCH /api/v1/models/{id}/toggle`) and displays artifact path cards.

### 8. Analytics (`/analytics`)
- All metrics are computed server-side from persisted database rows with explicit **metric definitions** and **denominators** (no fabricated rates on empty datasets).
- Configurable date range (`7`, `30`, `90` days) and trend window (`7`, `14`, `30` days).
- Includes KPI summary cards, **Daily Trend** line chart, **Severity Distribution** bar chart, and **Decision Distribution** donut chart.

### 9. Administration (`/admin`)
- **Database Seeding:** One-click idempotent seed button (`POST /api/v1/admin/seed`) that registers downloaded pretrained weights, creates the default manufacturer, and sets up the default pipeline.
- **Roadmap Visibility:** Lists planned production administration capabilities (Organization, Facilities, Users/Roles, Audit Log).

### 10. Settings (`/settings`)
- Displays active frontend runtime configuration (`VITE_API_URL`, build mode, frontend version) and planned user/hardware settings.

### 11. Unavailable / Planned Features (Explicitly Labelled)
Following the UI specification's strict *"no half-finished shells"* rule, pages whose backend workflows are not yet implemented are clearly marked **Unavailable**:
- **Datasets (`/datasets`):** Planned for Milestone 3 (dataset upload wizard, duplicate/leakage checks, immutable versioning).
- **Training (`/training`):** Planned for Milestone 5 (UI-driven training job queue and live checkpoint monitoring; currently training is run via `scripts/train_efficientad.py`).
- **Authentication & Multi-Tenant RBAC:** Planned for Milestone 7 (endpoints currently run open for local prototype use).
