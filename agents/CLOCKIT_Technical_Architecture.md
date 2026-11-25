# CLOCKIT --- Technical Architecture & Repository Blueprint

**Document status:** Architecture baseline\
**Project:** CLOCKIT\
**Target:** Hackathon prototype with a path to a multi-industry
industrial inspection platform\
**Initial development hardware:** 16 GB RAM, 4-core CPU, NVIDIA RTX 3050
(VRAM variant to be confirmed), local execution\
**Architecture decision:** Modular monolith with pluggable model
adapters, configurable inspection pipelines, isolated training
workflows, and versioned model artifacts.

------------------------------------------------------------------------

## 1. Project vision

CLOCKIT is an industrial inspection and quality-management platform. It
accepts manufacturer-specific data, runs configurable AI inspection
workflows, combines the outputs of multiple specialist models, and
presents a unified inspection result.

The platform should support:

-   Multiple manufacturing industries and product categories.
-   Manufacturer-owned datasets and custom model adaptation.
-   Independent AI modules for anomaly detection, localization,
    classification, severity estimation, and confidence calibration.
-   Configurable inspection pipelines, including sequential, parallel,
    and conditional steps.
-   Unified result fusion and quality scoring.
-   Model evaluation, versioning, approval, rollback, and deployment.
-   Human review and verified feedback for future retraining.
-   Inspection history, analytics, and reports.

### Core architectural principle

**Models are specialists; the orchestrator coordinates them.**

Models must not call one another directly or depend on one another's
internal implementation. They communicate through documented
input/output schemas and pipeline context. This makes it possible to
replace a model, add a new industry, or alter a workflow without
rewriting the entire application.

------------------------------------------------------------------------

## 2. Architecture decisions

  -----------------------------------------------------------------------
  Area                    Initial decision        Reason
  ----------------------- ----------------------- -----------------------
  Overall architecture    Modular monolith        Simple to develop,
                                                  test, and debug during
                                                  a hackathon

  Backend                 FastAPI                 Python-native
                                                  integration with ML
                                                  libraries

  Frontend                React + Vite            Flexible management
                                                  dashboard

  ML framework            PyTorch                 Training and inference
                                                  support

  Image processing        OpenCV + Pillow         Image loading and
                                                  preprocessing

  Data validation         Pydantic                Typed API and model
                                                  contracts

  Database                SQLite initially        No database server
                                                  required for the
                                                  prototype

  Database migrations     Alembic                 Controlled schema
                                                  evolution

  Model configuration     YAML + database         Human-readable defaults
                          metadata                and persisted
                                                  configurations

  Model artifacts         Local filesystem        Avoid extra
                          initially               infrastructure

  Training execution      One heavy GPU job at a  Fits the initial
                          time                    workstation

  Inference execution     Sequential by default   Limits VRAM pressure

  Background work         In-process job manager  Avoid Redis/Celery
                          initially               complexity at first

  API style               REST, versioned under   Straightforward
                          `/api/v1`               frontend integration

  Tests                   pytest                  Unit and integration
                                                  coverage

  Deployment              Local development       Keep hackathon setup
                          first; Docker optional  manageable
  -----------------------------------------------------------------------

Do not introduce Kubernetes, Kafka, microservices, Redis, or a
distributed task queue in the first prototype unless a demonstrated
requirement justifies them.

------------------------------------------------------------------------

## 3. High-level system architecture

``` text
                         CLOCKIT
                            |
                 +----------+----------+
                 |                     |
             React UI              FastAPI
                 |                     |
                 +---------- REST -----+
                                       |
                               API / Service Layer
                                       |
                 +---------------------+--------------------+
                 |                     |                    |
           Inspection Service    Training Service     Dataset Service
                 |                     |                    |
                 +---------------------+--------------------+
                                       |
                              Model Orchestrator
                                       |
              +------------------------+-----------------------+
              |                        |                       |
        Pipeline Engine          Model Registry          Resource Manager
              |                        |                       |
       Dependency Resolver       Model Loader             CPU/GPU policy
              |                        |
        Execution Context      Model Adapters
              |                        |
       +------+------+---------+-------+---------+
       |             |         |                   |
   Anomaly       Localization Classification   Severity / Confidence
   Detection       / Segmentation                Estimation
       |             |         |                   |
       +-------------+---------+-------------------+
                                       |
                                Result Fusion
                                       |
                           Evaluation / Quality Score
                                       |
                         Database + Artifact Storage
                                       |
                             Reports / Analytics
```

Training is a separate workflow:

``` text
Dataset Upload
     |
Dataset Validation and Analysis
     |
Training Strategy Selection
     |
Model-specific Trainer
     |
Checkpointing and Experiment Tracking
     |
Evaluation on held-out data
     |
Approval / Rejection
     |
Model Registry (new version)
     |
Controlled deployment or rollback
```

Inference and training must share model interfaces and artifact
conventions, but training must not overwrite or interrupt the currently
deployed model.

------------------------------------------------------------------------

## 4. Final repository structure

The tree below is the target repository layout. Implement it
progressively; do not create dozens of empty files and pretend the
features are complete.

``` text
CLOCKIT/
│
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
├── Makefile
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_DOCUMENTATION.md
│   ├── MODEL_DOCUMENTATION.md
│   ├── TRAINING_GUIDE.md
│   ├── DATASET_GUIDE.md
│   ├── PIPELINE_GUIDE.md
│   └── DEVELOPMENT_GUIDE.md
│
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── alembic.ini
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── inspections.py
│   │   │       ├── models.py
│   │   │       ├── training.py
│   │   │       ├── datasets.py
│   │   │       ├── pipelines.py
│   │   │       ├── industries.py
│   │   │       ├── analytics.py
│   │   │       ├── feedback.py
│   │   │       └── health.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   ├── exceptions.py
│   │   │   ├── security.py
│   │   │   └── constants.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── common.py
│   │   │   ├── inspection.py
│   │   │   ├── model.py
│   │   │   ├── dataset.py
│   │   │   ├── training.py
│   │   │   ├── pipeline.py
│   │   │   ├── defect.py
│   │   │   ├── severity.py
│   │   │   └── results.py
│   │   │
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   ├── base.py
│   │   │   ├── models/
│   │   │   │   ├── manufacturer.py
│   │   │   │   ├── industry.py
│   │   │   │   ├── product.py
│   │   │   │   ├── dataset.py
│   │   │   │   ├── inspection.py
│   │   │   │   ├── training_job.py
│   │   │   │   ├── model_version.py
│   │   │   │   ├── pipeline.py
│   │   │   │   └── feedback.py
│   │   │   └── repositories/
│   │   │       ├── inspection_repository.py
│   │   │       ├── dataset_repository.py
│   │   │       ├── model_repository.py
│   │   │       ├── pipeline_repository.py
│   │   │       └── training_repository.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base_model.py
│   │   │   ├── model_registry.py
│   │   │   ├── model_loader.py
│   │   │   ├── model_manager.py
│   │   │   ├── model_metadata.py
│   │   │   ├── model_validator.py
│   │   │   ├── anomaly_detection/
│   │   │   │   ├── efficientad/
│   │   │   │   │   ├── model.py
│   │   │   │   │   ├── adapter.py
│   │   │   │   │   └── config.yaml
│   │   │   │   └── patchcore/
│   │   │   │       ├── model.py
│   │   │   │       ├── adapter.py
│   │   │   │       └── config.yaml
│   │   │   ├── localization/
│   │   │   │   └── yolo_seg/
│   │   │   │       ├── model.py
│   │   │   │       ├── adapter.py
│   │   │   │       └── config.yaml
│   │   │   ├── classification/
│   │   │   │   └── mobilenet/
│   │   │   │       ├── model.py
│   │   │   │       ├── adapter.py
│   │   │   │       └── config.yaml
│   │   │   ├── severity/
│   │   │   │   ├── model.py
│   │   │   │   └── config.yaml
│   │   │   └── confidence/
│   │   │       ├── calibration.py
│   │   │       ├── temperature_scaling.py
│   │   │       └── isotonic.py
│   │   │
│   │   ├── preprocessing/
│   │   │   ├── image_loader.py
│   │   │   ├── image_validator.py
│   │   │   ├── image_resizer.py
│   │   │   ├── normalizer.py
│   │   │   ├── augmentation.py
│   │   │   ├── tiling.py
│   │   │   └── transforms.py
│   │   │
│   │   ├── orchestration/
│   │   │   ├── orchestrator.py
│   │   │   ├── pipeline_engine.py
│   │   │   ├── pipeline_validator.py
│   │   │   ├── pipeline_scheduler.py
│   │   │   ├── execution_context.py
│   │   │   ├── dependency_resolver.py
│   │   │   └── resource_manager.py
│   │   │
│   │   ├── pipelines/
│   │   │   ├── pipeline_loader.py
│   │   │   ├── pipeline_templates.py
│   │   │   ├── default_inspection.yaml
│   │   │   └── industry_templates/
│   │   │       ├── automotive.yaml
│   │   │       ├── electronics.yaml
│   │   │       └── metal_manufacturing.yaml
│   │   │
│   │   ├── training/
│   │   │   ├── training_manager.py
│   │   │   ├── training_scheduler.py
│   │   │   ├── training_config.py
│   │   │   ├── dataset_analyzer.py
│   │   │   ├── dataset_validator.py
│   │   │   ├── dataset_splitter.py
│   │   │   ├── experiment_tracker.py
│   │   │   ├── checkpoint_manager.py
│   │   │   ├── early_stopping.py
│   │   │   ├── trainers/
│   │   │   │   ├── base_trainer.py
│   │   │   │   ├── efficientad_trainer.py
│   │   │   │   ├── yolo_trainer.py
│   │   │   │   ├── mobilenet_trainer.py
│   │   │   │   ├── patchcore_trainer.py
│   │   │   │   └── severity_trainer.py
│   │   │   └── strategies/
│   │   │       ├── strategy_selector.py
│   │   │       ├── fine_tuning.py
│   │   │       ├── feature_bank.py
│   │   │       └── calibration_training.py
│   │   │
│   │   ├── evaluation/
│   │   │   ├── evaluation_engine.py
│   │   │   ├── classification_metrics.py
│   │   │   ├── detection_metrics.py
│   │   │   ├── segmentation_metrics.py
│   │   │   ├── anomaly_metrics.py
│   │   │   ├── calibration_metrics.py
│   │   │   └── model_comparator.py
│   │   │
│   │   ├── fusion/
│   │   │   ├── result_fusion.py
│   │   │   ├── score_aggregator.py
│   │   │   ├── severity_aggregator.py
│   │   │   ├── confidence_aggregator.py
│   │   │   └── quality_score.py
│   │   │
│   │   ├── services/
│   │   │   ├── inspection_service.py
│   │   │   ├── dataset_service.py
│   │   │   ├── training_service.py
│   │   │   ├── model_service.py
│   │   │   ├── pipeline_service.py
│   │   │   ├── report_service.py
│   │   │   └── feedback_service.py
│   │   │
│   │   ├── storage/
│   │   │   ├── file_storage.py
│   │   │   ├── model_storage.py
│   │   │   ├── dataset_storage.py
│   │   │   └── artifact_storage.py
│   │   │
│   │   ├── reporting/
│   │   │   ├── report_generator.py
│   │   │   ├── json_report.py
│   │   │   └── pdf_report.py
│   │   │
│   │   └── feedback/
│   │       ├── feedback_manager.py
│   │       ├── label_verification.py
│   │       └── retraining_queue.py
│   │
│   ├── migrations/
│   │   └── versions/
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       │   ├── test_model_registry.py
│       │   ├── test_preprocessing.py
│       │   ├── test_pipeline_engine.py
│       │   ├── test_result_fusion.py
│       │   └── test_dataset_validator.py
│       ├── integration/
│       │   ├── test_inspection_flow.py
│       │   ├── test_training_flow.py
│       │   └── test_api.py
│       └── fixtures/
│           └── sample_data.py
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   ├── client.js
│       │   ├── inspections.js
│       │   ├── models.js
│       │   ├── datasets.js
│       │   ├── training.js
│       │   └── pipelines.js
│       ├── components/
│       │   ├── common/
│       │   ├── dashboard/
│       │   ├── inspection/
│       │   ├── model_management/
│       │   ├── dataset/
│       │   ├── training/
│       │   ├── pipeline_builder/
│       │   └── reports/
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── Inspections.jsx
│       │   ├── InspectionDetails.jsx
│       │   ├── Models.jsx
│       │   ├── Datasets.jsx
│       │   ├── Training.jsx
│       │   ├── Pipelines.jsx
│       │   ├── Analytics.jsx
│       │   └── Settings.jsx
│       ├── hooks/
│       ├── context/
│       ├── utils/
│       ├── styles/
│       └── assets/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── train/
│   ├── validation/
│   ├── test/
│   └── README.md
│
├── artifacts/
│   ├── pretrained/
│   ├── trained/
│   ├── checkpoints/
│   ├── feature_banks/
│   ├── calibration/
│   └── evaluations/
│
├── storage/
│   ├── uploads/
│   ├── inspection_results/
│   ├── reports/
│   └── temporary/
│
├── configs/
│   ├── app.yaml
│   ├── hardware.yaml
│   ├── training.yaml
│   ├── inference.yaml
│   └── logging.yaml
│
├── scripts/
│   ├── setup_windows.bat
│   ├── setup_linux.sh
│   ├── download_models.py
│   ├── initialize_database.py
│   ├── seed_database.py
│   ├── train_model.py
│   ├── run_inspection.py
│   ├── benchmark_hardware.py
│   └── verify_installation.py
│
├── deployment/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
│
└── .github/
    └── workflows/
        ├── backend-tests.yml
        └── frontend-tests.yml
```

------------------------------------------------------------------------

## 5. Subsystem responsibilities

### 5.1 API layer --- `backend/app/api/`

The API layer receives HTTP requests, validates inputs, calls services,
and returns response schemas. It must not contain model inference or
training implementation.

  File               Responsibility
  ------------------ -------------------------------------------
  `router.py`        Registers versioned API routers
  `inspections.py`   Create and retrieve inspections
  `models.py`        List models, versions, and model status
  `training.py`      Start, monitor, cancel training jobs
  `datasets.py`      Upload, inspect, and manage datasets
  `pipelines.py`     Create, validate, and execute pipelines
  `industries.py`    Manage industry/product configuration
  `analytics.py`     Inspection statistics and trends
  `feedback.py`      Submit human review and labels
  `health.py`        API, database, and resource health checks

### 5.2 Core --- `backend/app/core/`

Contains cross-cutting application concerns:

-   `config.py`: loads environment variables and application settings.
-   `logging.py`: structured logging configuration.
-   `exceptions.py`: shared application exception types.
-   `security.py`: authentication and authorization helpers when needed.
-   `constants.py`: shared constants and enumerations.

### 5.3 Schemas --- `backend/app/schemas/`

Pydantic schemas define stable contracts between API, services, pipeline
nodes, and model adapters.

Use explicit schema versions when output formats change. Do not pass
arbitrary model-specific Python objects between subsystems.

Suggested common inspection result:

``` json
{
  "inspection_id": "inspection-001",
  "manufacturer_id": "manufacturer-001",
  "product_id": "product-001",
  "status": "completed",
  "anomaly_score": 0.91,
  "quality_score": 72.5,
  "defects": [
    {
      "defect_id": "defect-001",
      "type": "surface_crack",
      "confidence": 0.94,
      "severity": "high",
      "bbox": [120, 80, 240, 190],
      "mask_reference": null
    }
  ],
  "models_used": [
    {
      "model_id": "efficientad",
      "version": "1.0.0"
    }
  ],
  "warnings": []
}
```

This is an illustrative contract. Define exact coordinate conventions,
score ranges, nullability, units, and confidence semantics in the actual
Pydantic schemas.

### 5.4 Database --- `backend/app/database/`

SQLite stores application metadata and relationships, not large image
files or model weights.

Recommended entities:

  Entity         Purpose
  -------------- --------------------------------------------------
  Manufacturer   Organization using CLOCKIT
  Industry       Manufacturing domain
  Product        Product or component being inspected
  Dataset        Dataset metadata, ownership, format, and version
  Inspection     One inspection execution
  TrainingJob    Training status and configuration
  ModelVersion   Registered model artifact and metrics
  Pipeline       Saved inspection workflow
  Feedback       Human-reviewed prediction or label

Use repository classes to isolate database queries from services. Use
Alembic migrations so schema changes are reproducible.

### 5.5 Model subsystem --- `backend/app/models/`

Every model implementation must be wrapped in a common adapter. The rest
of CLOCKIT should not need to know whether the underlying model is
EfficientAD, YOLO, MobileNet, or a custom manufacturer model.

Suggested interface:

``` python
from abc import ABC, abstractmethod
from typing import Any


class BaseModel(ABC):

    @abstractmethod
    def load(self, artifact_path: str, device: str) -> None:
        """Load weights and initialize the model."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, input_data: Any) -> dict:
        """Run inference and return a standardized result."""
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        """Release model resources where possible."""
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self) -> dict:
        """Return model identity, version, task, and capabilities."""
        raise NotImplementedError
```

The exact interface may be refined to use typed input/output schemas,
but all adapters must obey the same contract.

Model-specific directories:

  -----------------------------------------------------------------------
  Directory                           Role
  ----------------------------------- -----------------------------------
  `anomaly_detection/efficientad/`    Learns normal product appearance
                                      and produces anomaly scores/maps

  `anomaly_detection/patchcore/`      Feature-memory-based anomaly
                                      detection

  `localization/yolo_seg/`            Detects and segments annotated
                                      defect classes

  `classification/mobilenet/`         Classifies defect crops or images

  `severity/`                         Predicts severity from labeled
                                      examples or engineered measurements

  `confidence/`                       Calibrates prediction confidence
                                      using held-out data
  -----------------------------------------------------------------------

Keep model source code separate from model weights. Weights belong in
`artifacts/`, not inside the source directories.

### 5.6 Preprocessing --- `backend/app/preprocessing/`

Responsibilities:

-   Validate file type, dimensions, color mode, and image readability.
-   Normalize image representation.
-   Resize according to each model's expected input.
-   Apply training-only augmentation.
-   Tile large images when supported by the model and pipeline.
-   Preserve coordinate transforms so predictions can be mapped back to
    original image coordinates.

Important: preprocessing must be model-aware. Do not apply one global
normalization or resizing rule to every model. Store preprocessing
configuration alongside each model version.

### 5.7 Orchestration --- `backend/app/orchestration/`

This is the central execution coordinator.

  -----------------------------------------------------------------------
  File                                Responsibility
  ----------------------------------- -----------------------------------
  `orchestrator.py`                   Coordinates one inspection request

  `pipeline_engine.py`                Executes pipeline nodes and
                                      dependencies

  `pipeline_validator.py`             Checks graph structure and
                                      input/output compatibility

  `pipeline_scheduler.py`             Determines execution order

  `execution_context.py`              Holds shared inspection data and
                                      intermediate outputs

  `dependency_resolver.py`            Resolves which outputs are required
                                      by each node

  `resource_manager.py`               Enforces CPU/GPU and memory
                                      policies
  -----------------------------------------------------------------------

The orchestrator must support:

-   Sequential nodes.
-   Parallel nodes when resources allow.
-   Conditional branches.
-   Optional model stages.
-   Failure handling and timeouts.
-   Model loading and unloading.
-   Per-node execution metadata.
-   Pipeline-level status and errors.

For the initial workstation, configure sequential GPU inference and one
active heavy training job. Parallel execution should be opt-in and
resource-checked.

### 5.8 Pipelines --- `backend/app/pipelines/`

Pipelines define *what* should run. The orchestration engine defines
*how* it runs.

Example YAML:

``` yaml
pipeline_id: default_industrial_inspection
version: 1

nodes:
  - id: anomaly_detection
    model_id: efficientad
    task: anomaly_detection
    depends_on: []

  - id: localization
    model_id: yolo11n_seg
    task: segmentation
    depends_on: [anomaly_detection]
    condition: anomaly_detected

  - id: classification
    model_id: mobilenet_v3
    task: classification
    depends_on: [localization]

  - id: severity
    model_id: severity_model
    task: severity_estimation
    depends_on: [localization, classification]

  - id: fusion
    task: result_fusion
    depends_on:
      - anomaly_detection
      - localization
      - classification
      - severity
```

This is a conceptual example. The pipeline validator must ensure that
model IDs exist, dependencies are valid, there are no cycles, and each
node receives compatible inputs. Conditions and node schemas must be
formally defined before execution.

Industry templates should be starting configurations, not rigid
hardcoded rules. Manufacturers must be able to customize pipelines
within validated constraints.

### 5.9 Training subsystem --- `backend/app/training/`

Training is independent from inference.

Core responsibilities:

1.  Inspect dataset structure and annotation formats.
2.  Validate labels, image integrity, and class distributions.
3.  Create reproducible train/validation/test splits.
4.  Select a model-specific training strategy.
5.  Enforce hardware resource limits.
6.  Start, monitor, pause, or cancel jobs where supported.
7.  Save checkpoints and logs.
8.  Evaluate on held-out data.
9.  Register candidate model versions.
10. Require approval before deployment.

Model-specific strategies:

  -----------------------------------------------------------------------
  Model                   Adaptation strategy     Data requirement
  ----------------------- ----------------------- -----------------------
  EfficientAD             Train on normal         Normal images, plus
                          reference images        anomalous validation
                                                  examples for evaluation

  YOLO segmentation       Fine-tune on annotated  Images with valid
                          instances/masks         segmentation labels

  MobileNetV3             Fine-tune classifier    Defect class labels

  PatchCore               Build category-specific Normal reference images
                          feature memory          

  Severity model          Train regression or     Human-assigned severity
                          classification head     labels

  Confidence calibration  Fit calibrator on       Validation labels and
                          held-out predictions    model predictions
  -----------------------------------------------------------------------

Do not force a trainer to run if its required labels are missing. For
example, YOLO segmentation cannot learn meaningful segmentation from
unannotated images alone.

### 5.10 Evaluation --- `backend/app/evaluation/`

Evaluation must be task-specific.

  -----------------------------------------------------------------------
  Task                                Useful metrics
  ----------------------------------- -----------------------------------
  Classification                      Precision, recall, F1, confusion
                                      matrix, per-class metrics

  Object detection                    mAP, precision, recall

  Segmentation                        IoU, Dice, mask AP

  Anomaly detection                   Image AUROC, pixel AUROC, AUPRO
                                      where appropriate

  Severity                            MAE, RMSE, class-wise recall

  Confidence                          Expected calibration error,
                                      reliability diagrams, Brier score
                                      where appropriate
  -----------------------------------------------------------------------

Do not use one generic accuracy number to approve every model. Compare
candidate and currently deployed models on the same held-out evaluation
set. Track dataset version, evaluation configuration, and metrics.

### 5.11 Fusion --- `backend/app/fusion/`

The fusion subsystem combines outputs from different models into an
inspection-level result.

Responsibilities:

-   Associate detections and segmentation regions where appropriate.
-   Combine anomaly evidence with localization and classification
    outputs.
-   Aggregate severity using documented business rules or a trained
    model.
-   Report calibrated confidence without treating unrelated model scores
    as directly comparable.
-   Calculate a quality score using a documented, configurable policy.
-   Preserve raw model outputs for traceability.

**Important:** Do not blindly average anomaly scores, class
probabilities, severity values, and confidence values. They represent
different quantities. Normalize or calibrate them only where
mathematically justified, and document the scoring policy. Keep the raw
outputs available in the final record.

### 5.12 Services --- `backend/app/services/`

Services implement application use cases and coordinate repositories,
model orchestration, storage, and reporting.

Examples:

-   `inspection_service.py`: create and execute inspections.
-   `dataset_service.py`: upload and validate datasets.
-   `training_service.py`: create and manage training jobs.
-   `model_service.py`: register, inspect, and activate model versions.
-   `pipeline_service.py`: create, validate, and execute pipelines.
-   `report_service.py`: create reports.
-   `feedback_service.py`: store reviewed predictions.

Services should not duplicate API validation or contain model-specific
inference code.

### 5.13 Storage and artifacts

Use different locations for different kinds of data:

  -----------------------------------------------------------------------
  Location                            Content
  ----------------------------------- -----------------------------------
  `data/raw/`                         Original datasets

  `data/processed/`                   Validated/transformed dataset
                                      copies or manifests

  `data/train/`                       Training split references or
                                      prepared data

  `data/validation/`                  Validation split references or
                                      prepared data

  `data/test/`                        Held-out test split references or
                                      prepared data

  `artifacts/pretrained/`             Downloaded pretrained weights

  `artifacts/trained/`                Approved or candidate trained
                                      weights

  `artifacts/checkpoints/`            Resumable training checkpoints

  `artifacts/feature_banks/`          PatchCore or other feature memory
                                      artifacts

  `artifacts/calibration/`            Calibration parameters

  `artifacts/evaluations/`            Evaluation outputs

  `storage/uploads/`                  User-uploaded files

  `storage/inspection_results/`       Inspection output files

  `storage/reports/`                  Generated reports

  `storage/temporary/`                Temporary files, cleaned by
                                      retention policy
  -----------------------------------------------------------------------

Database records should store paths or object keys and metadata, not
image bytes or large model weights.

### 5.14 Feedback subsystem

Human feedback should be explicitly reviewed and tracked.

Store:

-   Original prediction.
-   Human-corrected label or severity.
-   Reviewer and timestamp where identity tracking is enabled.
-   Image/dataset reference.
-   Model version that produced the prediction.
-   Review status.
-   Whether the feedback is approved for future training.

Never automatically train on every model prediction. Incorrect
pseudo-labels can reinforce model errors. Only verified, appropriately
permissioned feedback should enter a training dataset.

### 5.15 Frontend

The frontend is a management application, not just an image-upload page.

Suggested pages:

  -----------------------------------------------------------------------
  Page                                Purpose
  ----------------------------------- -----------------------------------
  Dashboard                           Inspection overview and operational
                                      metrics

  Inspections                         Search and review inspection
                                      records

  Inspection Details                  Image overlays, defects, scores,
                                      and model outputs

  Models                              Model catalog, versions, status,
                                      and metrics

  Datasets                            Upload, validation, and dataset
                                      management

  Training                            Configure and monitor training jobs

  Pipelines                           Configure industry-specific
                                      inspection workflows

  Analytics                           Trends and quality metrics

  Settings                            Manufacturer, product, and
                                      application configuration
  -----------------------------------------------------------------------

Use `frontend/src/api/` as the only normal interface for backend HTTP
calls. Keep API calls out of presentation components where practical.

------------------------------------------------------------------------

## 6. Model selection for the first prototype

Start with a small, complementary model set.

  ---------------------------------------------------------------------------
  Capability              Initial choice              Why
  ----------------------- --------------------------- -----------------------
  Anomaly detection       EfficientAD                 Designed for industrial
                                                      anomaly detection

  Optional anomaly        PatchCore                   Useful for comparison
  baseline                                            and category-specific
                                                      memory

  Localization            YOLO11n-seg                 Lightweight
                                                      segmentation model

  Classification          MobileNetV3 Small           Efficient classifier

  Severity                Small                       Can be trained on
                          regression/classification   verified severity
                          model                       labels

  Confidence              Temperature scaling         Lightweight post-hoc
                          initially                   calibration
  ---------------------------------------------------------------------------

Pretrained models are starting points, not automatically accurate
industrial defect detectors. COCO-pretrained YOLO weights and
ImageNet-pretrained MobileNet weights need appropriate industrial
fine-tuning for target defects. EfficientAD and PatchCore also require
product/category-specific reference data and correct training
procedures.

Verify model licenses and the licenses of datasets before distributing
CLOCKIT or its bundled artifacts.

------------------------------------------------------------------------

## 7. Hardware-aware execution plan

### Initial workstation

-   RAM: 16 GB.
-   CPU: 4 cores.
-   GPU: NVIDIA RTX 3050.
-   GPU VRAM: confirm exact 4 GB, 6 GB, or 8 GB variant.
-   Execution: local.

### Initial resource policy

  -----------------------------------------------------------------------
  Setting                             Starting policy
  ----------------------------------- -----------------------------------
  Concurrent heavy training jobs      1

  Concurrent inspection jobs          1

  GPU inference                       Sequential by default

  Batch size                          1 for initial inference

  Image size                          Model-specific, begin around
                                      256--512 pixels where supported

  Data-loader workers                 0--2

  Precision                           FP16 only where supported and
                                      validated

  Model loading                       Lazy/on demand

  GPU memory                          Monitor before loading each model

  Large images                        Tile or resize with coordinate
                                      mapping

  Checkpoints                         Save periodically to disk
  -----------------------------------------------------------------------

These are starting settings, not guarantees. Actual requirements depend
on GPU VRAM, model architecture, input dimensions, intermediate
activations, framework versions, and whether training or inference is
running.

Do not load all models onto the GPU at startup. Use the resource manager
to load a model for its stage, execute inference, release references and
temporary tensors, and unload it when appropriate. Verify memory usage
rather than assuming `empty_cache()` frees memory occupied by live
tensors.

Training and inference should not compete for the GPU in the initial
prototype. Pause or queue training while a live inspection is running.

------------------------------------------------------------------------

## 8. API design

Use a versioned API prefix:

``` text
/api/v1
```

Suggested endpoints:

  Method   Endpoint                       Purpose
  -------- ------------------------------ --------------------------
  GET      `/health`                      Health status
  POST     `/inspections`                 Submit an inspection
  GET      `/inspections`                 List inspections
  GET      `/inspections/{id}`            Get inspection details
  POST     `/datasets`                    Upload/register dataset
  GET      `/datasets/{id}`               Dataset details
  POST     `/datasets/{id}/validate`      Validate dataset
  GET      `/models`                      List registered models
  GET      `/models/{id}`                 Model details
  POST     `/training/jobs`               Start training
  GET      `/training/jobs/{id}`          Training status
  POST     `/training/jobs/{id}/cancel`   Request cancellation
  GET      `/pipelines`                   List pipelines
  POST     `/pipelines`                   Create pipeline
  POST     `/pipelines/{id}/validate`     Validate pipeline
  POST     `/pipelines/{id}/run`          Execute pipeline
  POST     `/feedback`                    Submit reviewed feedback
  GET      `/analytics/overview`          Dashboard analytics

Long-running training and inspection operations should return job IDs
and status endpoints. Do not keep an HTTP request open for the entire
duration of a long training job.

For a local prototype, a persistent job table plus a controlled
background worker can be enough. If the app later needs reliable
distributed jobs, introduce a dedicated queue and worker architecture
then.

------------------------------------------------------------------------

## 9. Dataset format and validation

CLOCKIT should accept a documented set of dataset formats rather than
claiming to support every arbitrary folder structure.

### Initial dataset modes

1.  **Normal-only anomaly detection**
    -   Normal/reference images.
    -   Optional anomalous validation/test images.
    -   Optional pixel masks for localization evaluation.
2.  **Classification**
    -   Class folders or a CSV manifest mapping image paths to labels.
3.  **Object detection**
    -   Images and bounding-box annotations in a supported format.
4.  **Segmentation**
    -   Images and valid instance/pixel masks in a supported format.
5.  **Severity estimation**
    -   Images or defect-region references with human-assigned severity
        labels or numeric measurements.

### Dataset validation checks

-   File readability and supported formats.
-   Duplicate and near-duplicate detection where feasible.
-   Missing or invalid labels.
-   Class imbalance.
-   Image dimensions and color modes.
-   Annotation bounds and mask alignment.
-   Train/validation/test leakage.
-   Product, batch, or physical-part grouping where available.
-   Dataset license and usage permissions.
-   Manufacturer ownership and access boundaries.

Keep a dataset manifest with file checksums, labels, split assignment,
source, and dataset version. Preserve original raw data.

------------------------------------------------------------------------

## 10. Model registry and artifact versioning

A model registry entry should include:

``` yaml
model_id: efficientad-metal-surface
version: 1.0.0
task: anomaly_detection
framework: pytorch
artifact_path: artifacts/trained/efficientad-metal-surface/1.0.0/
manufacturer_id: manufacturer-001
product_category: metal_surface
dataset_version: metal-dataset-001-v1
preprocessing:
  image_size: [256, 256]
  color_mode: RGB
evaluation:
  image_auroc: null
  pixel_auroc: null
status: candidate
created_at: "ISO-8601 timestamp"
```

The example values are placeholders. Real metrics must come from
evaluation, not be filled with assumed values.

Suggested model lifecycle:

``` text
Downloaded / Imported
       |
       v
Registered
       |
       v
Candidate
       |
       v
Evaluated
       |
       +---- Rejected
       |
       v
Approved
       |
       v
Active
       |
       v
Archived / Rolled Back
```

Never replace an active model artifact in place. Register a new
immutable version, evaluate it, and switch the active-version pointer
only after approval.

------------------------------------------------------------------------

## 11. Result fusion and quality score

The final inspection should preserve both detailed model outputs and a
unified summary.

Recommended output fields:

-   Inspection ID and timestamp.
-   Manufacturer/product identifiers.
-   Pipeline ID and version.
-   Input image reference and checksum.
-   Model IDs and versions used.
-   Anomaly score and anomaly-map reference.
-   Defect type and classification probabilities.
-   Bounding boxes and segmentation-mask references.
-   Severity and its source.
-   Calibrated confidence and calibration version.
-   Unified quality score and scoring-policy version.
-   Warnings, errors, and skipped stages.
-   Execution times and hardware metadata.

Do not conflate: - Anomaly score: evidence that an input differs from
learned normality. - Class probability: model estimate over defined
classes. - Confidence: a reliability estimate that should be calibrated
and validated. - Severity: impact or seriousness according to a defined
labeling/business policy. - Quality score: a business-level aggregation
with an explicit formula.

A quality score should be configurable by industry/product and should
expose its component contributions. Do not represent an arbitrary
weighted score as a scientifically calibrated probability.

------------------------------------------------------------------------

## 12. Security, privacy, and reliability

Even a hackathon prototype should establish sensible boundaries.

-   Validate uploads and enforce file-size limits.
-   Generate server-side filenames; do not trust user-provided paths.
-   Prevent path traversal and unsafe archive extraction.
-   Restrict access to manufacturer-owned datasets, models, and
    inspections.
-   Keep secrets in environment variables, never source control.
-   Avoid logging raw sensitive image content.
-   Record model version and pipeline version for every inspection.
-   Keep raw uploaded files immutable where practical.
-   Use explicit retention and deletion policies.
-   Validate YAML pipeline configuration before execution.
-   Do not execute arbitrary Python supplied by a manufacturer.
-   Use allowlisted model adapters and pipeline node types.
-   Handle failed jobs without corrupting active model versions.
-   Back up the SQLite database and important metadata.
-   Record training dataset provenance and model artifact checksums.

For multi-tenant production use, add robust authentication,
authorization, tenant isolation, audit logs, and a production
database/storage solution before onboarding real manufacturers.

------------------------------------------------------------------------

## 13. Git and `.gitignore`

Do not commit large datasets, trained weights, checkpoints, environment
files, or generated user uploads.

Suggested `.gitignore`:

``` gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Environment and secrets
.env
.env.*
!.env.example

# Frontend
node_modules/
dist/

# Model weights and engines
*.pt
*.pth
*.onnx
*.ckpt
*.safetensors
*.engine

# Local datasets
data/raw/*
data/processed/*
data/train/*
data/validation/*
data/test/*

# Generated artifacts
artifacts/pretrained/*
artifacts/trained/*
artifacts/checkpoints/*
artifacts/feature_banks/*
artifacts/calibration/*
artifacts/evaluations/*

# User files and runtime output
storage/uploads/*
storage/inspection_results/*
storage/reports/*
storage/temporary/*
*.log
logs/

# Local databases
*.db
*.sqlite
*.sqlite3

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
```

Keep placeholder `.gitkeep` files only when an otherwise-empty runtime
directory needs to exist in a fresh checkout. Keep documentation,
configuration templates, manifests, small test fixtures, and code in
Git.

------------------------------------------------------------------------

## 14. Development roadmap

Build a working vertical slice at each phase. Do not implement all
folders before testing the end-to-end path.

### Phase 1 --- Foundation

Implement:

-   FastAPI application startup.
-   Configuration and logging.
-   Pydantic schemas.
-   SQLite connection and initial tables.
-   Health endpoint.
-   Dataset upload endpoint.
-   Basic React application and API client.

**Exit criteria:** Frontend can upload an image; backend validates it,
stores it, and returns a record ID.

### Phase 2 --- First model

Implement:

-   `BaseModel` contract.
-   One model adapter.
-   Model loader and registry.
-   Image preprocessing.
-   Single-image inference.
-   Standardized output schema.

**Exit criteria:** One image can be processed by one model and its
result is persisted.

### Phase 3 --- Orchestration

Implement:

-   Execution context.
-   Pipeline schema and validator.
-   Sequential pipeline engine.
-   Resource manager.
-   Failure and timeout handling.
-   Model load/unload behavior.

**Exit criteria:** A pipeline can execute two compatible stages and
return a traceable combined result.

### Phase 4 --- Multi-model inspection

Add:

-   Localization model.
-   Classification model.
-   Severity estimation.
-   Confidence calibration.
-   Result fusion.
-   Inspection report.

**Exit criteria:** One inspection produces a unified report with source
model versions and intermediate outputs.

### Phase 5 --- Custom datasets and training

Add:

-   Dataset analyzer and validator.
-   Dataset manifests and versioning.
-   One trainer at a time.
-   Checkpoints and experiment tracking.
-   Held-out evaluation.
-   Candidate model registration.

**Exit criteria:** A manufacturer dataset can train a candidate model,
evaluate it, and register a new version without replacing the active
model.

### Phase 6 --- Management interface

Add:

-   Inspection history and detail views.
-   Model catalog and version management.
-   Dataset management.
-   Training job monitoring.
-   Pipeline configuration UI.
-   Analytics and reports.

**Exit criteria:** A user can manage the main inspection lifecycle
through the frontend.

### Phase 7 --- Feedback and hardening

Add:

-   Human review.
-   Verified feedback storage.
-   Retraining queue.
-   Model comparison and rollback.
-   Resource monitoring.
-   Security and reliability checks.

**Exit criteria:** Feedback can be reviewed, used in a controlled new
training run, evaluated, and approved for deployment.

------------------------------------------------------------------------

## 15. Initial dependency groups

Pin tested versions in the actual dependency files after checking
compatibility with the chosen Python, CUDA, and operating-system
environment.

### Backend/runtime

-   `fastapi`
-   `uvicorn[standard]`
-   `pydantic`
-   `pydantic-settings`
-   `python-multipart`
-   `sqlalchemy`
-   `alembic`
-   `pyyaml`
-   `numpy`
-   `pillow`
-   `opencv-python`
-   `python-dotenv`

### AI/inference/training

-   `torch`
-   `torchvision`
-   `ultralytics`
-   `anomalib`
-   `scikit-learn`
-   `scipy`
-   `tqdm`
-   `matplotlib`

### Development/testing

-   `pytest`
-   `httpx`
-   `ruff`
-   `mypy`

### Frontend

-   `react`
-   `react-dom`
-   `vite`
-   `react-router-dom`
-   `axios` (or native `fetch`, choose one)
-   A charting library if needed
-   A component/icon library if needed

Do not blindly install every optional package at once. PyTorch/CUDA
wheels must match the supported driver and installation channel.
Anomalib and Ultralytics versions should be pinned and tested together.
Avoid installing multiple OpenCV wheel variants into the same
environment.

------------------------------------------------------------------------

## 16. Initial configuration files

### `configs/hardware.yaml`

``` yaml
execution:
  device: auto
  inference_mode: sequential
  max_concurrent_inspections: 1
  max_concurrent_training_jobs: 1

gpu:
  enabled: true
  allow_fp16: true
  reserve_vram_mb: 768

cpu:
  dataloader_workers: 2

memory:
  lazy_model_loading: true
  unload_after_stage: true
  max_image_pixels: 25000000
```

These are starting policies, not guaranteed safe limits. Confirm actual
VRAM before setting the reserve and benchmark each model.

### `configs/inference.yaml`

``` yaml
defaults:
  batch_size: 1
  image_size: 512
  precision: auto
  fail_on_missing_required_stage: true

models:
  efficientad:
    enabled: true
  yolo11n_seg:
    enabled: true
  mobilenet_v3:
    enabled: true
  patchcore:
    enabled: false
```

Each model adapter must be able to override image size and preprocessing
according to its actual requirements.

### `configs/training.yaml`

``` yaml
training:
  max_concurrent_jobs: 1
  checkpoint_interval_epochs: 5
  save_best_checkpoint: true
  require_validation_split: true
  require_held_out_test_evaluation: true
  auto_deploy: false

resources:
  device: auto
  dataloader_workers: 1
  mixed_precision: true
```

### `.env.example`

``` dotenv
APP_NAME=CLOCKIT
APP_ENV=development
APP_DEBUG=true
API_V1_PREFIX=/api/v1

DATABASE_URL=sqlite:///./clockit.db

DATA_ROOT=./data
ARTIFACT_ROOT=./artifacts
STORAGE_ROOT=./storage

DEFAULT_DEVICE=auto
LOG_LEVEL=INFO
MAX_UPLOAD_MB=50
```

Never put real secrets in this file. The example is safe to commit;
`.env` is not.

------------------------------------------------------------------------

## 17. Definition of done for the first hackathon demo

The first credible demo should prove the complete product idea without
attempting every future feature.

1.  A user uploads a manufacturing image.
2.  CLOCKIT validates and stores it.
3.  A selected pipeline runs at least one anomaly detector.
4.  A localization stage runs when appropriate.
5.  Outputs are converted into a standardized schema.
6.  Fusion creates a traceable inspection summary.
7.  The result is saved and displayed in the frontend.
8.  The user can upload a small labeled/normal dataset.
9.  At least one supported custom-training workflow can run.
10. The candidate model is evaluated and registered as a new version.
11. The user can see which model versions were used.
12. A failed training or inference job does not corrupt existing model
    versions.

A smaller, reliable end-to-end demonstration is stronger than a large
dashboard full of nonfunctional modules.

------------------------------------------------------------------------

## 18. Final architecture rules

1.  Model adapters implement a shared interface.
2.  Models do not call other models directly.
3.  Pipelines declare dependencies and data contracts.
4.  The orchestrator controls execution and resources.
5.  Training never overwrites an active model.
6.  Every model version records its artifact, configuration, dataset
    provenance, and evaluation.
7.  Every inspection records its pipeline and model versions.
8.  Raw model outputs remain available for audit and debugging.
9.  Industry-specific behavior is configured wherever practical, not
    hardcoded into generic engine logic.
10. The initial implementation favors sequential execution and low
    memory use.
11. Dataset splits are reproducible and guard against leakage.
12. Confidence, anomaly score, severity, and quality score remain
    distinct concepts.
13. No model is automatically approved just because training completed.
14. New infrastructure is introduced only when a measured requirement
    justifies it.

------------------------------------------------------------------------

## 19. Immediate next steps

Start implementation in this order:

1.  Create the repository and top-level folders.
2.  Add Python project configuration and install a compatible
    environment.
3.  Implement FastAPI startup, settings, logging, and health check.
4.  Create Pydantic contracts for model input/output and inspection
    results.
5.  Implement SQLite connection and the first database tables.
6.  Implement `BaseModel`, one adapter, and `ModelRegistry`.
7.  Load one pretrained model and run one image.
8.  Persist the inspection result.
9.  Add the sequential pipeline engine.
10. Add the next model only after the first end-to-end path is reliable.

**Architecture baseline:** This document is the source of truth for the
initial CLOCKIT repository. If the architecture changes, update this
document and the relevant subsystem guides rather than allowing the
codebase and documentation to drift apart.
