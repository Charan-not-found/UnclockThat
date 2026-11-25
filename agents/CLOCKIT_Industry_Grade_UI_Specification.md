# CLOCKIT / PROMETHEUS-X
## Industry-Grade UI/UX Product and Implementation Specification

**Document type:** Product requirements, UX specification, frontend architecture and implementation contract  
**Reference date:** 25 November 2026  
**Audience:** Product, design, frontend, backend, AI/ML, QA and coding-agent teams  
**Status:** Target-state specification. Existing and planned capabilities are explicitly distinguished.

---

# 1. Product vision

CLOCKIT is a configurable industrial visual-inspection and quality-intelligence platform. It supports manufacturers across different industries through a shared platform with configurable products, defect taxonomies, datasets, models and inspection pipelines.

The platform combines:

- Manufacturer, facility, product and inspection-station management.
- Dataset ingestion, validation, preparation and versioning.
- Independently managed AI models.
- Configurable inspection pipelines.
- Anomaly detection, defect localization, severity estimation and confidence calibration.
- Explainable quality decisions and human review.
- Inspection history, analytics, reporting and traceability.
- Model training, evaluation, deployment, rollback and monitoring.

The interface must feel like mature industrial operations software: precise, calm, trustworthy, information-dense where useful, accessible and predictable. It must not resemble a generic AI dashboard filled with decorative charts, fake metrics or non-functional controls.

## 1.1 Core principle

**One common platform; configurable industry, product and inspection workflows.**

Do not attempt to solve every manufacturing problem with one universal model. The platform is shared, while data schemas, defect taxonomies, models, thresholds and pipelines are configurable for the relevant industry, product and inspection station.

## 1.2 Product outcomes

A user should be able to:

1. Configure their organization and manufacturing context.
2. Register products, production lines and inspection stations.
3. Import images and datasets with traceable provenance.
4. Select available models and create an inspection pipeline.
5. Run an inspection and see evidence, not just a score.
6. Understand why the system reached a decision.
7. Review uncertain or critical results.
8. Compare model versions and inspect model quality.
9. Track quality trends without misleading statistics.
10. Reproduce a historical inspection using the exact model and pipeline versions used at the time.

---

# 2. Existing implementation baseline

This section reflects the project information recorded in `completed.md` and the prior project discussion. It is not a claim that the target-state product is already complete.

## 2.1 Existing technology

### Backend
- Python and FastAPI.
- SQLAlchemy 2.0.
- SQLite database (`clockit.db`) initialized by the current application.
- Pydantic schemas.
- API prefix `/api/v1`.
- Existing health, inspection and model endpoints.
- Local files stored under `data/`, `artifacts/` and `storage/`.

### Frontend
- React 18.
- TypeScript.
- Vite 5.
- Tailwind CSS.
- React Router v6.
- Axios.
- Recharts.
- Lucide React.

### Existing database entities
- `manufacturer_profiles`
- `users`
- `model_configs`
- `pipeline_configs`
- `inspection_records`
- `anomaly_results`
- `severity_scores`

### Existing API routes
- `GET /api/v1/health`
- `GET /api/v1/inspections`
- `POST /api/v1/inspections`
- `POST /api/v1/inspections/{inspection_id}/confirm`
- `GET /api/v1/models`
- `PATCH /api/v1/models/{model_id}/toggle`

### Existing frontend pages
- Dashboard
- Inspection
- Inspection History
- Models
- Placeholder routes for Pipelines, Datasets, Training, Analytics and Settings

### Existing verification recorded
- Three backend tests passed.
- Frontend TypeScript/Vite production build completed successfully.

## 2.2 Important limitations to preserve honestly

The current inspection POST route was documented as using OpenCV Gaussian-blur, contrast and contour heuristics. This is not a trained industrial anomaly detector.

The actual AI subsystem, real model adapters, training pipeline, evaluation, model versioning, confidence calibration, orchestration and result fusion were documented as not yet implemented.

The models endpoint was documented as auto-seeding a default manufacturer and three placeholder model records when the model table is empty. Remove this behavior. A GET request must never create business records.

Authentication, role-based access, production-grade auditing, tenant isolation, real model inference and model training are not established as complete by the project notes.

The project team has since reported downloading these artifacts:
- `pretrained_teacher_small.pth`
- `pretrained_teacher_medium.pth`
- `yolo11n-seg.pt`

These downloads do not prove that adapters, trained product-specific models, evaluation or production deployment are complete. PatchCore remains a planned integration requiring a compatible implementation and product-specific memory bank.

**UI rule:** Never present planned functionality as live. Use honest states such as `Not configured`, `Not installed`, `Not trained`, `Unavailable`, `Queued`, `Running`, `Failed` or `Requires review`. Never fabricate manufacturers, inspections, model performance, inspection results or analytics.

---

# 3. Users, roles and permissions

The backend must enforce authorization. Hiding a button in the frontend is not security.

## 3.1 Roles

### Platform administrator
- Manages platform-level configuration and operational health.
- Can inspect system-wide resource and service status.
- Manages tenant provisioning if implemented.
- Must not casually access manufacturer inspection evidence without an authorized reason.

### Manufacturer administrator
- Manages their organization, facilities, users and permissions.
- Configures products, stations, datasets, models and pipelines.
- Reviews quality analytics and audit history.
- Controls model and pipeline activation within their tenant.

### Quality manager
- Reviews inspections, trends, severity and quality decisions.
- Configures review policies and defect taxonomies where authorized.
- Approves, rejects or escalates reviewed inspections.
- Exports reports.

### Inspection operator
- Runs inspections at authorized stations.
- Reviews evidence and submits decisions or notes.
- Cannot alter deployed model weights or platform configuration unless explicitly granted permission.

### ML / model engineer
- Registers model artifacts and configurations.
- Manages datasets, training, evaluation and model versions.
- Promotes or rolls back models only with required permissions.
- Cannot bypass manufacturer data isolation.

### Read-only auditor
- Views permitted inspections, reports, versions and audit records.
- Cannot mutate configuration or decisions.

## 3.2 Permission matrix

| Capability | Platform admin | Manufacturer admin | Quality manager | Operator | ML engineer | Auditor |
|---|---|---|---|---|---|---|
| View authorized dashboard | Yes | Yes | Yes | Limited | Yes | Read-only |
| Manage organization/users | Platform scope | Tenant scope | No | No | No | No |
| Manage products/stations | Support | Yes | Configurable | View | View | View |
| Upload datasets | Support | Yes | Optional | No | Yes | No |
| Train models | Support | Optional | No | No | Yes | No |
| Register model artifacts | Support | Optional | No | No | Yes | No |
| Build pipelines | Support | Yes | Optional | No | Yes | No |
| Run inspections | Support | Yes | Yes | Yes | Test scope | No |
| Review inspections | Support | Yes | Yes | Assigned scope | Test scope | Read-only |
| Promote/rollback models | Platform policy | Authorized | Approval policy | No | Authorized | No |
| View audit trail | Platform scope | Tenant scope | Tenant scope | Own actions | Tenant scope | Authorized scope |

---

# 4. Information architecture and navigation

Use a persistent left navigation sidebar, compact top bar and consistent content workspace. Support collapse on smaller desktop widths. Avoid deep, confusing nesting.

## 4.1 Primary navigation

1. **Overview**
   - Operations dashboard
   - System status (permission-dependent)

2. **Inspections**
   - New inspection
   - Inspection history
   - Review queue
   - Inspection stations

3. **Pipelines**
   - Pipeline library
   - Pipeline builder
   - Pipeline versions

4. **AI Models**
   - Model registry
   - Model details
   - Model versions
   - Evaluation
   - Deployment history

5. **Datasets**
   - Dataset library
   - Upload/import
   - Dataset details and versions
   - Annotation and defect taxonomy
   - Data quality

6. **Training**
   - Training jobs
   - New training job
   - Experiments
   - Evaluation reports

7. **Analytics**
   - Quality trends
   - Defect Pareto
   - Station/product comparisons
   - Model performance
   - Drift monitoring

8. **Reports**
   - Report library
   - Scheduled reports (only if implemented)
   - Export history

9. **Administration**
   - Organization
   - Facilities / production lines
   - Products
   - Users and roles
   - Audit log
   - Settings

Show navigation according to permissions and actual feature availability. Do not expose dead routes.

## 4.2 Global top bar

Include, where implemented:
- Organization / tenant selector for users with multiple organizations.
- Facility or production-line context selector.
- Global search for permitted products, inspections, datasets and models.
- Notifications for review tasks, training completion/failure and operational alerts.
- Help / documentation.
- User menu and session actions.

Do not add a search box or notification control that does nothing. Omit it until it has a real workflow.

---

# 5. Visual design system

## 5.1 Design direction

Use a restrained industrial software aesthetic:
- Neutral slate/graphite surfaces.
- Clear typography and hierarchy.
- One restrained primary accent for actions and selected navigation.
- Semantic colors for statuses and severity.
- Thin borders and consistent spacing.
- Minimal shadows.
- Dense but readable data tables.
- Large, high-contrast inspection evidence viewer.
- No decorative gradients behind every card.
- No excessive pill controls.
- No glassmorphism.
- No meaningless animated counters.
- No fake 3D industrial imagery.

## 5.2 Design tokens

Define tokens centrally using CSS variables or the existing Tailwind theme. Do not scatter arbitrary hex values through components.

Suggested tokens:
- `--color-bg`
- `--color-surface`
- `--color-surface-raised`
- `--color-border`
- `--color-border-strong`
- `--color-text`
- `--color-text-muted`
- `--color-primary`
- `--color-primary-hover`
- `--color-success`
- `--color-warning`
- `--color-danger`
- `--color-info`
- `--color-focus-ring`

Support light and dark themes. Preserve contrast in charts, image annotations, tables and dialogs.

## 5.3 Typography and layout

Use a readable UI font such as Inter or a system sans-serif stack. Use tabular numerals for scores, counts, timestamps and measurements.

Suggested hierarchy:
- Page title: 24–30 px desktop.
- Section title: 16–20 px.
- Body: 14–16 px.
- Table text: 13–14 px.
- Metadata: 12–13 px, never too small for critical information.

Use a consistent 4/8 px spacing scale. Data-heavy pages may use full width. Keep filters close to the tables they control. Use sticky table headers for long lists where useful.

## 5.4 Status and severity semantics

Use text labels and icons in addition to color.

Statuses:
- Draft
- Configured
- Ready
- Queued
- Running
- Completed
- Failed
- Disabled
- Unavailable
- Needs review
- Approved
- Rejected
- Archived

Severity vocabulary:
- Informational
- Minor
- Major
- Critical

Severity definitions and thresholds must be configurable per industry/product and approved by the manufacturer. Do not hardcode universal industrial safety thresholds.

---

# 6. Page-by-page UI requirements

## 6.1 Overview dashboard

### Purpose
Provide an accurate operational summary, not a wall of decorative metrics.

### Header
- Page title: Overview.
- Organization, facility, production line and selected time range.
- Last data refresh timestamp.
- Refresh action if supported.

### KPI region
Only show metrics computed from persisted, authorized records:
- Inspections performed.
- Accepted / rejected / needs-review counts.
- Defect rate, with denominator and time window.
- Critical findings.
- Review backlog.
- Active inspection stations.
- Model/pipeline availability.

Every metric must have a definition, time window, data source and empty state. Never show a `0% defect rate` when there are no inspections. Show `—` or `No inspection data` and explain that the denominator is zero.

### Charts
Potential charts:
- Inspection volume over time.
- Accepted / rejected / review distribution.
- Defect categories Pareto.
- Severity distribution.
- Product or station comparison.

Charts must use actual API data, show units/date range/aggregation, include accessible labels and tooltips, avoid misleading axes and show empty states.

### Recent activity
Show recent inspections, review actions, training events and model deployments only if those records exist.

### Operational health
Show API/database/model-worker status only when backed by real health checks. Distinguish platform health from model readiness.

## 6.2 New inspection page

### Required context
- Manufacturer / organization (read-only if fixed by session).
- Facility.
- Production line.
- Inspection station.
- Product.
- Product variant / revision.
- Serial or batch identifier.
- Pipeline selection.
- Input image or supported image source.
- Operator identity from authenticated session.

### Upload interaction
- Drag-and-drop and browse.
- Show filename, file size, image dimensions and preview.
- Validate accepted formats and file-size limits based on backend configuration.
- Explain validation errors.
- Do not silently convert or resize original evidence.
- If preprocessing creates a derivative, preserve original and record preprocessing details.
- Support camera/live capture only if the backend and device flow are implemented.

### Execution states
- Ready to submit.
- Uploading.
- Queued.
- Running.
- Completed.
- Failed.
- Cancelled, only if cancellation is supported.

Show progress only when the backend provides meaningful progress. Do not invent percentage progress.

On completion, navigate to a persistent inspection detail page. Do not keep results only in transient component state.

## 6.3 Inspection detail page

This is one of the most important pages in CLOCKIT.

### Header
- Inspection ID.
- Decision status.
- Product and serial/batch.
- Station.
- Timestamp with timezone.
- Operator.
- Pipeline name and immutable version.
- Model versions used.
- Permission-aware actions: review, export, compare, open audit history.

### Evidence workspace
Provide a large image viewer with:
- Original image.
- Anomaly heatmap overlay.
- Segmentation mask overlay.
- Bounding boxes.
- Layer visibility controls.
- Opacity control.
- Zoom and pan.
- Fit-to-view and reset.
- Legend.
- Coordinate / region details where available.

Do not display an overlay if the model did not produce it. Distinguish unavailable evidence from an empty detection.

### Results panel
For each model stage show:
- Model name and version.
- Stage status.
- Anomaly score and documented score range.
- Decision threshold used.
- Calibrated confidence, if calibration exists.
- Inference duration.
- Defect class predictions, if available.
- Localization references.
- Warnings and error details.

Explain whether a value is raw, normalized or calibrated. Do not label an uncalibrated score as probability or confidence.

### Severity
Show:
- Severity class.
- Numeric score and scale definition.
- Affected area ratio, if measured.
- Defect dimensions only when calibrated image scale exists.
- Rules applied.
- Human-review requirement.
- Rationale.

Do not infer physical dimensions from pixels without camera calibration or known scale.

### Final decision
Show:
- Accepted / rejected / needs review.
- Decision policy and version.
- Contributing model stages.
- Thresholds and aggregation logic.
- Reasons for the decision.
- Any stage that failed or was skipped.

A failed stage must not silently result in an accepted inspection. Define safe failure behavior in backend policy.

### Human review
- Reviewer.
- Review timestamp.
- Confirm / reject / escalate actions as authorized.
- Mandatory reason or note for material overrides.
- Previous decision and audit history.
- Clear distinction between AI recommendation and human decision.

## 6.4 Inspection history

Use a server-driven table.

Columns:
- Inspection ID.
- Timestamp.
- Product.
- Serial / batch.
- Station.
- Pipeline version.
- Decision.
- Severity.
- Review status.
- Operator.

Features:
- Search by inspection ID, serial or batch.
- Filters for date range, product, station, decision, severity, pipeline and review state.
- Sortable columns.
- Pagination.
- Saved filters only if persistence is implemented.
- CSV export from authorized backend data.
- Bulk actions only when safe and explicitly supported.

Preserve filters when opening and returning from detail where practical. Show result count, active filters, no-results and no-data states. Do not load all history into the browser.

## 6.5 Review queue

A dedicated work queue for uncertain, critical or policy-escalated inspections.

Show:
- Priority.
- Age / waiting time.
- Product and station.
- Decision reason.
- Severity.
- Confidence/calibration status.
- Assigned reviewer if implemented.

Actions:
- Open evidence.
- Confirm AI decision.
- Override decision with reason.
- Escalate.
- Assign/reassign if supported.

Do not imply calibrated confidence exists until calibration is implemented.

## 6.6 Model registry

### Model list fields
- Model name.
- Model family / architecture.
- Task type.
- Version.
- Artifact status.
- Training status.
- Evaluation status.
- Deployment status.
- Device compatibility.
- Last updated.
- Owner / scope.

### Model detail tabs
1. Overview.
2. Versions and artifacts.
3. Configuration.
4. Evaluation.
5. Training history.
6. Deployment history.
7. Usage / inspection history.
8. Audit events.

### Model lifecycle
Represent lifecycle explicitly:
- Artifact uploaded.
- Artifact validated.
- Configuration registered.
- Training required / trained.
- Evaluation pending / passed / failed.
- Approved for deployment.
- Deployed.
- Disabled.
- Archived.

A model file on disk is not automatically a registered, trained, evaluated or deployable model.

### Initial model inventory context
The project team reports downloaded EfficientAD teacher weights (`pretrained_teacher_small.pth`, `pretrained_teacher_medium.pth`) and a YOLO11n-seg checkpoint (`yolo11n-seg.pt`). These are local artifacts, not proof of end-to-end inference or manufacturer-specific training.

PatchCore is planned. Its compatible implementation and product-specific memory bank must be created before it is marked ready.

### Model actions
- Register artifact.
- Validate artifact.
- Configure model.
- Run test inference.
- Start training.
- Evaluate.
- Approve.
- Deploy.
- Disable.
- Roll back.
- Archive.

Only enable actions when their backend workflow exists. Otherwise show disabled controls with a clear reason or omit the action.

## 6.7 Dataset management

### Dataset list
Fields:
- Dataset name.
- Manufacturer / tenant.
- Industry.
- Product.
- Dataset version.
- Image count.
- Label status.
- Class distribution.
- Split status.
- Validation status.
- Created date.
- Owner.

### Dataset upload wizard
1. Select manufacturer/product context.
2. Upload images or supported archive.
3. Inspect file inventory and validation results.
4. Map labels / defect taxonomy if labeled data is provided.
5. Configure train/validation/test split.
6. Review leakage and duplicate checks.
7. Confirm immutable dataset version.

### Data quality checks
- Corrupt/unreadable images.
- Unsupported formats.
- Duplicate and near-duplicate images.
- Missing labels.
- Invalid annotations.
- Class imbalance.
- Resolution and aspect-ratio distribution.
- Potential train/test leakage.
- Distribution differences between splits.

Do not automatically discard files without showing exclusions and reasons.

### Dataset detail
- Dataset lineage.
- Version history.
- File manifest.
- Labels and taxonomy.
- Split membership.
- Validation report.
- Training jobs using it.
- Model versions trained from it.

## 6.8 Pipeline library and builder

### Purpose
Allow a manufacturer or authorized engineer to chain independent inspection stages.

Potential stage types:
- Input validation.
- Image preprocessing.
- Anomaly detection.
- Object detection.
- Segmentation/localization.
- Severity estimation.
- Confidence calibration.
- Result aggregation.
- Rule evaluation.
- Human review.
- Output/report.

Use a reliable, accessible node-and-edge workflow editor if supported. Otherwise start with a structured stage editor rather than a fake visual canvas.

### Stage configuration panel
Each stage should expose:
- Stage name.
- Model / implementation.
- Version.
- Input contract.
- Output contract.
- Parameters.
- Thresholds.
- Timeout.
- Failure behavior.
- Enabled state.
- Documentation.

### Pipeline validation
Before activation:
- Validate graph connectivity.
- Validate required inputs and outputs.
- Detect cycles unless explicitly supported.
- Validate model compatibility.
- Validate configuration ranges.
- Ensure required stages exist.
- Define behavior for model failure and timeout.
- Show resource requirements only if measured or reliably derived.

### Pipeline versions
- Draft.
- Validated.
- Approved.
- Active.
- Retired.

Published pipeline versions must be immutable. Inspections must reference the exact version used.

### Result aggregation
Do not average raw scores from unrelated models by default. Use validated/calibrated inputs, explicit thresholds and documented rules. Show each stage's contribution to the final decision.

## 6.9 Training center

### Training job creation
Fields:
- Target model family.
- Dataset and immutable version.
- Product / category.
- Training configuration.
- Device.
- Batch size.
- Epochs / steps.
- Image size.
- Seed.
- Checkpoint policy.
- Output version name.

Expose advanced settings progressively. Validate hardware constraints before starting a job.

### Job list and detail
- Queued / running / completed / failed / cancelled.
- Start/end time.
- Runtime.
- Device utilization if available.
- Epoch/step progress only from actual training events.
- Loss and validation metrics.
- Logs.
- Checkpoints.
- Error details.
- Dataset and code/config version.

### Experiments
Compare models only on the same evaluation dataset and compatible evaluation protocol. Clearly label comparisons that are not directly comparable.

### Evaluation metrics
Depending on task and dataset:
- Image-level AUROC.
- Pixel-level AUROC.
- AUPRO.
- Precision.
- Recall.
- F1.
- Confusion matrix.
- Per-class metrics.
- Calibration error / reliability metrics.
- Inference latency and throughput.

Show only metrics appropriate to the task and explain their calculation.

## 6.10 Analytics

Analytics should answer:
- Which products or stations generate the most defects?
- Which defect categories dominate?
- Are defect rates changing?
- Which inspections require human review?
- Are model false negatives or false positives increasing?
- Is input data distribution shifting?
- Which model/pipeline version is active?

Every chart must include metric definition, date range, filter context, denominator where relevant and data freshness.

Do not claim drift detection exists until a real drift calculation and alert policy are implemented.

## 6.11 Reports

Support:
- Inspection report.
- Batch / lot quality report.
- Product quality summary.
- Station performance report.
- Model evaluation report.
- Audit/export report.

Include organization/facility, generation time and timezone, filtered period, data definitions, inspection references, model and pipeline versions, permitted evidence, distinction between AI recommendation and human decision, and export provenance.

Generate reports from authorized backend data. Do not silently omit records due to client-side pagination.

## 6.12 Administration and settings

Pages:
- Organization profile.
- Facilities.
- Production lines.
- Products and variants.
- Inspection stations.
- Users and roles.
- Defect taxonomy.
- Retention policy.
- File storage settings.
- Model runtime settings.
- Notification settings.
- Audit log.

Separate environment/system settings from manufacturer-level configuration.

---

# 7. Shared interaction patterns

Every data page must implement:
- Loading state.
- Empty state.
- Error state with retry where safe.
- Permission-denied state.
- Stale-data indicator where applicable.
- Responsive layout.
- Keyboard navigation.
- Accessible labels.
- Clear action feedback.
- Confirmation for destructive actions.
- Server-side pagination/filtering for large datasets.

## 7.1 Forms
- Explicit labels and helper text.
- Fields grouped by purpose.
- Client validation for usability and server validation for correctness.
- Preserve input after recoverable errors.
- Prevent duplicate submissions.
- Mark required fields.
- Show field-level errors.
- Confirm irreversible operations.
- Never use placeholder text as the only label.

## 7.2 Dialogs and drawers
Use dialogs for focused confirmations and short forms. Use drawers for contextual details that should not discard table context. Use full pages for complex workflows such as dataset upload, model configuration and pipeline editing.

## 7.3 Notifications
Use notifications for upload, inspection, training, deployment and review events. A toast is not a replacement for persistent job history or error details.

## 7.4 Accessibility
Target WCAG 2.2 AA where practical:
- Keyboard access for all actions.
- Visible focus indicators.
- Sufficient text and status contrast.
- Semantic headings and landmarks.
- Accessible form errors.
- Non-color-only status encoding.
- Screen-reader labels for charts and image controls.
- Reduced-motion support.

---

# 8. Frontend architecture

Keep the existing React + TypeScript + Vite stack. Do not rewrite the application merely to adopt a fashionable framework.

Suggested structure, to be adapted to the existing repository rather than duplicated:

```text
frontend/
└── src/
    ├── app/
    │   ├── App.tsx
    │   ├── router.tsx
    │   ├── providers/
    │   └── guards/
    ├── components/
    │   ├── layout/
    │   ├── navigation/
    │   ├── data-display/
    │   ├── forms/
    │   ├── feedback/
    │   ├── charts/
    │   └── inspection-viewer/
    ├── features/
    │   ├── dashboard/
    │   ├── inspections/
    │   ├── review-queue/
    │   ├── pipelines/
    │   ├── models/
    │   ├── datasets/
    │   ├── training/
    │   ├── analytics/
    │   ├── reports/
    │   └── administration/
    ├── services/
    │   ├── apiClient.ts
    │   ├── healthService.ts
    │   ├── inspectionService.ts
    │   ├── modelService.ts
    │   ├── datasetService.ts
    │   └── pipelineService.ts
    ├── hooks/
    ├── types/
    ├── utils/
    ├── styles/
    └── assets/
```

## 8.1 Architecture rules
- Feature-oriented modules; avoid one giant component per page.
- Keep API calls out of presentational components.
- Use typed request/response contracts.
- Centralize API client configuration and error handling.
- Do not duplicate backend business rules in frontend code.
- Keep authorization decisions on the backend.
- Avoid global state unless genuinely shared.
- Use URL query parameters for shareable table filters where appropriate.
- Do not store large image blobs or model artifacts in general application state.
- Revoke temporary object URLs when no longer needed.
- Add error boundaries around major feature areas.
- Do not add dependencies without a clear need.

## 8.2 API integration
The documented frontend API base URL is:

`VITE_API_URL ?? http://localhost:8000/api/v1`

Continue using environment configuration. Do not hardcode production URLs in components.

Every API service should have typed inputs/outputs, cancellation where appropriate, consistent error classification and safe data refresh after mutations. Never silently substitute mock data when the API fails.

## 8.3 Type contracts
Create frontend types that mirror documented backend contracts. Do not guess fields from UI mockups. If a backend contract does not exist, mark the feature as blocked by API contract and document the required schema.

---

# 9. Backend capabilities required by the target UI

The frontend cannot deliver a real industrial workflow without backend support. Recommended future resource families:

- `/auth`
- `/organizations`
- `/facilities`
- `/production-lines`
- `/products`
- `/stations`
- `/users`
- `/datasets`
- `/dataset-versions`
- `/models`
- `/model-versions`
- `/training-jobs`
- `/evaluations`
- `/pipelines`
- `/pipeline-versions`
- `/inspections`
- `/inspection-results`
- `/reviews`
- `/reports`
- `/audit-logs`
- `/system-health`

These are proposed resource families, not a claim that these routes currently exist.

## 9.1 Backend contract rules
- Use stable IDs, not display names, as references.
- Include tenant scope and enforce it server-side.
- Use timezone-aware timestamps.
- Use pagination for list endpoints.
- Validate sort/filter fields.
- Use consistent error response schemas.
- Use idempotency for operations where retries could create duplicate jobs or inspections.
- Use background jobs for long-running inference, training and report generation where required.
- Return job IDs and explicit lifecycle states.
- Store immutable references to input images, model versions and pipeline versions.
- Version APIs deliberately.
- Document endpoints using OpenAPI.

---

# 10. Industrial inspection evidence and trust

The UI must help users understand the evidence behind an AI-assisted decision.

## 10.1 Keep these concepts separate
- Anomaly score.
- Defect probability.
- Model confidence.
- Calibrated confidence.
- Severity.
- Affected area.
- Final quality decision.

They are different quantities and may have different ranges and meanings.

## 10.2 Evidence provenance
For each result, preserve and expose where available:
- Original input image reference and integrity hash.
- Preprocessing operations and parameters.
- Model name, version and artifact hash.
- Pipeline version.
- Thresholds and decision policy.
- Inference timestamp and runtime environment.
- Model outputs.
- Human review and override history.

## 10.3 Uncertainty and failure
- If a model is uncalibrated, say so.
- If a stage fails, show the stage failure.
- If an output is missing, do not render a fabricated overlay.
- If the image is invalid or out-of-distribution, show an explicit warning if detected by the backend.
- If a decision cannot safely be made, route to review according to configured policy.
- Never silently turn an incomplete pipeline into a passing result.

## 10.4 Explainability
Show evidence available from the model: heatmap, segmentation, bounding boxes, per-stage scores, threshold comparisons and rule outcomes. Do not invent natural-language explanations unsupported by model outputs or configured rules.

---

# 11. Performance and hardware-aware UI

The development machine has been described in project discussions as 16 GB system RAM and an NVIDIA RTX 3050. Treat this as a development constraint, not a production capacity guarantee.

UI requirements:
- Show model readiness and device assignment from backend telemetry.
- Show whether a model is loaded, unloaded or loading.
- Do not imply all models are resident in GPU memory.
- Support sequential inference and lazy model loading.
- Avoid repeated rendering of huge image payloads.
- Use thumbnails in tables and full-resolution evidence in detail views.
- Use server-side pagination and aggregation.
- Avoid excessive polling; use backend-supported polling or events.
- Make long-running jobs recoverable after page refresh.

The documented runtime approach includes sequential inference, one concurrent inspection, one concurrent training job, lazy loading and reserved VRAM. The UI must reflect actual runtime settings, not hardcode assumptions.

---

# 12. Security, privacy and auditability

The UI is only one security layer. The backend must enforce all controls.

Requirements:
- Tenant isolation on every tenant-scoped API.
- Role-based authorization.
- Secure session/token handling.
- No secrets in frontend bundles.
- Server-side file validation.
- Restrict file types, sizes and archive extraction paths.
- Prevent path traversal.
- Avoid exposing local filesystem paths to ordinary users.
- Use authorized or signed evidence access.
- Record consequential actions in audit logs.
- Require reasons for manual overrides and model/pipeline promotion where policy requires.
- Show session expiration and permission errors clearly.
- Do not leak another tenant's names, IDs, image paths or model metadata in errors.

Audit events should include actor, action, target, timestamp, scope, result and relevant before/after values where appropriate. Do not store passwords, secrets or unnecessary sensitive data in audit payloads.

---

# 13. Error handling and operational states

Define a shared error taxonomy and reusable UI components.

Examples:
- `NETWORK_UNAVAILABLE`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `VALIDATION_FAILED`
- `RESOURCE_NOT_FOUND`
- `UPLOAD_REJECTED`
- `MODEL_NOT_READY`
- `MODEL_LOAD_FAILED`
- `INFERENCE_FAILED`
- `PIPELINE_INVALID`
- `TRAINING_FAILED`
- `RESOURCE_EXHAUSTED`
- `INTERNAL_ERROR`

For each error:
- Give a concise human-readable message.
- Show a safe diagnostic/reference ID if available.
- Provide a recovery action when appropriate.
- Keep technical details in authorized diagnostic views/logs.
- Do not expose stack traces to ordinary users.

Do not show a green success notification if a later persistence step failed.

---

# 14. Testing and quality gates

A visually polished frontend is not complete unless its workflows are tested.

## 14.1 Component tests
- Buttons, menus and dialogs.
- Form validation.
- Status indicators.
- Data tables.
- Empty/loading/error states.
- Image viewer controls.
- Permission-aware actions.

## 14.2 Feature tests
- Dashboard loads only persisted data.
- Inspection upload validates and submits correctly.
- Inspection detail renders only returned evidence.
- Review action persists and records a note.
- Model registry reflects backend lifecycle states.
- Dataset wizard handles invalid and valid uploads.
- Pipeline validation errors are visible.
- Training job state survives page refresh.
- Analytics filters match backend results.

## 14.3 End-to-end tests
At minimum, when authentication and workflows exist:
1. Log in with a test account.
2. Select an organization and product.
3. Upload a valid image.
4. Submit an inspection.
5. Observe lifecycle states from actual backend responses.
6. Open the persisted result.
7. Inspect original image and returned overlays.
8. Review the result with a reason.
9. Verify review in history/audit log.
10. Confirm another tenant cannot access the inspection.

## 14.4 Accessibility and responsive tests
- Keyboard-only navigation.
- Focus order.
- Screen reader labels.
- Contrast checks.
- Tablet layout.
- Small desktop viewport.
- Large data table behavior.
- Reduced motion.

## 14.5 Build gates
Before merging:
- TypeScript compilation passes.
- Lint passes.
- Unit tests pass.
- Feature tests pass.
- Production build passes.
- No console errors in primary workflows.
- No fake data or placeholder buttons in completed areas.
- API contract tests pass.

---

# 15. Delivery strategy: complete vertical slices

Do not build every page as a visual shell and call the product complete. Build one end-to-end workflow at a time.

## Milestone 0 — UI foundation
Deliver:
- Design tokens.
- Application shell.
- Navigation.
- Typography and layout.
- Shared button, input, table, dialog, status and empty-state components.
- Responsive behavior.
- Theme support.
- API client and error handling.

Acceptance:
- Existing routes still work.
- No fake data is introduced.
- Frontend production build passes.

## Milestone 1 — Inspection workflow
Deliver:
- New inspection form.
- Upload validation.
- Real API integration.
- Inspection lifecycle states.
- Persistent inspection detail.
- Evidence viewer.
- Inspection history.
- Human review workflow where backend supports it.

Acceptance:
- One real uploaded image can be processed and persisted.
- UI renders only actual backend outputs.
- Errors and incomplete model stages are visible.
- Historical result can be reopened after refresh.

## Milestone 2 — Model registry
Deliver:
- Model inventory.
- Artifact registration.
- Model details.
- Model lifecycle.
- Version information.
- Test inference action where backend supports it.

Acceptance:
- Downloaded weights are not automatically shown as production-ready models.
- Model readiness is backed by artifact/configuration/inference validation.
- No placeholder model records.

## Milestone 3 — Dataset management
Deliver:
- Dataset upload.
- Validation.
- Versioning.
- Dataset detail and lineage.
- Split management.

Acceptance:
- Dataset files and metadata are persisted.
- Validation results are traceable.
- Dataset versions are immutable.

## Milestone 4 — Pipelines
Deliver:
- Pipeline list.
- Stage configuration.
- Validation.
- Versioning.
- Activation and history.

Acceptance:
- A pipeline can be executed by the backend.
- The inspection records the exact pipeline version.
- Model outputs are combined only by a documented policy.

## Milestone 5 — Training and evaluation
Deliver:
- Training job configuration.
- Job monitoring.
- Logs and checkpoints.
- Evaluation reports.
- Model comparison.

Acceptance:
- Training status is backed by actual jobs.
- Metrics are computed on identified dataset versions.
- Model promotion requires explicit evaluation and authorization.

## Milestone 6 — Analytics and reporting
Deliver:
- Quality trends.
- Defect distribution.
- Station/product comparisons.
- Reports and exports.
- Audit views.

Acceptance:
- Every metric has a definition and source.
- Aggregates reconcile with underlying inspection records.
- Empty datasets do not produce misleading rates.

## Milestone 7 — Production hardening
Deliver:
- Permission-aware experience.
- Tenant-safe UI flows.
- Audit trail.
- Operational health.
- Resilience and recovery.
- Accessibility and performance optimization.

Acceptance:
- Cross-tenant access tests pass.
- Critical actions are audited.
- Failure states are safe and understandable.
- Release checklist is signed off.

---

# 16. Definition of done — no half-finished UI

A page is not complete merely because it renders.

A feature is complete only when all applicable conditions are met:
- Real user problem and workflow are defined.
- Backend API contract exists.
- Data is persisted where required.
- Loading, empty, error, permission and success states exist.
- Forms validate correctly.
- Actions perform real operations.
- Destructive actions are confirmed.
- User feedback reflects actual operation outcomes.
- Data is refreshed after mutations.
- Permissions are enforced by the backend.
- Responsive and keyboard behavior is tested.
- Automated tests cover critical behavior.
- No fabricated data or fake performance metrics exist.
- No dead buttons, fake links or misleading status labels exist.
- Documentation explains known limitations.

If the backend is not ready, label the feature unavailable or keep it out of production navigation. Do not ship a convincing-looking but non-functional page.

---

# 17. Instructions to the coding agent

You are implementing the CLOCKIT / PROMETHEUS-X frontend as a serious industrial quality-inspection application.

## First: inspect the repository

Before changing code:
1. Read the existing frontend source and route structure.
2. Read backend API routes and Pydantic schemas.
3. Read project architecture and `completed.md`.
4. Identify what is actually implemented.
5. Identify mock data, placeholder pages and non-functional controls.
6. Produce a concise implementation plan with files to change.
7. Preserve working integrations.

Do not assume that a page or endpoint exists because it is described in this document.

## Implementation rules

- Retain React 18, TypeScript, Vite, Tailwind, React Router, Axios, Recharts and Lucide unless a specific technical reason requires a change.
- Do not rebuild the backend.
- Do not invent API endpoints or response fields.
- Do not add fake datasets, manufacturers, inspections, model metrics or charts.
- Do not use static arrays as a substitute for live business data.
- Do not create decorative controls that do nothing.
- Do not claim model training, calibration, localization or pipeline orchestration is live until verified.
- Do not implement all pages as empty shells.
- Do not change database records from GET requests.
- Do not weaken existing tests to make the build pass.
- Do not remove real user data.
- Do not add dependencies without justification.
- Do not expose filesystem paths, secrets or tenant data.

## Visual quality requirements

- Consistent design tokens and reusable components.
- Excellent hierarchy and information density.
- Precise tables and forms.
- High-quality inspection evidence viewer.
- Clear status semantics.
- Responsive layout.
- Light and dark themes.
- Accessible interaction patterns.
- No excessive gradients, decorative cards or generic AI-dashboard styling.

## Work method

Build one complete vertical slice at a time. For each milestone:
1. Explain scope and dependencies.
2. Inspect current implementation.
3. Define or verify API contracts.
4. Implement shared components.
5. Implement the complete workflow.
6. Add loading/empty/error/permission states.
7. Add tests.
8. Run tests and production build.
9. Report exact files changed and known limitations.
10. Do not pretend blocked backend features are complete.

## Required final report after each milestone

- What is implemented.
- What is connected to real APIs.
- What remains unavailable.
- Files created/modified.
- Tests executed and results.
- Known bugs and technical debt.
- Next milestone and dependencies.

**Primary objective:** Deliver a reliable, traceable and extensible industrial quality-intelligence interface. Correctness, evidence, usability and operational trust are more important than the number of screens or visual effects.
