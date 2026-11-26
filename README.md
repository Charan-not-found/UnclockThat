# PROMETHEUS-X — Industrial AI Visual Inspection Platform

**PROMETHEUS-X** is a local-first industrial anomaly detection and quality inspection platform. Create **Scanner Units**, attach and train multiple AI **Analysis Modules** on normal/labelled datasets, run **single-sample** or **high-throughput Mass Test** inspections with weighted multi-module aggregation, and review results in real time.

---

## Key Features

- **Scanner Units & Multi-Module Aggregation**: Compose Scanner Units with multiple AI modules, per-module weights (`1–100`), and configurable outputs (`anomaly_score`, `heatmap`, `bounding_boxes`, `defect_class`, `segmentation_mask`). Shared numeric outputs are combined via weighted average; distinct outputs are preserved as-is.
- **Supported AI Models** (`models/base/` & `models/custom/`):
  - **PatchCore** (`WideResNet-50`) — medium-speed normal-only coreset anomaly detection.
  - **Dinomaly** (`DINOv2 ViT-B/14`) — high-precision ViT reconstruction anomaly detection.
  - **EfficientAD-Small / Medium** — high-speed real-time surface anomaly detection.
  - **AnomalyDINO** (`DINOv2 Few-Shot`) — custom WACV 2025 implementation with few-shot rotation augmentation, PCA foreground patch masking, cosine-NN search, and mean top-1% aggregation.
  - **OmniPoseAD** — pose-agnostic multi-view DINOv2 reference bank + homography alignment.
  - **YOLO11n-Seg / YOLO11m-Seg** — supervised object/defect detection & instance segmentation.
  - **OpenCV Contrast Heuristic** — deterministic non-AI fallback.
- **Training Orchestrator**: Train individual modules or **Train All** (`chained` or `simultaneous` mode) with live progress logs and isolated per-module weights in `models/custom/`.
- **High-Throughput Inspection Engine**: Persistent SQLite-backed `JobBatch` / `InspectionJob` queue, bounded CPU preprocessing, single-owner GPU scheduler, restart recovery, **Mass Test** UI (`/mass-test`) for ZIP/multi-image batches, External API (`/api/v1/jobs`, `/api/v1/batches/*`), and live telemetry (`/api/v1/engine/status`, `/api/v1/engine/metrics`).
- **Overview & Analytics**: Real-time KPIs, 7-day inspection activity trend, 30-day severity distribution, per-Scanner-Unit analytics, and Human Review Queue.

---

## Quick Start (Windows)

### 1. First-time Setup
```bat
init.bat
```
Creates `.venv`, installs Python (`requirements.txt`) and frontend (`frontend/node_modules`) dependencies, downloads base models into `models/base/`, and initializes `clockit.db`.

### 2. Run the Application
```bat
run.bat
```
- **Frontend UI:** `http://localhost:5173`
- **Backend API & Swagger Docs:** `http://127.0.0.1:8000/api/docs`
- **Brand-new Reset:** `run.bat --resetdb` (clears DB, uploads, custom trained models, and outputs while preserving `models/base/`).

---

## Project Structure

```text
UnclockThat/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # FastAPI endpoints (scanner_units, training, inspections, engine_api, analytics, settings)
│   │   ├── database/      # SQLAlchemy ORM models, repositories, SQLite init
│   │   ├── engine/        # High-throughput processing engine (registry, scheduler, worker, aggregator)
│   │   └── models/        # Model adapters (Anomalib, EfficientAD, AnomalyDINO, OmniPoseAD, YOLO) & catalogue
│   └── tests/             # Integration tests
├── frontend/              # React + TypeScript + Vite + Tailwind CSS UI
├── models/
│   ├── base/              # Base/pretrained model weights
│   └── custom/            # Trained Scanner Unit module checkpoints
├── scripts/               # Model installer, training, and benchmark utilities
├── init.bat               # One-step environment & model setup
└── run.bat                # Launch backend + frontend
```

---

## Testing & Verification

```bat
.venv\Scripts\python.exe -m pytest backend/tests -v
npm.cmd --prefix frontend run build
.venv\Scripts\python.exe scripts\benchmark_engine.py
```
