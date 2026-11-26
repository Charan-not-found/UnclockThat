# CLOCKIT Model Library --- Codex Implementation Guide

## Objective

Implement a self-contained model library for CLOCKIT. Every model lives
in its own folder under `models/`, with model weights/assets, a
human-readable `model.txt`, and an optional `config.yaml`. Discover
models automatically, validate files and metadata, expose a catalogue to
the UI, and load weights only on demand.

## Directory structure

``` text
CLOCKIT/
├── models/
│   ├── efficientad/
│   │   ├── model/
│   │   │   └── pretrained_teacher_medium.pth
│   │   ├── model.txt
│   │   └── config.yaml
│   ├── yolov8/
│   │   ├── model/
│   │   │   └── best.pt
│   │   ├── model.txt
│   │   └── config.yaml
│   └── sam/
│       ├── model/
│       │   └── sam_vit_b.pth
│       ├── model.txt
│       └── config.yaml
└── ...
```

Adapt existing paths rather than creating duplicate model directories.
Use stable, lowercase, filesystem-safe model IDs. Keep original weight
filenames. `model/` may contain multiple files. Do not place datasets,
logs, results, or feedback in the weights folder.

## `model.txt` format

Use UTF-8 and a simple `key: value` format with multiline bullet lists.

Example:

``` text
Name: EfficientAD
Version: 1.0
Category: Anomaly Detection
Description: Learns normal product appearance and identifies unusual visual patterns.

Capabilities:
- Surface anomaly detection
- Scratch-like appearance anomaly detection
- Dent-like appearance anomaly detection
- Texture anomaly detection

Input Type: Image
Input Size: 256x256
Output Types:
- Anomaly score
- Anomaly heatmap

Training Mode: Normal images
Custom Training: Supported
Framework: PyTorch
Model Format: PTH

Orientation Independent: Not guaranteed
Geometry Analysis: No

Limitations:
- Detects visual anomalies; does not directly measure physical dimensions.
- Performance depends on image quality, lighting, and representative normal training data.
```

### Required fields

-   `Name`
-   `Category`
-   `Description`
-   `Framework`
-   `Model Format`
-   `Input Type`
-   `Capabilities`
-   `Limitations`

Optional fields may include `Version`, `Input Size`, `Output Types`,
`Training Mode`, `Custom Training`, `Orientation Independent`,
`Geometry Analysis`, `Tags`, `Documentation`, and `License`.

Parser requirements: - Support scalar fields and multiline bullet
lists. - Ignore blank lines and lines beginning with `#`. - Trim
whitespace and preserve list order. - Detect malformed metadata and
duplicate required fields. - Do not guess missing capabilities or
limitations. - Invalid metadata must make that model unavailable with a
useful reason, not crash the registry. - Never execute metadata or use
`eval`; implement a small parser for this format.

## `config.yaml`

Optional technical/runtime settings, not user-facing description.

``` yaml
loader:
  type: efficientad
  entrypoint: clockit.models.efficientad:load_model

runtime:
  device: auto
  precision: auto

files:
  weights:
    - model/pretrained_teacher_medium.pth

preprocessing:
  color_mode: RGB
  resize:
    width: 256
    height: 256
```

Do not assume every architecture uses the same loader. Do not import
arbitrary module paths from metadata unless explicitly
trusted/allowlisted. Validate paths and reject traversal (such as
`../../`). Avoid machine-specific absolute paths and secrets. If config
is missing, use safe defaults or mark the model as requiring
configuration.

## Backend architecture

### ModelRegistry

Responsible for scanning the model root, discovering folders, parsing
metadata, reading optional config, validating required files, reporting
status/errors, and refreshing the catalogue. Scanning must not load
weights.

Suggested API:

``` python
class ModelRegistry:
    def scan(self) -> list[ModelInfo]: ...
    def get(self, model_id: str) -> ModelInfo | None: ...
    def refresh(self) -> list[ModelInfo]: ...
```

### ModelLoader

Load selected models through trusted architecture-specific adapters.
Choose device safely, cache loaded instances, support explicit unload,
and return actionable errors.

``` python
class ModelLoader:
    def load(self, model_id: str, device: str = "auto"): ...
    def unload(self, model_id: str) -> None: ...
    def get_loaded(self, model_id: str): ...
```

Do not build one giant loader based on fragile extension/filename
checks. Use adapters per architecture.

## API/UI catalogue

Expose stable model metadata without leaking absolute local filesystem
paths. Example response:

``` json
{
  "id": "efficientad",
  "name": "EfficientAD",
  "category": "Anomaly Detection",
  "description": "Learns normal appearance and identifies unusual visual patterns.",
  "capabilities": ["Surface anomaly detection"],
  "limitations": ["Does not directly measure physical dimensions"],
  "framework": "PyTorch",
  "model_format": "PTH",
  "input_type": "Image",
  "status": "available",
  "loaded": false,
  "validation_errors": []
}
```

Adapt endpoint names and conventions to the existing project: -
`GET /api/models` --- list models. - `GET /api/models/{model_id}` ---
metadata for one model. - `POST /api/models/refresh` --- rescan. -
`POST /api/models/{model_id}/load` --- load on demand. -
`POST /api/models/{model_id}/unload` --- unload.

Use existing API security and local-app conventions.

UI must use registry data rather than a hardcoded list. Show name,
category, description, capabilities, limitations, availability, and
loaded status. Allow metadata inspection. Distinguish: - **Available:**
metadata and required files validate. - **Unavailable:** validation
error, missing files, unsupported loader, etc. - **Loaded:** weights are
currently resident.

## Scanner-unit integration

-   Store stable `model_id` values, not absolute paths.
-   Store scanner/model parameters separately from model metadata.
-   Validate availability when adding a model.
-   Load only when the scanner unit is activated or inference begins.
-   Reuse loaded instances where safe.
-   Surface structured errors.
-   Refreshing the registry must not silently alter existing
    scanner-unit selections.

## Performance and resource use

Prototype target may have 16 GB RAM, an RTX 3050, and a 4-core CPU: -
Never load every model on startup. - Avoid unnecessarily keeping
multiple large models on GPU. - Support CPU fallback where the adapter
permits. - Log selected device and diagnostics. - Avoid concurrent heavy
inference by default. - Handle CUDA out-of-memory gracefully; do not
assume every model fits.

## Migration

1.  Inspect repository, existing weights, loaders, and references.
2.  Identify each weight's architecture and loader (do not infer solely
    from extension).
3.  Create new folders and metadata.
4.  Move/copy assets only when safe; preserve originals until
    verification.
5.  Update references to use registry/stable IDs.
6.  Smoke-test every migrated model.
7.  Remove obsolete duplicates only after confirming references are
    gone.

## Tests

Registry tests should cover: - Discovery and scalar/list metadata
parsing. - Blank lines and comments. - Missing required fields and
malformed/duplicate fields. - Missing model directory, weights, or
optional config. - Continuing scan when a model is invalid. - No weight
loading during discovery.

Security tests: - Path traversal rejected. - Metadata/config never
executed. - Absolute paths not leaked in API output.

Loader/API/UI tests: - Trusted adapter loads a model. - No redundant
duplicate loads. - Dependency, incompatible-weight, CPU fallback, CUDA
and unload handling. - Dynamic catalogue and unavailable-state
display. - Scanner unit stores stable model IDs.

Use temporary directories and mocked/small assets in tests. Avoid
downloads of large models.

## Logging/errors

Use existing logging. Log scan start/end, discovered IDs, validation
failures, load/unload, device, and failures. Avoid logging image
contents, secrets, or unnecessary absolute paths. Return actionable
errors such as: - `Missing weight file: model/weights.pth` -
`No trusted loader registered for model ID: example-model` -
`CUDA out of memory while loading model`

## Implementation order

1.  Inspect current repository and summarize model paths, loaders,
    framework, and API.
2.  Define metadata parser/schema.
3.  Implement registry and validation.
4.  Test registry.
5.  Implement trusted adapter registration.
6.  Implement lazy loading, caching, unloading.
7.  Add API endpoints following existing conventions.
8.  Connect UI model picker.
9.  Integrate stable IDs with scanner units.
10. Migrate existing assets and verify end-to-end.

Do not rewrite unrelated CLOCKIT components.

## Definition of done

-   Models are individually organized in folders.
-   Each has validated, human-readable metadata.
-   Optional runtime config is separate.
-   Automatic discovery works without hardcoding model names.
-   Invalid models do not crash scanning.
-   Weights load only on demand.
-   UI shows registry data.
-   Scanner units store stable IDs.
-   Existing inference pipelines remain functional.
-   Automated tests cover discovery, validation, path safety, and lazy
    loading.

## Instruction to Codex

**Inspect the existing repository first.** Do not blindly move files or
generate a new architecture before understanding the codebase. Report
the current structure and the smallest safe plan, then implement in
verifiable steps. Preserve working inference pipelines and avoid
unrelated refactors.
