# CLOCKIT --- High-Throughput Inspection Engine

## Mass Testing, External API Ingestion, Parallel Processing & Reliability

**Document type:** Product and technical implementation specification\
**Project:** CLOCKIT\
**Primary objective:** Enable CLOCKIT to accept and process large
volumes of image inspections reliably, without blocking the API or
exhausting CPU, RAM, or GPU resources.

------------------------------------------------------------------------

## 1. Objective

CLOCKIT must support sustained, high-volume inspection workloads through
two submission channels:

1.  **Mass Test UI:** An operator uploads a ZIP archive or multiple
    image files for bulk inspection, benchmarking, and simulation.
2.  **External API:** Another application submits individual or bulk
    inspection requests to simulate an automated production line.

Both channels must use the **same inspection pipeline**. Do not create
separate inference implementations for the dashboard and API.

The system must support:

-   Concurrent submissions.
-   Large datasets without loading all files into RAM.
-   Multiple scanner units and analysis modules.
-   Bounded CPU preprocessing.
-   Controlled GPU inference.
-   Reusable loaded models.
-   Persistent job state and results.
-   Progress reporting.
-   Cancellation and bounded retries.
-   Recovery after application restart.
-   Throughput, latency, and resource monitoring.

The goal is not simply to process many images at once. The goal is to
accept work continuously, control resource usage, and complete every
accepted inspection with a traceable outcome.

## 2. Core Architecture

Separate the system into five responsibilities:

1.  **Submission layer:** Accepts work from the Mass Test UI or external
    clients.
2.  **API and ingestion layer:** Validates submissions, stores uploaded
    files, and creates persistent jobs.
3.  **Job queue:** Tracks pending work, priorities, attempts, and
    execution state.
4.  **Processing engine:** Prepares images, schedules model inference,
    and assembles inspection results.
5.  **Persistence and monitoring:** Saves results and exposes progress
    and performance metrics.

### 2.1 Processing flow

``` text
Mass Test UI                 External Application
     |                              |
     +--------------+---------------+
                    |
             FastAPI / API Layer
                    |
       Validation, Upload, Job Creation
                    |
          Persistent Job / Batch Records
                    |
              Job Dispatcher
                    |
           Bounded Processing Queue
                    |
          CPU Preparation Workers
                    |
          GPU Inference Scheduler
                    |
        Scanner Unit / Analysis Modules
                    |
          Result Aggregation Layer
                    |
          Existing Inspection Records
                    |
        Progress, Results, and Metrics
```

The API accepts and registers work. The queue manages work. The
processing engine executes work. The API must not own the lifecycle of
an inference operation.

### 2.2 Shared pipeline

``` text
Mass Test ─────┐
               ├──> Job Creation ──> Shared Processing Engine
External API ──┘
```

Both submission channels must produce the same normalized inspection-job
representation. Do not duplicate model loading, preprocessing,
inference, defect aggregation, or result persistence logic.

## 3. Concurrency and Resource Management

### 3.1 Hardware target

Initial development hardware:

-   RAM: 16 GB
-   GPU: NVIDIA RTX 3050
-   CPU: 4 cores
-   Execution: Local machine

All concurrency values below are **initial tuning settings**, not
guaranteed optimal values. Measure actual throughput, latency, and
memory use before increasing them.

### 3.2 Recommended starting configuration

  Component                             Initial configuration
  ---------------------------- ------------------------------
  GPU inference worker                                      1
  CPU preparation workers                                   2
  Preprocessing thread pool      Bounded, initially 4 threads
  Initial micro-batch target     2--4 images, model dependent
  Maximum batch wait                          Initially 50 ms
  In-memory pending work                              Bounded
  Concurrent upload streams          Configurable and bounded

Avoid assigning every CPU core to every library. PyTorch, OpenCV, BLAS,
and other native libraries may create their own threads. Uncontrolled
nested parallelism can oversubscribe the four-core CPU.

Set and benchmark library thread limits explicitly. Keep preprocessing
concurrency configurable.

### 3.3 CPU work

Use bounded thread pools for suitable I/O-heavy and native-library
operations, including:

-   Image file reads.
-   Image decoding where the library releases the GIL.
-   Image resizing and format conversion.
-   ZIP member reads and extraction.
-   Other independent preprocessing operations.

Use multiprocessing only when profiling demonstrates a benefit for
CPU-bound Python work. Do not create a process per image.

### 3.4 GPU work

Use a dedicated GPU inference scheduler/worker as the single owner of
GPU model execution in the initial single-GPU prototype.

The scheduler must:

-   Reuse loaded model instances.
-   Control the number of concurrent GPU operations.
-   Group compatible images into micro-batches where supported.
-   Respect model-specific batch-size limits.
-   Monitor CUDA memory and execution failures.
-   Reduce batch size or retry safely after an out-of-memory event.
-   Avoid repeatedly loading and unloading models.

One GPU worker does **not** mean one image per operation. A compatible
model may process a batch in one forward pass. Models that do not
support batching efficiently may run sequentially while remaining
loaded.

Do not run multiple independent copies of the same large model merely to
increase concurrency.

## 4. Model Registry and Lifecycle

Create a central Model Registry so the processing engine can identify,
load, reuse, and manage models.

Suggested structure:

``` text
backend/
└── engine/
    ├── model_registry.py
    ├── model_loader.py
    ├── inference_scheduler.py
    ├── batch_processor.py
    ├── preprocessing.py
    ├── result_aggregator.py
    ├── resource_manager.py
    └── worker.py

models/
├── edge_detection/
│   ├── model.pt
│   └── info.txt
├── efficientad/
│   ├── model.pt
│   └── info.txt
└── yolo/
    ├── model.pt
    └── info.txt
```

The exact model folder layout must remain compatible with the project's
model-management specification.

### 4.1 Model loading workflow

1.  A job identifies its scanner unit.
2.  CLOCKIT resolves the scanner unit's configured analysis modules.
3.  Each module resolves its required model and configuration.
4.  The registry checks whether a compatible model instance is already
    loaded.
5.  If not loaded, the model is initialized once.
6.  Subsequent jobs reuse the loaded instance.
7.  Models are unloaded only through controlled lifecycle management.

### 4.2 Model identity and safe reuse

A reusable model instance must be keyed by enough information to prevent
incompatible reuse, including:

-   Model identifier and weights/version.
-   Device.
-   Model configuration.
-   Relevant preprocessing configuration.
-   Execution mode and precision, where applicable.

If two scanner units use the same compatible model and configuration,
the registry may reuse the instance. Do not assume that matching model
names alone makes two instances interchangeable.

### 4.3 Model lifecycle states

Track at least:

-   UNLOADED
-   LOADING
-   READY
-   ERROR
-   UNLOADING

Expose model load failures clearly. Do not mark an inspection as
successfully processed if a required model could not load.

## 5. Job and Batch Model

A **batch** represents a submission containing one or more inspection
jobs. Each image inspection is an independent job.

Example:

``` text
Batch: MASS-001
├── Job: INS-001 — COMPLETED
├── Job: INS-002 — COMPLETED
├── Job: INS-003 — PROCESSING
├── Job: INS-004 — QUEUED
└── Job: INS-005 — QUEUED
```

External API submissions must use the same batch/job model.

### 5.1 Batch record

Create a `JobBatch` entity with fields such as:

  Field             Purpose
  ----------------- ---------------------------------
  batch_id          Unique batch identifier
  source_type       MASS_TEST or API
  scanner_unit_id   Selected scanner unit
  total_items       Number of accepted jobs
  completed_items   Successfully completed jobs
  failed_items      Jobs that failed execution
  cancelled_items   Jobs cancelled before execution
  created_at        Submission timestamp
  started_at        First processing timestamp
  completed_at      Terminal timestamp
  status            Aggregate batch status
  metadata          Optional submission metadata

Progress counts must be derived from persisted job states or updated
transactionally. Avoid allowing counters to drift from the underlying
jobs.

### 5.2 Inspection job record

Create an `InspectionJob` entity with fields such as:

  Field             Purpose
  ----------------- ---------------------------------------------------
  job_id            Unique job identifier
  batch_id          Parent batch
  image_path        Managed image location
  scanner_unit_id   Scanner configuration
  priority          Scheduling priority
  status            Execution state
  retry_count       Number of attempts
  submitted_at      Submission timestamp
  started_at        Processing start
  completed_at      Terminal timestamp
  error_code        Machine-readable failure category
  error_message     Safe diagnostic description
  idempotency_key   Duplicate submission protection, where applicable

Store durable file references, not image bytes, in job records.

### 5.3 Processing metrics record

Record metrics per job, where measurable:

-   preprocessing_ms
-   model_load_ms, where attributable
-   inference_ms
-   analysis_ms
-   persistence_ms
-   total_processing_ms
-   peak_process_memory_mb
-   GPU memory measurements, where available

Do not confuse queue wait time with processing time. Track them
separately.

### 5.4 Existing inspection records

The existing `InspectionRecord` and associated result tables remain the
authoritative completed inspection results.

The job system tracks execution lifecycle. It must not create a
competing duplicate representation of inspection decisions or defect
records.

A job may be `COMPLETED` while its inspection decision is `FAIL` or
`REVIEW_REQUIRED`.

## 6. Job States and State Transitions

Execution status and inspection decision are separate concepts.

### 6.1 Execution statuses

  Status          Meaning
  --------------- ---------------------------------------------------------
  QUEUED          Accepted and waiting
  PREPROCESSING   Image is being prepared
  PROCESSING      Model inference is running
  ANALYZING       Module results are being combined
  COMPLETED       Result successfully persisted
  FAILED          Processing failed permanently or retries were exhausted
  CANCELLED       Cancelled before execution

### 6.2 State rules

-   A job is created as QUEUED.
-   A worker claims it atomically before processing.
-   State changes are persisted.
-   A job must not be claimed by two workers simultaneously.
-   COMPLETED is set only after the inspection result has been persisted
    successfully.
-   A FAIL inspection decision is still a successfully COMPLETED job.
-   FAILED is reserved for execution failures, not detected product
    defects.
-   CANCELLED jobs must not be dispatched.
-   Retries must be bounded and recorded.

Use explicit, validated state transitions. Do not allow arbitrary status
changes from API clients.

### 6.3 Retry policy

Retry only failures considered transient.

Examples:

-   Temporary file-access error.
-   Recoverable worker interruption.
-   Transient database connectivity issue.
-   GPU out-of-memory event after a safe batch-size reduction.

Do not repeatedly retry permanent failures such as corrupt or
unsupported files.

Use a configurable retry limit and record each attempt.

## 7. Persistent Queue and Recovery

### 7.1 Prototype approach

For the initial single-machine prototype, use the existing
database-backed job records and a controlled dispatcher.

SQLite is acceptable for this stage if:

-   Job claiming uses transactions and atomic updates.
-   Write transactions are short.
-   Database writes are not held open during inference.
-   Database connections are handled safely across threads.
-   Busy/locked errors are handled with bounded retries.
-   The queue is not implemented as an unbounded in-memory list.

Use a single controlled job-claiming mechanism initially. Do not treat
SQLite as a distributed, high-concurrency message broker.

### 7.2 In-memory queues

In-memory queues may be used as bounded buffers between processing
stages. They must not be the source of truth.

If the application stops, pending jobs must remain discoverable from
persistent records.

### 7.3 Restart recovery

On startup:

1.  Find jobs left in non-terminal states.
2.  Determine whether they were safely completed or interrupted.
3.  Reconcile them with persisted inspection results.
4.  Requeue recoverable work.
5.  Mark unrecoverable work FAILED with a diagnostic reason.
6.  Recalculate batch progress from job records.

Design processing to be idempotent. A crash after result persistence but
before the job status update must not create duplicate inspection
results during recovery.

### 7.4 Future broker migration

Do not introduce Redis, Celery, or RabbitMQ solely for the initial
prototype.

Consider a shared message broker when CLOCKIT needs multiple worker
processes, multiple machines, distributed scheduling, or queue
throughput beyond what the database-backed design can safely support.

Keep the queue interface separate from inference code so the backing
implementation can change without rewriting the model pipeline.

## 8. Image Ingestion and File Handling

Large datasets must not be loaded into memory all at once.

### 8.1 Upload handling

-   Stream uploads to managed storage.
-   Enforce maximum upload and archive sizes.
-   Validate file types using content inspection, not only filename
    extensions.
-   Limit image dimensions and decoded pixel counts.
-   Reject unsupported formats clearly.
-   Prevent path traversal during ZIP extraction.
-   Prevent ZIP bombs through limits on entry count, total uncompressed
    size, and compression ratio.
-   Generate safe internal filenames.
-   Keep original filenames as metadata only.
-   Avoid extracting untrusted archives directly into arbitrary project
    directories.

### 8.2 Dataset workflow

1.  Receive upload.
2.  Store the archive or files safely.
3.  Validate archive and entries.
4.  Build a manifest.
5.  Register accepted image jobs.
6.  Extract or stage files in bounded chunks.
7.  Dispatch jobs for preprocessing.

Do not create all decoded image objects at ingestion time.

### 8.3 Supported formats

Use the formats supported by the existing CLOCKIT image pipeline. The UI
and API must report unsupported formats consistently.

## 9. Preprocessing and Micro-Batching

### 9.1 Preprocessing stage

CPU workers prepare individual images according to the requirements of
the configured scanner unit and models.

Typical work includes:

-   Decode.
-   Validate dimensions and channels.
-   Resize or pad as required.
-   Normalize.
-   Convert to model tensor format.
-   Attach image and job metadata.

Avoid applying one universal preprocessing pipeline to every model. Each
analysis module must retain its required input contract.

### 9.2 Micro-batching

Implement configurable batching for models that support it.

Initial experimental settings:

``` python
INITIAL_BATCH_SIZE = 4
MAX_BATCH_WAIT_MS = 50
```

These values must be configurable and benchmarked per model.

The scheduler should:

-   Collect compatible ready inputs.
-   Batch only inputs with compatible model, shape, configuration, and
    device requirements.
-   Dispatch when the batch reaches its target size.
-   Dispatch a partial batch when the wait deadline expires.
-   Never wait indefinitely for a full batch.
-   Reduce batch size after recoverable GPU memory pressure.
-   Preserve the original job identity for every batch item.

A batch failure must not automatically cause every contained job to be
marked FAILED if individual retry or smaller-batch execution can recover
them.

## 10. Inspection Result Aggregation

A scanner unit may contain multiple analysis modules.

The engine must:

1.  Resolve the scanner unit configuration.
2.  Execute the required modules.
3.  Associate each module result with the correct inspection job.
4.  Normalize outputs into the existing CLOCKIT result contracts.
5.  Aggregate defect findings and severity classifications using the
    existing decision rules.
6.  Persist the final inspection result.
7.  Mark the job COMPLETED only after successful persistence.

Do not invent new defect aggregation or quality-score rules as part of
this infrastructure work. Reuse the existing inspection logic and
contracts.

A failure in one required module must follow an explicit scanner-unit
policy. Do not silently treat a missing module result as a clean
inspection.

## 11. External API

External applications must be able to submit work without using the
dashboard.

Suggested endpoints:

  --------------------------------------------------------------------------------
  Method                  Endpoint                         Purpose
  ----------------------- -------------------------------- -----------------------
  POST                    `/api/v1/jobs`                   Submit one inspection

  POST                    `/api/v1/jobs/bulk`              Submit multiple
                                                           inspections

  GET                     `/api/v1/jobs/{id}`              Retrieve individual job
                                                           status

  GET                     `/api/v1/batches/{id}`           Retrieve batch progress

  GET                     `/api/v1/batches/{id}/results`   Retrieve paginated
                                                           batch results

  POST                    `/api/v1/batches/{id}/cancel`    Cancel pending jobs

  GET                     `/api/v1/engine/status`          Retrieve engine health

  GET                     `/api/v1/engine/metrics`         Retrieve performance
                                                           metrics
  --------------------------------------------------------------------------------

These are proposed contracts. Inspect the existing API conventions
before implementation and avoid duplicating existing endpoints.

### 11.1 Bulk submission example

A bulk request may use multipart uploads or secure file references. Do
not assume an external application's local filesystem paths are
accessible to CLOCKIT.

Illustrative metadata contract:

``` json
{
  "scanner_unit_id": 1,
  "priority": "NORMAL",
  "metadata": {
    "production_line": "LINE_01",
    "batch_reference": "SHIFT_A_001"
  }
}
```

The actual image files or secure file references accompany the request.

### 11.2 Immediate response

Return after validation and durable job registration, not after
inference completes.

Illustrative response:

``` json
{
  "batch_id": "MASS-001",
  "status": "QUEUED",
  "total_items": 3,
  "completed_items": 0,
  "status_url": "/api/v1/batches/MASS-001"
}
```

Use real generated identifiers, not hardcoded examples.

### 11.3 API requirements

-   Authentication and authorization.
-   Request validation.
-   Upload and payload size limits.
-   Rate limiting.
-   Idempotency keys for safe retries.
-   Pagination for result retrieval.
-   Clear HTTP status codes and error contracts.
-   No arbitrary server filesystem paths supplied by clients.
-   Do not expose internal paths, stack traces, or secrets.
-   Ensure a client can only access jobs and batches it is authorized to
    access.

Use polling initially. WebSocket or server-sent event progress can be
added later without changing the underlying job model.

## 12. Mass Test Interface

Create a dedicated Mass Test page. Do not overload the ordinary
single-image Test Sample workflow.

### 12.1 Submission

Support:

-   ZIP archive upload.
-   Multiple image selection.
-   Scanner unit selection.
-   Validation preview.
-   Submission confirmation.
-   Clear rejected-file reporting.

### 12.2 Live progress

Display:

-   Total accepted jobs.
-   Queued jobs.
-   Preprocessing jobs.
-   Processing jobs.
-   Completed jobs.
-   Failed jobs.
-   Cancelled jobs.
-   Overall progress percentage.
-   Elapsed time.
-   Current throughput.

All values must come from real persisted job state or measured engine
metrics. Never use simulated progress in the production UI.

### 12.3 Controls

-   Pause dispatch of new work.
-   Resume dispatch.
-   Cancel pending jobs.
-   Retry eligible failed jobs.
-   View individual job details.
-   Filter results by execution status, inspection decision, and
    severity.
-   Export results.

Pause must not forcibly interrupt a CUDA operation. It should stop
dispatching new work and allow in-flight operations to finish safely.

Cancellation should stop pending work. In-flight operations should
complete or be cancelled only at safe boundaries.

### 12.4 Results

Display the existing CLOCKIT inspection result fields:

-   Product/image identity.
-   Inspection decision.
-   Quality score, when available.
-   Defects.
-   Severity.
-   Processing duration.
-   Error information for failed jobs.

Do not create a second result format solely for Mass Test.

## 13. Monitoring and Performance Metrics

The engine must expose operational metrics independently of inspection
analytics.

### 13.1 Required metrics

  Metric               Definition
  -------------------- --------------------------------------------
  Queue depth          Number of jobs waiting
  Throughput           Completed inspections per second or minute
  Queue wait           Time from acceptance to processing start
  Processing latency   Time from processing start to completion
  End-to-end latency   Time from acceptance to completion
  P50 latency          Median end-to-end or processing latency
  P95 latency          95th percentile latency
  Failure rate         Failed execution jobs / accepted jobs
  CPU utilization      System or process CPU usage
  RAM usage            Process and system memory usage
  GPU utilization      GPU workload, when available
  GPU memory           VRAM usage
  Model load time      Time spent initializing models

Clearly label the time interval and population behind each metric.

Do not confuse inspection decision FAIL with execution failure.

### 13.2 Engine status

The engine status endpoint should report:

-   Engine state.
-   Worker state.
-   Queue depth.
-   Loaded models.
-   GPU availability.
-   Recent processing activity.
-   Resource utilization where supported.

Do not expose sensitive host information to unauthenticated clients.

## 14. Reliability and Failure Handling

  -----------------------------------------------------------------------
  Failure                             Expected behaviour
  ----------------------------------- -----------------------------------
  Corrupt image                       Reject or mark individual job
                                      invalid/FAILED

  Unsupported format                  Reject with a clear reason

  GPU out of memory                   Reduce batch size and retry safely

  Model loading failure               Report engine/module error; do not
                                      produce a false PASS

  Inference exception                 Isolate job and record diagnostic
                                      details

  Database temporarily unavailable    Do not mark result persisted; retry
                                      safely

  Application restart                 Recover interrupted and queued jobs

  Duplicate submission                Apply idempotency protection

  User cancels batch                  Stop pending jobs; finish in-flight
                                      work safely

  Disk space exhausted                Stop accepting work safely and
                                      report an operational error
  -----------------------------------------------------------------------

Use bounded retries with backoff for transient failures. Permanent
failures must not retry indefinitely.

Persist enough state to distinguish accepted, claimed, running,
result-persisted, and terminal jobs.

## 15. Security and Resource Protection

Treat uploaded files and external API requests as untrusted.

Implement:

-   Authentication and authorization.
-   Request and upload limits.
-   Archive extraction protections.
-   Image dimension and pixel-count limits.
-   Safe generated filenames.
-   Managed storage paths.
-   Per-client rate limits.
-   Idempotency protection.
-   Bounded queues and worker pools.
-   Disk-space monitoring.
-   Resource-aware admission control.
-   Safe error messages.
-   Audit logs for submissions and cancellations.

When the system reaches configured capacity, reject or defer new
submissions explicitly. Do not accept unlimited work into memory.

## 16. Implementation Roadmap

Implement in stages. Each stage must be tested before proceeding.

### Stage 1 --- Processing Engine

-   [ ] Inspect and document the existing inference implementation.
-   [ ] Identify existing model loading and preprocessing code.
-   [ ] Create a central Model Registry.
-   [ ] Implement a dedicated GPU inference scheduler.
-   [ ] Implement bounded CPU preparation workers.
-   [ ] Implement model-compatible micro-batching.
-   [ ] Reuse existing inspection and result aggregation logic.
-   [ ] Add basic execution timing.

**Acceptance:** Existing single-image inspection still works through the
new engine and reuses loaded models.

### Stage 2 --- Persistent Job System

-   [ ] Add JobBatch.
-   [ ] Add InspectionJob.
-   [ ] Add processing metrics storage.
-   [ ] Implement atomic job claiming.
-   [ ] Implement validated job state transitions.
-   [ ] Implement bounded retry policy.
-   [ ] Implement cancellation of pending work.
-   [ ] Implement restart recovery.
-   [ ] Make result persistence idempotent.

**Acceptance:** Jobs survive backend restart and are not executed twice
accidentally.

### Stage 3 --- Mass Test

-   [ ] Add dedicated Mass Test page.
-   [ ] Support ZIP and multiple-file upload.
-   [ ] Implement safe, bounded ingestion.
-   [ ] Register one job per accepted image.
-   [ ] Display persisted progress.
-   [ ] Add pause, resume, cancel, and retry controls.
-   [ ] Display inspection results and errors.

**Acceptance:** A large dataset can be submitted without loading the
entire dataset into RAM.

### Stage 4 --- External API

-   [ ] Add single-job submission.
-   [ ] Add bulk-job submission.
-   [ ] Add job status endpoint.
-   [ ] Add batch status endpoint.
-   [ ] Add paginated result retrieval.
-   [ ] Add cancellation endpoint.
-   [ ] Add authentication and authorization.
-   [ ] Add rate limits and idempotency.
-   [ ] Document API request and response contracts.

**Acceptance:** An external client can submit work and retrieve results
without using the frontend.

### Stage 5 --- Engine Monitoring

-   [ ] Add queue-depth metrics.
-   [ ] Add throughput and latency metrics.
-   [ ] Add P50 and P95 measurements.
-   [ ] Add CPU and RAM monitoring.
-   [ ] Add GPU and VRAM monitoring where supported.
-   [ ] Add model load-time tracking.
-   [ ] Add engine health endpoint.

**Acceptance:** Operators can distinguish an idle engine, a busy engine,
a backed-up queue, and an unhealthy engine.

### Stage 6 --- Stress and Recovery Testing

-   [ ] Test 100 images.
-   [ ] Test 1,000 images.
-   [ ] Test 10,000 images.
-   [ ] Test concurrent API submissions.
-   [ ] Test mixed scanner units.
-   [ ] Test model load failures.
-   [ ] Test corrupt and unsupported files.
-   [ ] Test GPU memory pressure.
-   [ ] Restart backend during processing.
-   [ ] Verify no missing or duplicate completed results.
-   [ ] Record throughput, latency, and peak memory.

**Acceptance:** All accepted jobs reach a valid terminal state, or
remain recoverable after interruption. Resource usage remains within
configured limits.

## 17. Scope and Architectural Restrictions

For the initial prototype:

-   Keep the existing FastAPI backend.
-   Keep the existing database.
-   Use a persistent database-backed job queue.
-   Use bounded CPU worker pools.
-   Use one controlled GPU inference worker.
-   Reuse the existing model and inspection implementations.
-   Keep Mass Test and external API on the same pipeline.
-   Do not introduce Redis, Celery, or RabbitMQ prematurely.
-   Do not create duplicate inspection result tables.
-   Do not create a model instance for every image.
-   Do not create an unbounded thread or process per request.
-   Do not load entire datasets into RAM.
-   Do not silently convert processing failures into PASS results.
-   Do not change existing inspection decision rules as part of queue
    implementation.

Keep the queue and worker interfaces modular so future migration to a
message broker or multiple machines remains possible.

## 18. Instructions for Codex

Before changing code:

1.  Inspect the existing repository structure.
2.  Locate the FastAPI application and current inspection endpoints.
3.  Locate the existing inference pipeline, model loader, and
    scanner-unit/module configuration.
4.  Locate the existing database models and inspection result
    persistence logic.
5.  Identify which operations currently block API requests.
6.  Identify any existing background tasks, thread pools, or model
    caches.
7.  Produce a short implementation plan referencing actual files and
    functions.

Then implement incrementally.

### Mandatory implementation rules

-   Extend existing functionality; do not create a parallel inference
    engine.
-   Preserve existing single-image inspection behaviour and API
    contracts unless a migration is explicitly required.
-   Reuse existing model adapters and result schemas.
-   Make worker counts, queue limits, batch size, and wait timeout
    configurable.
-   Use safe database transaction boundaries.
-   Never hold database write transactions open during model inference.
-   Ensure each job has a durable identity.
-   Make job claiming and result persistence safe against duplicate
    execution.
-   Implement bounded queues and backpressure.
-   Keep errors observable and traceable.
-   Add tests for normal execution, concurrent submissions, failures,
    retries, cancellation, and restart recovery.
-   Do not claim stress-test completion without running the tests and
    reporting measured results.

### Required deliverables

1.  Working shared processing engine.
2.  Persistent job and batch system.
3.  Model Registry and GPU scheduler.
4.  Mass Test interface.
5.  External API integration.
6.  Engine monitoring.
7.  Automated tests.
8.  Updated setup and execution instructions.
9.  A benchmark report with actual measured results.

------------------------------------------------------------------------

## Final Objective

CLOCKIT must evolve from a single-image AI inspection application into a
reliable, high-throughput industrial inspection engine.

Whether an operator uploads 10,000 images or an external production-line
application submits inspections continuously, both must use the same
processing infrastructure.

**The core architectural principle is simple: accept work independently,
queue it durably, process it with controlled concurrency, reuse models,
and persist every outcome.**
