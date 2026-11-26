# PROMETHEUS-X — Industrial AI Visual Inspection Platform

**PROMETHEUS-X** is a local-first industrial anomaly detection and quality inspection platform. Build **Scanner Units**, attach and train multiple AI **Analysis Modules** on normal or labelled datasets, run **single-sample** or **high-throughput Mass Test** inspections with weighted multi-module aggregation, simulate production-line streams, and review results in real time.

---

## Quick Start (Windows)

### 1. First-Time Setup
```bat
init.bat
```
Creates `.venv`, installs Python (`requirements.txt`) and frontend (`frontend/node_modules`) dependencies, downloads base AI weights into `models/base/`, and initializes `clockit.db`.

### 2. Launch Application + Simulator
```bat
run.bat
```
- **Web UI (Frontend):** `http://localhost:5173`
- **Simulator UI (Line Stream):** `http://127.0.0.1:5180`
- **Backend API & Swagger Docs:** `http://127.0.0.1:8000/api/docs`
- **Brand-New Reset:** `run.bat --resetdb` (clears DB, uploads, custom trained models in `models/custom/`, and outputs while preserving `models/base/`).

---

## Platform Tools & Pages

| Tool / Page | Route / Script | What It Does |
| :--- | :--- | :--- |
| **Overview Dashboard** | `/` | Live 30-day KPIs (`Total Inspections`, `Pass Rate`, `Anomaly Rate`, `Awaiting Review`), 7-day **Inspection Activity** chart, 30-day **Defect Severity Distribution**, and **Recent Inspections**. |
| **Scanner Units** | `/scanners` | Create Scanner Units, attach multiple AI Analysis Modules, configure per-module outputs and **weights (`1–100`)**, and upload datasets inline. |
| **Training** | `/training` | Train a single module or **Train All** modules of a Scanner Unit (`chained` one-by-one or `simultaneous`) with live progress logs. Saves isolated checkpoints to `models/custom/`. |
| **Test Sample** | `/test-sample` | Single-image inspection (requires Scanner Unit). Adjust per-module weights (`max 100`), view **Weighted Average** + **Distinct** outputs, individual module cards, and side-by-side heatmaps. |
| **Mass Test Engine** | `/mass-test` | High-throughput ZIP / multi-image bulk inspection backed by a persistent SQLite job queue (`JobBatch` / `InspectionJob`), bounded CPU prep, single-owner GPU scheduler, Pause/Resume/Cancel/Retry, CSV export, and live hardware/latency telemetry. |
| **Inspection Detail** | `/inspections/:id` | Side-by-side **Unscanned (Original)** vs. **Scanned (Defects Highlighted)** viewer with module heatmap switcher, bounding-box overlays, defect table, and human review. |
| **Review Queue & History** | `/review`, `/history` | Operator approval/rejection of borderline (`Needs review`) inspections and searchable inspection history. |
| **AI Models & Settings** | `/models`, `/settings` | View enabled base & custom models; globally enable/disable models in Settings (hidden across modules and AI Models page). |
| **Analytics & Admin** | `/analytics`, `/admin` | Per-Scanner-Unit analytics breakdown and system administration utilities. |
| **Line Simulator (UI & CLI)** | `simulator/web_simulator.py`, `simulator/stream_simulator.py` | Streams images from `simulator/sample_data/` (or any folder) one-by-one to the server and receives `True` (`PASS`) / `False` (`FAIL` or `REVIEW_REQUIRED`) with live previews & CSV export. |

---

## Supported AI Models (`models/base/` & `models/custom/`)

| Model Key | Model | Speed & Capability | Training Paradigm |
| :--- | :--- | :--- | :--- |
| `efficientad_small` | **EfficientAD-Small** | High Speed · Real-time surface anomaly detection & pixel localization | Normal-only |
| `efficientad_medium` | **EfficientAD-Medium** | Medium-High Speed · Balanced normal-only surface anomaly detection | Normal-only |
| `patchcore` | **PatchCore (WideResNet-50)** | Medium Speed · High-accuracy coreset memory bank anomaly detection | Normal-only |
| `dinomaly` | **Dinomaly (DINOv2 ViT-B/14)** | Low Speed · High-precision Vision Transformer reconstruction | Normal-only |
| `anomalydino` | **AnomalyDINO (DINOv2 Few-Shot)** | High Speed (Inference) · Custom WACV 2025 few-shot rotation aug + PCA foreground masking + cosine-NN + mean top-1% | Few-shot / Normal-only |
| `omniposead` | **OmniPoseAD (Pose-Agnostic)** | Low Speed · Multi-view DINOv2 reference bank + ORB/homography pose alignment | Multi-view normal |
| `yolo11n_seg` | **YOLO11n-Seg (Nano)** | High Speed · Real-time supervised bounding boxes & segmentation masks | Pretrained / Fine-tune |
| `yolo11m_seg` | **YOLO11m-Seg (Medium)** | Medium Speed · Higher-accuracy supervised detection & segmentation | Pretrained / Fine-tune |
| `opencv_heuristic` | **OpenCV Contrast Heuristic** | Ultra-High Speed · Deterministic contrast-deviation fallback (no training) | None |

---

## Supported Datasets (MVTec AD & Kaggle)

PROMETHEUS-X validates uploaded datasets as **flat image-only ZIP archives** (root-level `.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`, `.tif`, `.tiff` — no nested subfolders) and standardizes images to **640×480 (480p)**.

### 1. MVTec AD (MVTec Anomaly Detection)
- **Official Source:** [MVTec AD Dataset](https://www.mvtec.com/company/research/datasets/mvtec-ad)
- **15 Industrial Categories:**
  - **Textures (5):** `carpet`, `grid`, `leather`, `tile`, `wood`
  - **Objects (10):** `bottle`, `cable`, `capsule`, `hazelnut`, `metal_nut`, `pill`, `screw`, `toothbrush`, `transistor`, `zipper`
- **How to use in PROMETHEUS-X:**
  - **Training:** Zip the images inside `<category>/train/good/` (flat, no subfolders) and upload under **Datasets** or inline in **Scanner Units**.
  - **Mass Testing:** Zip defective/test images from `<category>/test/<defect_type>/` and upload on the **Mass Test** page.

### 2. Kaggle Industrial Defect Datasets
- **[Casting Product Image Data for Quality Inspection](https://www.kaggle.com/datasets/ravirajsinh45/casting-product-image-data-for-quality-inspection)** — Top-view grayscale submersible pump impeller images (`ok_front` for normal-only training, `def_front` for testing).
- **[NEU Surface Defect Database](https://www.kaggle.com/datasets/kaustubhdixit/neu-surface-defect-database)** — Hot-rolled steel strip surface defects (crazing, inclusion, patches, pitted surface, rolled-in scale, scratches).
- **[Casting Defect Detection](https://www.kaggle.com/datasets/theovasilou/casting-defect-detection)** — Multi-class casting defect dataset for classification and inspection benchmarking.
- **[Surface Defect Inspection Dataset (SDID)](https://www.kaggle.com/datasets/ziya07/surface-defect-inspection-dataset-sdid)** — High-resolution industrial metal and automotive panel surface flaws.

---

## External API & High-Throughput Engine

Both **Mass Test UI** and **External API** share the same processing pipeline:

- `POST /api/v1/jobs` — Queue a single image asynchronously (`202 Accepted`, optional `idempotency_key` and `X-API-Key`).
- `POST /api/v1/jobs/bulk` — Queue multiple images or a `.zip` archive (`MASS_TEST` or `API`).
- `GET /api/v1/batches/{batch_id}` & `GET /api/v1/batches/{batch_id}/results` — Poll batch progress and paginated `passed` (`true`/`false`), `overall_decision`, `quality_score`, and `severity` results.
- `POST /api/v1/batches/{batch_id}/{pause,resume,cancel,retry}` — Control dispatch without interrupting in-flight GPU work.
- `POST /api/v1/inspections` — Synchronous single-image scan returning `passed: true/false`, `weighted_outputs`, `distinct_outputs`, and `module_results`.
- `GET /api/v1/engine/status` & `GET /api/v1/engine/metrics` — Queue depth, throughput (`img/min`), P50/P95 latency, CPU/RAM/GPU VRAM, and loaded models.

---

## Project Structure & Verification

```text
UnclockThat/
├── backend/app/
│   ├── api/v1/            # FastAPI routes (scanner_units, training, inspections, engine_api, analytics, settings)
│   ├── database/          # SQLAlchemy ORM models & SQLite connection
│   ├── engine/            # High-throughput engine (registry, preprocessing, GPU scheduler, worker, aggregator)
│   └── models/            # Model adapters (Anomalib, EfficientAD, AnomalyDINO, OmniPoseAD, YOLO) & catalogue
├── frontend/              # React + TypeScript + Vite + Tailwind CSS UI
├── models/
│   ├── base/              # Base/pretrained model weights
│   └── custom/            # Trained Scanner Unit module checkpoints
├── simulator/
│   ├── sample_data/       # Sample normal & defective PNGs
│   ├── web_simulator.py   # Browser simulator UI (port 5180)
│   ├── simulator_ui.py    # Desktop Tkinter simulator UI
│   └── stream_simulator.py# CLI image stream client
├── scripts/               # install_models.py, benchmark_engine.py, train_efficientad.py
├── init.bat               # One-step environment & model setup
└── run.bat                # Launch backend + frontend + simulator UI
```

```bat
:: Run backend integration tests
.venv\Scripts\python.exe -m pytest backend/tests -v

:: Build frontend production bundle
npm.cmd --prefix frontend run build

:: Run 100-image engine throughput benchmark
.venv\Scripts\python.exe scripts\benchmark_engine.py
```
