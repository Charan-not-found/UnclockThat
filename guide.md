# CLOCKIT User & Developer Guide

Welcome to **CLOCKIT** — an industrial visual quality-inspection platform built with **FastAPI + SQLite/SQLAlchemy** on the backend, **React + TypeScript + Vite** on the frontend, and **Anomalib (EfficientAD)** + **OpenCV** for anomaly detection.

---

## 1. How CLOCKIT Works (Architecture Overview)

1. **Image Upload & Storage**
   - You upload a product image in the **New Inspection** page (`/inspect`) or via `POST /api/v1/inspections`.
   - The backend saves the uploaded image to `storage/uploads/` and stores only the file path in SQLite (`clockit.db`).
2. **Inference Engine**
   - If a trained EfficientAD checkpoint exists at `artifacts/trained/efficientad_casting.ckpt`, `EfficientAdAdapter` (`backend/app/models/efficientad_adapter.py`) runs real EfficientAD inference:
     - Computes an anomaly score and per-pixel anomaly map.
     - Saves a blended heatmap overlay image to `storage/inspection_results/`.
     - Extracts bounding boxes for regions exceeding the anomaly threshold.
   - Otherwise, it falls back to the OpenCV Gaussian-blur difference heuristic in `backend/app/api/v1/inspections.py`.
3. **Decision & Severity Scoring**
   - Based on the anomaly score and your chosen threshold:
     - **PASS** → Status: `Completed`
     - **REVIEW_REQUIRED** → Status: `Needs review` (added to the **Review Queue**)
     - **FAIL** → Status: `Failed`
   - Severity is classified using the platform vocabulary: `Informational`, `Minor`, `Major`, or `Critical`.
4. **Persistence & Review**
   - Results are persisted across `inspection_records`, `anomaly_results`, and `severity_scores` in `clockit.db`.
   - Operators review flagged inspections in **Review Queue** (`/review`) or **Inspection Detail** (`/inspections/:id`) with an `Approved` or `Rejected` decision and a mandatory review note.

---

## 2. Running the Application

Open two terminals in `c:\ClockIT\UnclockThat`:

### Terminal 1 — Start Backend API
```powershell
.\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --port 8000
```
- API base URL: `http://localhost:8000/api/v1`
- Interactive Swagger docs: `http://localhost:8000/api/docs`

### Terminal 2 — Start Frontend UI
```powershell
npm.cmd --prefix frontend run dev
```
- Web UI: `http://localhost:5173`

### First-Time Database Seeding (if starting with an empty DB)
The database (`clockit.db`) initializes automatically on startup. If no models or pipelines are registered yet:
- Open `http://localhost:5173/admin` and click **Run seed**, **or**
- Run:
  ```powershell
  curl -X POST http://localhost:8000/api/v1/admin/seed
  ```

---

## 3. Using the Web Interface

| Page | Route | What it does |
|---|---|---|
| **Overview** | `/` | Live KPIs, 7-day trend, severity breakdown, and recent inspections from `clockit.db`. |
| **New Inspection** | `/inspect` | Select industry/product, set anomaly threshold (`0.00–1.00`), upload an image, and run inspection. |
| **Inspection History** | `/history` | Browse, search, and filter all past inspections. |
| **Inspection Detail** | `/inspections/:id` | View uploaded image, toggle bounding-box overlays, inspect model stage scores, and submit human review. |
| **Review Queue** | `/review` | Priority-sorted queue (`Critical` → `Major` → `Minor`, oldest first) for inspections needing human review. |
| **Pipelines** | `/pipelines` | View, create, and enable/disable inspection pipeline configurations. |
| **AI Models** | `/models` | Inspect registered models, weight file presence on disk, and toggle active status. |
| **Analytics** | `/analytics` | Server-computed pass rate, anomaly rate, daily trends, and severity/decision distributions. |
| **Administration** | `/admin` | Run idempotent database seeding (`POST /api/v1/admin/seed`). |
| **Settings** | `/settings` | View active frontend environment and API base URL. |
| **Datasets / Training** | `/datasets`, `/training` | Marked *Unavailable* in the UI for now — dataset placement and model training are done locally (see Section 4). |

---

## 4. Training with Your Own Dataset

### Where to Place Datasets
Keep your datasets under `data/`:
- `data/raw/<product_name>/` — Original dataset files
- `data/train/` — Training split
- `data/validation/` — Validation split
- `data/test/` — Held-out test split
- `data/processed/` — Preprocessed data (if needed)

For **EfficientAD** (unsupervised anomaly detection), training uses **normal (defect-free) images only**, while defective images are used only in validation/test:
```text
data/raw/<your_product>/
├── train/
│   └── ok_front/      # Normal images only
└── test/
    ├── ok_front/      # Normal test images
    └── def_front/     # Defective test images
```

### Running EfficientAD Training
Use `scripts/train_efficientad.py` (which uses `anomalib` and `artifacts/pretrained/pretrained_teacher_small.pth`):

```powershell
# Quick baseline run (CPU-friendly)
.\.venv\Scripts\python.exe scripts/train_efficientad.py --max-epochs 2 --limit-train-batches 100 --limit-val-batches 20 --limit-test-batches 20

# Longer run for higher accuracy
.\.venv\Scripts\python.exe scripts/train_efficientad.py --max-epochs 10 --limit-train-batches 1000 --limit-val-batches 50 --limit-test-batches 50
```

When training finishes:
1. The checkpoint is saved to `artifacts/trained/efficientad_casting.ckpt`.
2. Test metrics (`image_AUROC`, `image_F1Score`) are logged and saved into `clockit.db` for `EfficientAD-Small (Prototype)`.
3. `POST /api/v1/inspections` automatically detects and uses the checkpoint on the next inspection.

### Downloading / Refreshing Pretrained Weights
If `artifacts/pretrained/` is missing weights (`pretrained_teacher_small.pth`, `pretrained_teacher_medium.pth`, `yolo11n-seg.pt`), run:
```powershell
.\.venv\Scripts\python.exe scripts/download_weights.py
```

---

## 5. Customizing CLOCKIT

### Environment & Database Configuration
Settings are managed in `backend/app/core/config.py` via `.env` (see `.env.example`):
- **`DATABASE_URL`**: Defaults to `sqlite:///.../clockit.db`. Because the database layer uses SQLAlchemy ORM and repository classes (`backend/app/database/repositories/`), you can switch to PostgreSQL or MySQL by changing `DATABASE_URL` without rewriting application queries.
- **`STORAGE_ROOT` / `ARTIFACT_ROOT` / `DATA_ROOT`**: Override where uploads, checkpoints, and datasets are stored.
- **`VITE_API_URL`**: Set in `frontend/.env` to point the frontend to a non-default backend URL (defaults to `http://localhost:8000/api/v1`).

### Training & Inference YAML Configs
- `configs/training.yaml` — Concurrency (`max_concurrent_jobs: 1`), checkpoint intervals, device, and dataloader settings.
- `configs/inference.yaml` — Default image size, batch size, and enabled model flags.
- `configs/hardware.yaml` — Hardware resource defaults.

### Adding a New AI Model Adapter
1. Create a new adapter module under `backend/app/models/` (similar to `backend/app/models/efficientad_adapter.py`) that loads your checkpoint lazily and returns `anomaly_score`, `confidence_score`, `defects`, `heatmap_path`, and `processing_time_ms`.
2. Register the model in `clockit.db` (or via `backend/app/api/v1/admin.py`).
3. Route to your adapter in `backend/app/api/v1/inspections.py` based on active model configuration or pipeline stage.

### Customizing Industries & Products in the UI
Edit `INDUSTRIES` in `frontend/src/pages/Inspection/Inspection.tsx` to add your own manufacturing industries and product names.

### Customizing Design & Theme
Edit CSS design tokens in `frontend/src/styles/globals.css` (`--color-bg`, `--color-surface`, `--color-brand`, status colors, and dark mode variables).

---

## 6. Verification & Tests

```powershell
# Run backend integration tests
.\.venv\Scripts\python.exe -m pytest backend/tests -v

# Build frontend production bundle
npm.cmd --prefix frontend run build
```
