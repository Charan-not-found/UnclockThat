# CLOCKIT --- Product, Data, AI and Resource Specification

**Document type:** Product and technical architecture blueprint\
**Version:** 1.1 (technical-audit aligned revision)\
**Date:** 25 November 2026\
**Initial industry focus:** Steel, textiles, and automotive
manufacturing\
**Core product concept:** User-created, trainable, configurable AI
Scanner Units

------------------------------------------------------------------------

## 1. Executive summary

CLOCKIT is a platform for creating, training, deploying, evaluating, and
continuously improving configurable industrial inspection systems called
**Scanner Units**.

A Scanner Unit is a reusable inspection configuration. It contains one
or more analysis modules, each backed by a compatible AI model or
deterministic analysis method. A Scanner Unit can contain a single
module or several modules whose outputs are combined into one inspection
result. For the local prototype, modules execute sequentially by default;
parallel execution is an explicitly benchmark-gated optimization, not an
assumed capability.

A manufacturer creates a Scanner Unit by:

1.  Defining its name, description, industry, product, inspection
    target, and other metadata.
2.  Selecting one or more AI analysis modules from a model catalogue.
3.  Uploading a dataset, initially often a ZIP of images showing
    normal/acceptable products.
4.  Letting CLOCKIT validate and prepare the data.
5.  Training compatible models to learn the normal appearance or to
    learn labelled defect classes, depending on the selected model.
6.  Selecting the outputs required, such as anomaly maps, bounding
    boxes, segmentation masks, classifications, scores, measurements,
    and reports.
7.  Evaluating and activating a version of the Scanner Unit.
8.  Running inspections and collecting human feedback.
9.  Using validated corrections in controlled training iterations,
    evaluating a candidate model against the current model, and
    deploying only an approved version.

The main dashboard is therefore a **Scanner Unit management workspace**,
not merely an image-upload page or a generic statistics dashboard.

### The central product principle

> The Scanner Unit is the product. AI models are its building blocks.
> Datasets teach and validate it. Human feedback measures its real-world
> performance and supplies corrected examples. CLOCKIT manages its full
> lifecycle.

------------------------------------------------------------------------

## 2. Product vocabulary

Use these terms consistently in the codebase, UI, API, database, and
documentation.

  -----------------------------------------------------------------------
  Term                                Meaning
  ----------------------------------- -----------------------------------
  Scanner Unit                        A named, versioned inspection
                                      system created by a user

  Analysis Module                     One configured inspection
                                      capability inside a Scanner Unit

  Model Family                        An algorithm family, such as
                                      EfficientAD, PatchCore, or YOLO

  Model Artifact                      The trained weights/checkpoint and
                                      associated files

  Dataset                             A versioned collection of source
                                      data and annotations

  Training Run                        A reproducible execution of a
                                      model's training procedure

  Scanner Version                     An immutable snapshot of module
                                      configurations and model artifacts

  Inspection                          One execution of a Scanner Unit
                                      against a sample, part, batch, or
                                      production item

  Finding                             A predicted anomaly, defect,
                                      object, measurement, or quality
                                      issue

  Human Review                        A person's assessment of an
                                      inspection or finding

  Correction Record                   A human-confirmed correction linked
                                      to the original prediction and
                                      evidence

  Learning Iteration                  A controlled training/evaluation
                                      cycle using an updated dataset

  Candidate Model                     A newly trained model awaiting
                                      evaluation and approval

  Deployment                          The Scanner Version currently
                                      enabled for a given inspection
                                      environment
  -----------------------------------------------------------------------

A Scanner Unit must be independent of a single dataset or model file. It
should reference exact dataset versions, training runs, model artifacts,
and configuration versions so past results remain reproducible.

------------------------------------------------------------------------

## 3. Main user journeys

### 3.1 Create a Scanner Unit

The Scanner Creator should guide the user through a structured workflow.

**Step 1 --- Identity and scope**

Required or recommended fields:

-   Scanner name
-   Description and purpose
-   Industry: steel, textiles, automotive, or custom
-   Product family and product identifier
-   Component or inspection surface
-   Inspection stage or production station
-   Camera/sensor or input source, if known
-   Expected operating conditions
-   Owner/team and optional tags

**Step 2 --- Add analysis modules**

The user selects one or more modules from a catalogue. Each catalogue
entry must explain:

-   What the module does
-   Which data modalities it accepts
-   Whether it is normal-only, supervised, semi-supervised, or
    pretrained
-   What labels it requires
-   What outputs it can generate
-   Approximate compute requirements
-   Supported image sizes and formats
-   Known limitations
-   Whether training is supported in CLOCKIT or only inference
-   Whether the module can be chained with other modules

Do not present every model as interchangeable. A normal-only anomaly
detector and a supervised object detector have different data and
training requirements.

**Step 3 --- Upload and validate data**

Initially support ZIP upload for image datasets. The system should
extract files into managed storage, scan for invalid files, calculate
hashes, detect duplicates, inspect image metadata, and show a dataset
preview before training.

**Step 4 --- Configure training**

The training form should be generated from the selected model's declared
requirements. It should not assume every model trains on only normal
images.

**Step 5 --- Configure outputs**

The user selects supported output types. The UI should only offer
outputs the selected module can actually produce.

**Step 6 --- Train, evaluate, and activate**

Training creates a Training Run and Candidate Model. Evaluation compares
it with a baseline and applies acceptance criteria. Activation creates
or selects a Scanner Version for deployment.

### 3.2 Run an inspection

An inspection may receive:

-   One image
-   Multiple views of one part
-   A sequence or video-derived frames
-   A line-scan image of continuous material
-   A 3D scan or point cloud
-   Sensor/time-series data
-   Structured production metadata

The first release can focus on still images while designing the data
model so other modalities can be added without redesigning the Scanner
Unit concept.

The execution engine should:

1.  Identify the Scanner Unit and exact active version.
2.  Validate input modality, dimensions, and metadata.
3.  Run the configured modules in their required order or in parallel
    where appropriate.
4.  Normalize and store each module's outputs.
5.  Aggregate evidence using explicit, versioned rules.
6.  Apply product-specific acceptance criteria.
7.  Return a result such as **Pass**, **Fail**, or **Needs Review**.
8.  Store inputs, outputs, timing, model versions, and configuration for
    traceability.

### 3.3 Human review and correction

A reviewer must be able to mark:

-   Correct detection
-   False positive: flagged region is actually acceptable/normal
-   False negative: an actual defect was missed
-   Incorrect localization: the defect exists but the predicted region
    is wrong
-   Incorrect class: the defect was assigned the wrong category
-   Uncertain / needs expert review

For each correction, store the original prediction, selected finding,
human label, corrected region/class if applicable, reviewer, timestamp,
optional comment, and review status.

**Important:** A false-positive correction is useful training data, but
it must not automatically be treated as a complete training instruction
for every model family. For a normal-only anomaly detector, a validated
false-positive image/region may be incorporated into an expanded normal
training set or used in a model-specific adaptation strategy. For a
supervised detector, it may become a negative/background example or be
used with corrected annotations. The exact learning method belongs to
the module adapter.

### 3.4 Learning iteration

A user can collect corrections and launch an iteration when ready.

A learning iteration should:

1.  Select approved correction records.
2.  Build a new immutable dataset snapshot.
3.  Check for conflicting labels, duplicates, leakage, and class
    imbalance.
4.  Execute the model-specific training or adaptation strategy.
5.  Evaluate the candidate on a fixed holdout set and a representative
    challenge set.
6.  Compare it with the currently deployed version.
7.  Record metric changes and regression checks.
8.  Require approval before deployment.
9.  Keep the previous model version available for rollback.

Do not retrain blindly on one correction image. One image can be stored
immediately, but training should normally use a batch of corrections and
a stable replay/validation set. This reduces the risk of overfitting and
catastrophic forgetting.

### 3.5 Explicit training strategy contract

Every adapter must declare support independently for these operations:

1. **Initial training from scratch** — create a model from initialized
   parameters or a documented pretrained starting point.
2. **Fine-tuning** — update an existing compatible checkpoint using a
   labelled or otherwise model-appropriate dataset.
3. **Incremental adaptation** — update a deployed model without a full
   retraining cycle, only where the algorithm explicitly supports it.
4. **Full retraining** — train a new candidate using a complete selected
   training snapshot.
5. **Evaluation only** — run evaluation without modifying model weights.

Do not infer support from the fact that a Python package exposes a
training command. EfficientAD's normal-only workflow learns normal
appearance from approved normal samples. Conventional YOLO detection
training requires defect/object examples with class labels and bounding
boxes; segmentation requires compatible masks/polygons. A reviewed
false-positive from a normal-only detector may be eligible as a normal
sample after whole-image/region review. A false-negative for a detector
requires a corrected defect annotation where possible. A correction
image is not a universal training instruction.

The training UI and API must be generated from the selected adapter's
capability declaration and reject unsupported strategy requests.

------------------------------------------------------------------------

## 4. Scanner Unit architecture

A Scanner Unit is composed of modules and orchestration rules.

### 4.1 Example: Steel Surface Scanner

-   Module A: normal-only anomaly detection
-   Module B: supervised defect segmentation
-   Module C: optional surface/edge measurement
-   Output policy: anomaly map, defect mask, defect class, confidence,
    affected area
-   Aggregation policy: combine evidence and apply
    steel-grade/product-specific acceptance rules

### 4.2 Example: Textile Fabric Scanner

-   Module A: texture anomaly detection
-   Module B: supervised defect localization/classification
-   Module C: optional repeat-pattern or weave consistency analysis
-   Output policy: heatmap, defect region, defect type, affected area,
    position along fabric roll

### 4.3 Example: Automotive Component Scanner

-   Module A: component/part presence and assembly verification
-   Module B: anomaly detection for unexpected surface or assembly
    variation
-   Module C: supervised defect detection/segmentation
-   Module D: optional OCR/marking verification or dimensional/3D
    measurement
-   Output policy: boxes/masks, missing/misaligned component findings,
    OCR result, measurements, quality decision

These are example compositions, not mandatory fixed pipelines. A user
may create a Scanner Unit with only one module.

### 4.4 Module contract

Every analysis module should implement a common interface, while
declaring its own capabilities.

Conceptual contract:

``` python
class AnalysisModule:
    def validate_config(self, config): ...
    def validate_dataset(self, dataset_manifest): ...
    def prepare_data(self, dataset_version): ...
    def train(self, training_config, dataset_version): ...
    def evaluate(self, model_artifact, evaluation_dataset): ...
    def load(self, model_artifact, runtime_config): ...
    def predict(self, input_sample, context): ...
    def postprocess(self, raw_output, output_config): ...
    def explain_capabilities(self): ...
```

A module manifest should declare:

-   `module_type`
-   `model_family`
-   supported `tasks`
-   accepted `modalities`
-   supported input formats
-   training paradigm
-   required and optional labels
-   supported output types
-   training parameters and defaults
-   inference parameters
-   hardware requirements
-   dependency/runtime requirements
-   version and compatibility information

The platform should validate a Scanner Unit before training or
activation. For example, it should reject a request for bounding boxes
from a model that only generates an anomaly map unless another
compatible module provides boxes.

------------------------------------------------------------------------

## 5. Data CLOCKIT must understand

CLOCKIT should use a modality-aware data model. Do not treat every input
as an ordinary RGB image.

### 5.1 Core visual data

  ------------------------------------------------------------------------
  Data type               Description             Typical use
  ----------------------- ----------------------- ------------------------
  RGB image               Three-channel colour    Paint, textile colour,
                          image                   assembly, labels,
                                                  general appearance

  Grayscale image         Single-channel          Steel surfaces,
                          intensity image         monochrome cameras,
                                                  X-ray-like image exports

  High-resolution         Full-frame image of a   Components, panels,
  area-scan image         discrete part           machined parts

  Line-scan image         Image assembled         Steel strip, textile
                          line-by-line as         rolls, paper/web
                          material moves          material

  Multi-view images       Several views of the    Automotive components,
                          same physical item      castings, assemblies

  Macro/close-up image    High-magnification      Fine scratches, cracks,
                          local view              weave defects,
                                                  solder/connector details

  UV/IR/multispectral     Images captured at      Coating, contamination,
  image                   selected wavelengths    material or thermal
                                                  differences where
                                                  validated

  Thermal image           Temperature             Thermal process or
                          distribution            component hot-spot
                                                  inspection

  Depth map               Per-pixel               Shape, surface height,
                          distance/depth          deformation

  3D point cloud/mesh     Spatial geometry        Dimensional and surface
                                                  geometry inspection

  X-ray/radiographic      Internal                Internal
  image                   density/structure image weld/casting/component
                                                  inspection, where
                                                  appropriate

  Microscopy image        High-magnification      Surface/material
                          material image          microstructure
                                                  applications
  ------------------------------------------------------------------------

A modality must include calibration and acquisition metadata. A thermal
image without temperature calibration, or a 3D point cloud without
coordinate scale, may not support reliable measurement.

### 5.2 Structured metadata

Every sample should support optional metadata:

-   Sample ID and part/roll/coil/vehicle identifier
-   Product family, SKU, revision, and material/grade
-   Manufacturing site, line, machine, station, shift
-   Timestamp and batch/lot
-   Camera/sensor ID and calibration version
-   Lens, lighting, exposure, resolution, frame rate, and capture
    settings
-   Material thickness, width, length, dimensions, and weight where
    relevant
-   Process settings such as speed, temperature, pressure, tension, or
    machine recipe
-   Operator or reviewer ID where permitted
-   Environmental conditions when relevant
-   Supplier, material batch, and traceability fields
-   Ground-truth label and annotation provenance

Keep personally identifying worker information out of image metadata
unless it is genuinely required and governed by the site's privacy
policy.

### 5.3 Annotation and ground-truth types

Support multiple annotation levels:

  -----------------------------------------------------------------------
  Annotation                          Meaning
  ----------------------------------- -----------------------------------
  Image-level label                   Whole sample is normal/defective or
                                      belongs to a class

  Classification label                Sample belongs to a defined
                                      defect/product category

  Bounding box                        Rectangular defect/object region

  Polygon                             Region outline

  Pixel mask                          Per-pixel defect segmentation

  Rotated box                         Defect/object whose orientation
                                      matters

  Keypoints                           Defined points/features on a
                                      component

  Measurement                         Numeric value with unit and
                                      calibration reference

  Sequence label                      Label associated with a frame/time
                                      interval

  Part-level label                    Overall part disposition

  Multi-view association              Links views to the same physical
                                      part
  -----------------------------------------------------------------------

Store label provenance: human, imported, rule-generated, or
model-suggested. Model-suggested annotations must not silently become
ground truth.

------------------------------------------------------------------------

## 6. Industry data requirements

The three industry profiles below are starting templates. Actual
requirements depend on the product, material, production process, defect
specification, camera geometry, line speed, and quality standards agreed
with the manufacturer.

## 6.1 Steel industry

### Typical inspection targets

-   Hot-rolled and cold-rolled strip
-   Steel sheets and plates
-   Coils and slit strips
-   Pipes and tubes
-   Billets and slabs
-   Cast steel components
-   Welded joints and fabricated parts
-   Coated, galvanized, or painted steel

### Visual defect categories to support

The defect taxonomy must be configurable by product and process. Common
example categories include:

-   Surface scratches and scoring
-   Cracks and tears
-   Pits and pitting
-   Rolled-in scale
-   Inclusions
-   Patches and stains
-   Rust/corrosion
-   Laminations or surface separations where visually observable
-   Dents and handling damage
-   Coating gaps, blisters, or uneven coating
-   Weld surface irregularities
-   Edge cracks and edge damage

Do not assume that a camera image can reliably identify internal
defects. Internal cracks, inclusions, or weld flaws may require suitable
non-destructive testing (NDT) modalities and qualified procedures.

### Data to collect

**Primary visual inputs**

-   High-resolution grayscale or colour surface images
-   Line-scan images for moving strip/sheet
-   Area-scan images for discrete plates, billets, pipes, and components
-   Images from top, bottom, and edge cameras where applicable
-   Consistent lighting and exposure metadata
-   Surface position, strip/coil coordinates, line speed, and material
    grade
-   Thickness, width, and process/lot metadata

**Optional complementary inputs**

-   3D height/depth maps for dents, waviness, and surface profile
-   Thermal data for validated thermal-process use cases
-   Ultrasonic, eddy-current, or radiographic inspection records for
    relevant internal/material integrity applications
-   Process sensor data such as temperature, rolling force, tension,
    speed, and vibration

These complementary modalities should be integrated as separate data
sources with their own calibration, units, and validated models. They
should not be mixed into a 2D image model without a deliberate fusion
design.

### Recommended model families

  -----------------------------------------------------------------------------
  Need                    Candidate model family        Training data
  ----------------------- ----------------------------- -----------------------
  Discover previously     EfficientAD, PatchCore,       Primarily normal
  unseen surface          PaDiM, FastFlow               images; abnormal
  anomalies                                             samples for evaluation

  Pixel-level anomaly     EfficientAD/PatchCore-style   Normal images for
  localization            anomaly maps; segmentation    anomaly methods; masks
                          models                        for supervised
                                                        segmentation

  Known defect detection  YOLO detection, RT-DETR       Defect images with
                                                        bounding boxes and
                                                        class labels

  Exact defect shape/area YOLO segmentation, U-Net,     Pixel masks/polygons
                          DeepLab-style segmentation    

  Whole-image defect      CNN/ViT classifier            Image-level class
  classification                                        labels

  Surface                 3D anomaly or point-cloud     Depth/point-cloud data
  profile/geometry        methods; calibrated classical and geometry labels
                          vision                        

  Process drift or        Time-series models and        Timestamped sensor data
  equipment condition     statistical process           and event labels
                          monitoring                    
  -----------------------------------------------------------------------------

**Recommended initial steel Scanner Unit:** normal-only anomaly
detection plus optional supervised segmentation for known defect
classes. Start with controlled surface-imaging conditions and a clearly
defined steel product/grade.

## 6.2 Textile industry

### Typical inspection targets

-   Woven fabric
-   Knitted fabric
-   Non-woven material
-   Denim
-   Technical textiles
-   Printed/dyed fabric
-   Fabric rolls and continuous webs
-   Finished garments and cut panels

### Visual defect categories to support

-   Broken or missing yarn
-   Holes and tears
-   Snags and pulls
-   Slubs and thick/thin places
-   Misweaves and pattern irregularities
-   Stains and contamination
-   Colour variation and shade bands
-   Printing defects, missing print, and misregistration
-   Creases and wrinkles
-   Pilling or surface wear
-   Edge defects and selvedge problems

Textile defects are strongly affected by fabric construction, weave/knit
pattern, colour, texture, stretch, illumination, and viewing scale. A
model trained on one fabric type should not be assumed to generalize to
another.

### Data to collect

**Primary visual inputs**

-   High-resolution RGB images for colour, stains, printing, and
    appearance
-   Grayscale images where texture contrast is more useful
-   Line-scan images for continuous fabric inspection
-   Multiple illumination angles where texture or surface relief matters
-   Macro images for small yarn-level defects
-   Images with known scale or calibrated pixel-to-millimetre mapping

**Production metadata**

-   Fabric type and construction
-   Fibre/material composition
-   Weave or knit pattern
-   Yarn count/density where available
-   Colourway, dye lot, print design, and pattern repeat
-   Fabric width and roll length
-   Machine/loom/knitting machine ID
-   Line speed, tension, and inspection position
-   Roll ID, batch, and defect position along the roll

**Optional complementary inputs**

-   Spectral/colour measurements for shade consistency
-   3D or structured-light data for texture/height where justified
-   Process sensor streams for loom or machine monitoring

### Recommended model families

  ------------------------------------------------------------------------
  Need                    Candidate model family   Training data
  ----------------------- ------------------------ -----------------------
  Unknown                 EfficientAD, PatchCore,  Normal images; defects
  texture/appearance      PaDiM, DRAEM             for validation
  defects                                          

  Known defect            YOLO detection           Bounding boxes and
  localization                                     class labels

  Fine defect boundaries  U-Net, DeepLab-style,    Pixel masks/polygons
                          YOLO segmentation        

  Fabric type, shade, or  CNN/ViT classifier       Image-level labels
  defect category                                  

  Repeat-pattern          Classical                Normal pattern
  inconsistency           frequency/texture        references and
                          methods plus learned     annotated examples
                          features                 

  Roll-level defect       Detection/segmentation   Line-scan images and
  mapping                 plus coordinate tracking roll-position metadata
  ------------------------------------------------------------------------

**Recommended initial textile Scanner Unit:** normal-only texture
anomaly detection with heatmap output, followed by optional defect
classification/localization when the customer has labelled examples.

## 6.3 Automotive industry

Automotive inspection spans many distinct tasks. CLOCKIT should organize
these as product/component inspection profiles rather than assuming one
model can inspect an entire vehicle.

### Typical inspection targets

-   Body panels and painted surfaces
-   Welded structures and joints
-   Cast, forged, and machined components
-   Engine and transmission components
-   Brake and suspension components
-   Connectors, wiring, and electronic assemblies
-   Printed circuit boards and control units
-   Fasteners and assembly completeness
-   Interior trim, upholstery, and glass
-   Tyres and wheel assemblies
-   Labels, serial numbers, barcodes, and markings

### Visual defect and assembly categories

-   Scratches, dents, chips, and paint defects
-   Corrosion and coating irregularities
-   Weld appearance defects
-   Casting/machining surface defects
-   Missing, extra, or misplaced components
-   Incorrect orientation or assembly
-   Connector/pin damage
-   Seal/gasket misplacement
-   Incorrect fastener presence or position
-   Label/marking mismatch or unreadable code
-   Glass chips/cracks and trim defects
-   Dimensional or geometric deviations

Some safety-critical automotive checks require validated measurement
systems, controlled procedures, and human/engineering approval. A model
prediction alone must not be treated as certification or proof of
compliance.

### Data to collect

**Primary visual inputs**

-   RGB area-scan images for discrete parts and assemblies
-   Multi-camera views for different surfaces and angles
-   Line-scan images for continuous materials or selected moving
    surfaces
-   High-magnification images for connectors, pins, welds, and small
    details
-   Depth maps or 3D scans for geometry and fit
-   Thermal images for specifically validated thermal inspection tasks
-   X-ray images for appropriate internal inspection applications

**Production and traceability metadata**

-   Vehicle/component/part ID
-   Part number, revision, and variant
-   Assembly station and process step
-   Plant, line, machine, and timestamp
-   Supplier and material batch
-   Camera/sensor position and calibration
-   Assembly recipe and expected bill-of-materials configuration
-   Torque/force/pressure measurements where relevant
-   Dimensional measurements and tolerances
-   Software/firmware or configuration revision for electronic
    assemblies
-   Rework and final disposition history

**Optional non-visual data**

-   Torque-angle curves
-   Press-fit force/displacement curves
-   Vibration/acoustic signals
-   Temperature/current/voltage traces
-   End-of-line test measurements
-   PLC and machine event data

These should be represented as separate structured/time-series inputs
and joined to the same part or production event using traceable IDs and
timestamps.

### Recommended model families

  -----------------------------------------------------------------------
  Need                    Candidate model family  Training data
  ----------------------- ----------------------- -----------------------
  Unknown surface         EfficientAD, PatchCore, Normal images; defects
  anomalies               PaDiM                   for validation

  Known defect/object     YOLO detection, RT-DETR Bounding boxes and
  detection                                       class labels

  Exact defect/part       YOLO segmentation,      Pixel masks/polygons
  regions                 U-Net, DeepLab-style    

  Part/assembly           CNN/ViT classifier      Image-level labels
  classification                                  

  Presence, count, and    Object detection plus   Expected objects and
  placement checks        rule/geometry checks    annotations

  Text, label, and code   OCR models plus         Text regions, expected
  verification            deterministic           strings, OCR ground
                          comparison              truth

  Dimensional inspection  Calibrated 2D/3D vision Calibration targets,
                          and geometric           CAD/nominal geometry,
                          algorithms              tolerances

  Internal inspection     Modality-specific       Correctly labelled
                          X-ray/CT analysis       radiographic data

  Process signal          Statistical process     Timestamped process
  monitoring              control and time-series signals and
                          models                  failure/event labels
  -----------------------------------------------------------------------

**Recommended initial automotive Scanner Unit:** choose one narrowly
defined component and inspection station. Combine a normal-only anomaly
module with a supervised detection/segmentation or OCR module only when
its task and labelled dataset justify it.

------------------------------------------------------------------------

## 7. AI model catalogue

CLOCKIT should have a model catalogue with capability metadata. The
following are recommended model families to consider; this is not a
requirement to implement every model in the first release.

### 7.1 Normal-only / unsupervised anomaly detection

These are the closest fit to the initial workflow where a user uploads
normal/acceptable images and asks the model to learn normal appearance.

  -------------------------------------------------------------------------------------
  Model family      Purpose                         Typical output    Notes
  ----------------- ------------------------------- ----------------- -----------------
  EfficientAD       Fast industrial anomaly         Image score and   Strong candidate
                    detection                       anomaly map       for a first
                                                                      implementation

  PatchCore         Feature-memory-based anomaly    Anomaly score/map Useful baseline;
                    detection                                         memory/storage
                                                                      and inference
                                                                      cost need
                                                                      measurement

  PaDiM             Distribution modelling of       Anomaly score/map Useful classical
                    pretrained patch features                         baseline

  FastFlow          Normalizing-flow anomaly        Anomaly score/map Alternative model
                    detection                                         family

  DRAEM             Reconstruction/discriminative   Anomaly           Training strategy
                    anomaly detection               segmentation      differs from
                                                                      simple
                                                                      normal-only
                                                                      approaches
  -------------------------------------------------------------------------------------

Model choice must be based on representative customer data, latency,
image size, defect scale, hardware, and evaluation results---not model
popularity alone.

### 7.2 Supervised detection and segmentation

  -----------------------------------------------------------------------
  Model family            Task                    Required annotation
  ----------------------- ----------------------- -----------------------
  YOLO detection          Locate and classify     Bounding boxes + class
                          known defects/objects   

  YOLO segmentation       Instance-level defect   Polygon/mask + class
                          masks                   

  RT-DETR                 Object detection        Bounding boxes + class

  U-Net                   Pixel-level             Pixel masks
                          segmentation            

  DeepLab-style networks  Semantic segmentation   Pixel masks

  CNN/ViT classifier      Image/patch             Image-level class
                          classification          labels
  -----------------------------------------------------------------------

Supervised detection and segmentation generally need examples of defects
and appropriate annotations. A ZIP containing only normal images is not
enough to train a conventional defect-class detector.

### 7.3 Other useful analysis modules

-   OCR/text recognition for labels, markings, serials, and codes
-   Classical computer vision for edges, dimensions, alignment, and
    geometric rules
-   3D point-cloud/mesh analysis for shape and surface profile
-   Time-series anomaly detection for process signals
-   Sensor fusion for joining visual findings with process/measurement
    evidence
-   Similarity/retrieval models for finding comparable historical
    defects

### 7.4 Model catalogue fields

Every model entry should define:

-   Display name and technical family
-   Task category
-   Training paradigm
-   Accepted modalities
-   Accepted image dimensions/ranges
-   Required training data
-   Optional training data
-   Annotation schema
-   Supported output types
-   Training entry point and inference entry point
-   Supported device types (CPU/GPU)
-   Estimated VRAM/RAM needs
-   Dependencies and licence
-   Model version and framework version
-   Known limitations
-   Evaluation metrics
-   Export/deployment formats
-   Whether incremental learning is supported, or whether retraining is
    required
-   Required dataset directory/manifest structure and annotation schema
-   Explicit support flags for initial training, fine-tuning, incremental
    adaptation, full retraining, and evaluation-only
-   Supported preprocessing pipeline IDs and parameter schema
-   Expected input dimensions, channel order, colour space, normalization,
    tiling/overlap constraints, and output coordinate convention
-   Supported inference output schema and post-processing version
-   Estimated peak VRAM and RAM by workload class (training/inference),
    input size, and batch size; estimates must be benchmarked and labelled
-   Minimum/maximum supported batch size and safe device options
-   Artifact file list, checksum, format, and model/runtime compatibility
-   Adapter implementation version, test status, and integration status
-   Compatibility constraints with other modules and orchestration stages

A model is **integrated** only when a functioning adapter validates its
inputs, performs real inference, emits standardized outputs, handles
errors, persists artifact metadata, and passes adapter/integration tests.
A downloaded package or checkpoint alone is `available`, not `integrated`.

Initial implementation priority:

| Priority | Model/module | Initial supported scope |
|---|---|---|
| 1 | EfficientAD | Normal-only anomaly detection; training and inference adapter |
| 1 | YOLO | Supervised object detection; inference first, training only after annotation/data pipeline validation |
| 1 | OpenCV | Deterministic image processing, measurements, and rule-based checks |
| 2 | PatchCore | Anomaly detection after memory/runtime benchmarking |
| 2 | PaDiM | Anomaly detection after adapter and evaluation validation |
| 2 | YOLO segmentation | Segmentation when polygon/mask annotations and evaluation are available |

### 7.5 Output types

Output configuration should be capability-driven.

  -----------------------------------------------------------------------
  Output                              Meaning
  ----------------------------------- -----------------------------------
  Anomaly heatmap                     Pixel/patch-level anomaly intensity

  Overlay                             Original image with visualized
                                      findings

  Bounding boxes                      Rectangular object/defect regions

  Segmentation masks                  Pixel-level defect regions

  Contours/polygons                   Boundary representation

  Classification                      Predicted class and score

  Anomaly score                       Unusualness score, not
                                      automatically a probability

  Confidence                          Model-specific confidence,
                                      calibrated where possible

  Measurements                        Area, length, width, distance,
                                      angle, height, etc. with units

  OCR result                          Extracted text and recognition
                                      confidence

  Quality decision                    Pass, fail, or needs review based
                                      on explicit rules

  Report                              Structured result and
                                      human-readable summary
  -----------------------------------------------------------------------

Do not label an anomaly score as a probability unless it has been
calibrated and validated as such.

------------------------------------------------------------------------

## 8. Dataset and ZIP requirements

### 8.1 First-release ZIP workflow

The first release can accept a ZIP containing normal images. However,
the upload UI must explain which selected modules can use normal-only
data and which need labelled defect examples.

A simple accepted structure could be:

``` text
customer_dataset.zip
├── dataset_manifest.json          # optional but recommended
├── normal/
│   ├── sample_0001.jpg
│   ├── sample_0002.jpg
│   └── ...
├── defective/                     # optional
│   ├── sample_1001.jpg
│   └── ...
├── annotations/                   # optional
│   ├── instances.json
│   └── masks/
└── metadata/
    └── samples.csv                 # optional
```

For normal-only anomaly detection, `normal/` is the training source.
Defective samples, if provided, should be reserved for validation/test
unless the chosen model's documented training method explicitly uses
them.

For supervised detection/segmentation, require compatible annotations
and class definitions. The platform should provide an annotation
workflow or supported import formats.

### 8.2 Manifest example

``` json
{
  "dataset_name": "steel_surface_normal_v1",
  "industry": "steel",
  "product": "hot_rolled_strip",
  "modality": "grayscale",
  "training_paradigm": "normal_only_anomaly_detection",
  "image_count": 2400,
  "image_format": ["png", "jpg", "tif"],
  "image_dimensions": "variable",
  "capture_source": "line_scan_camera",
  "created_at": "2026-11-25",
  "labels": {
    "normal": "acceptable surface",
    "defective": "not used for normal-only training"
  }
}
```

The manifest should be optional for basic uploads but strongly
encouraged for industrial traceability. Values must be validated against
the actual extracted archive.

### 8.3 Data validation

The ingestion pipeline should check:

-   ZIP integrity and safe extraction
-   File size and archive expansion limits
-   Allowed extensions and actual file signatures
-   Corrupt/unreadable images
-   Unsupported colour modes
-   Resolution and aspect ratio
-   Duplicate files using hashes
-   Near-duplicates where practical
-   Empty/blank images
-   Extreme brightness/contrast and blur warnings
-   EXIF and orientation handling
-   Label/annotation consistency
-   Missing images referenced by annotations
-   Train/validation/test leakage
-   Sample and class counts
-   Metadata consistency

Never trust filenames or folder names as the only source of ground
truth. Show a validation report and let the user resolve ambiguous
labels.

### 8.3.1 First-class preprocessing pipeline

Preprocessing is a versioned pipeline, not a hidden side effect of a
model adapter. The pipeline stages are:

1. ZIP upload with configured archive/file-size limits.
2. Safe extraction into a quarantine/staging directory (reject path
   traversal, symlinks where unsafe, archive bombs, and unsupported
   entries).
3. File signature and extension validation.
4. Corrupt/unreadable image detection.
5. Exact duplicate detection by cryptographic file hash.
6. Optional near-duplicate detection using image similarity/perceptual
   hashes; retain the method, threshold, and candidate pairs.
7. EXIF orientation correction while preserving original source files.
8. Image dimensions, aspect ratio, channel count, and colour-mode checks.
9. Color-mode normalization only according to a selected pipeline.
10. Brightness, contrast, blank-image, and blur quality checks that
    produce warnings/rejections with recorded thresholds.
11. Resolution policy: reject, resize, pad, crop, or tile as explicitly
    configured; tiling records tile coordinates and overlap.
12. Dataset splitting with a fixed seed and, where metadata permits,
    grouping by part/lot/roll/production batch to reduce leakage.
13. Leakage checks across train/validation/test using hashes, near-
    duplicate candidates, and group identifiers.
14. Model-specific transforms, normalization, channel order, and tensor
    shape validation.
15. Immutable DatasetVersion creation with a complete sample manifest.

Original uploads are immutable and retained separately from derived
files. Every processed sample manifest entry records source path/hash,
processed path/hash, dimensions, labels/annotation references, split,
preprocessing pipeline/version, warnings, and provenance. Store the full
preprocessing configuration with the DatasetVersion. Do not apply one
universal resize, normalization, or color conversion to all model
families.

The accepted initial archive layout includes `normal/`, `defective/`,
`annotations/`, and `metadata/samples.csv` (all but the normal folder may
be optional for a normal-only workflow). For normal-only anomaly
detection, defective samples are generally evaluation/test material,
not normal training data. For supervised detection/segmentation,
require compatible labels and annotation files before enabling training.

Before training, generate a dataset validation report containing counts
by split/class, invalid files, duplicate and near-duplicate findings,
leakage warnings, annotation consistency, quality warnings, and the
selected adapter's compatibility result. Training must be blocked when
required validation checks fail; warnings may be accepted only with an
explicit recorded override.

### 8.4 Dataset versioning

Every dataset change should create a new immutable version or snapshot.
Store:

-   Original uploaded archive reference and checksum
-   Extracted file manifest
-   Per-file hash and metadata
-   Label/annotation version
-   Data split definition
-   Preprocessing configuration
-   Source/provenance
-   Created-by and created-at
-   Dataset validation report

Do not overwrite a dataset version used by a deployed Scanner Version.

------------------------------------------------------------------------

## 9. Human feedback and continuous learning

### 9.1 Review labels

At minimum:

-   Correct prediction
-   False positive
-   False negative
-   Incorrect class
-   Incorrect localization
-   Partially correct
-   Uncertain / escalate

For false positives, the reviewer should be able to confirm whether the
entire image is normal or only the highlighted region is normal. This
distinction matters: an image can contain both normal and defective
regions.

For false negatives, the reviewer should be able to draw or correct a
bounding box/mask and assign a defect class where known.

### 9.2 Correction record

A correction record should include:

-   Inspection ID
-   Scanner Unit and Scanner Version
-   Module and model artifact version
-   Original input/sample ID
-   Original prediction and output references
-   Human review label
-   Corrected class/region/measurement
-   Reviewer and timestamp
-   Review confidence or approval state
-   Eligibility for future training
-   Dataset snapshot/learning iteration that consumed it

### 9.3 Learning iteration controls

The user should be able to:

-   Review pending corrections
-   Filter by module, defect category, product, line, and date
-   Select approved records for a learning iteration
-   Preview the dataset changes
-   Choose a supported training strategy
-   Set compute limits and training parameters
-   Start, cancel, and monitor the run
-   Compare candidate and current versions
-   Approve or reject deployment

### 9.4 Evaluation and release gates

Use a stable, representative holdout set that is not silently absorbed
into training. Track metrics appropriate to each task:

**Anomaly detection** - Image-level AUROC/AP where appropriate -
Pixel-level AUROC/AP - PRO or region-overlap metrics where appropriate -
False-positive rate at a chosen operating threshold -
Per-product/per-condition performance

**Object detection** - Precision, recall, F1 - mAP at defined IoU
thresholds - Per-class performance - False positives per image/part

**Segmentation** - IoU - Dice/F1 - Precision and recall by class -
Boundary quality where needed

**Classification** - Confusion matrix - Per-class precision/recall/F1 -
Calibration metrics

**Production performance** - Latency percentiles - Throughput -
Memory/VRAM use - Failure rate - Human override rate - Performance by
shift, line, product, material batch, and capture condition

A single overall accuracy number is not sufficient for industrial
inspection. Accuracy can look high when defects are rare while the model
misses important defects.

### 9.5 Avoid misleading metrics

Human feedback is useful only when the labels are reliable and the
sample selection is understood. If humans review only flagged images,
the resulting metrics are biased and cannot estimate the true
false-negative rate. CLOCKIT should periodically include randomly
sampled unflagged/accepted items for review, as well as known challenge
samples, to measure missed defects.

------------------------------------------------------------------------

## 10. Scanner orchestration and decision logic

The orchestration engine should be separate from individual model
implementations.

It must support:

-   One-module Scanner Units
-   Multi-module Scanner Units
-   Sequential stages
-   Parallel independent modules only when explicitly enabled after resource benchmarking
-   Conditional execution
-   Multiple views of one part
-   Repeated scans or stations
-   Module-specific timeouts and error handling
-   Retry policies
-   Output normalization
-   Evidence aggregation
-   Human-review routing
-   Versioned decision rules

### 10.1 Keep model outputs separate from quality decisions

A model should report evidence, not independently decide manufacturing
disposition unless the application has explicitly configured and
validated that responsibility.

Example:

-   Anomaly detector: anomaly score and heatmap
-   Detector: class, box, and confidence
-   Segmentation model: mask and area
-   Measurement module: dimension and unit
-   Decision engine: applies approved tolerances and business rules
-   Final status: Pass / Fail / Needs Review

### 10.2 Multi-scan aggregation

A physical item may have front, back, edge, and close-up scans. Link
them to one `part_inspection` record.

Aggregation rules must account for:

-   Whether scans refer to the same physical item
-   Coverage and missing views
-   Coordinate transformations between views
-   Duplicate findings across scans
-   Severity/tolerance rules
-   Model confidence and calibration
-   Conflicting evidence
-   Required human review

Do not simply average scores from different models or views. Scores may
have different meanings and scales.

### 10.3 Evidence and decision semantics

Keep the following fields separate in normalized findings and persisted
inspection evidence:

- `anomaly_intensity`: anomaly-map or anomaly-score magnitude, with its
  model-specific scale and threshold context.
- `model_confidence`: confidence emitted by a classifier/detector; record
  whether it is calibrated. Do not call an uncalibrated score a probability.
- `defect_class` and `defect_location`: taxonomy identifier and image/part
  coordinate representation.
- `defect_size`: pixel area or calibrated physical size with units and
  calibration provenance.
- `physical_severity`: product/defect-specific severity category derived
  from approved criteria, not directly from anomaly intensity.
- `acceptance_criteria`: versioned product, grade, station, and defect
  tolerances.
- `inspection_decision`: `PASS`, `FAIL`, or `NEEDS_REVIEW`.

The decision engine consumes typed evidence through explicit, versioned
rules. Each rule declares input types, thresholds, missing-evidence
behavior, conflict behavior, and the reason code emitted. It must not
average EfficientAD anomaly scores with YOLO detection confidences. Where
normalization or calibration is unavailable, preserve the raw value and
its semantics. Missing modules, timeouts, or contradictory evidence must
route to a configured safe outcome (normally `NEEDS_REVIEW`) rather than
silently becoming `PASS`.


------------------------------------------------------------------------

## 11. Resources required

This section lists the capabilities and infrastructure CLOCKIT needs.
Actual compute sizing depends on image resolution, model choice,
throughput, concurrency, and training frequency. Benchmark with
representative customer data before promising a fixed hardware
specification.

### 11.1 Development stack

  -----------------------------------------------------------------------
  Area                                Recommended technology / capability
  ----------------------------------- -----------------------------------
  Backend API                         Python with FastAPI

  Frontend                            React + TypeScript

  Database                            SQLite for the local prototype; a
                                      production database migration is a
                                      later, separately approved phase

  ORM/migrations                      SQLAlchemy + Alembic

  ML framework                        PyTorch

  Computer vision                     OpenCV, Pillow, torchvision

  Detection/segmentation              A maintained framework such as
                                      Ultralytics, subject to licence
                                      review

  Data validation                     Pydantic and explicit dataset
                                      validators

  Background jobs                     In-process bounded job runner for
                                      the local prototype; external worker
                                      infrastructure is deferred

  Artifact storage                    Local filesystem for development;
                                      S3-compatible object storage for
                                      production

  Experiment tracking                 MLflow or equivalent

  Model registry                      CLOCKIT database metadata plus
                                      artifact storage; optionally MLflow
                                      registry

  Monitoring/logging                  Structured logs, metrics, job
                                      status, error tracking

  Packaging                           Native local execution for the
                                      prototype; containers are optional
                                      and not a prerequisite

  Testing                             pytest, API integration tests,
                                      model adapter tests, frontend tests
  -----------------------------------------------------------------------

These are capability options, not prototype dependencies. The initial
prototype remains a single local application using SQLite and local file
storage. Do not require PostgreSQL, Redis, Celery/RQ, Docker, cloud object
storage, or microservices to complete the first end-to-end Scanner Unit.

### 11.2 Hardware

**Initial local development target**

- 16 GB system RAM.
- Four CPU cores.
- NVIDIA RTX 3050 GPU; detect the actual installed VRAM at runtime
  because RTX 3050 variants differ.
- Local execution only, with SQLite metadata persistence and local file
  storage.
- SSD storage is recommended for datasets, checkpoints, and image
  artifacts.

This hardware is the prototype constraint, not a general recommendation
for production throughput. Benchmark the selected models using the actual
image dimensions and training settings before fixing performance claims.

**Model training and inference**

- CUDA GPU execution is preferred when the adapter supports it and the
  ResourceManager admits the workload.
- VRAM/RAM requirements vary with architecture, training versus inference,
  image resolution, tiling, and batch size.
- CPU fallback is available only for adapters/configurations that declare
  and pass CPU tests.
- Record GPU model and detected VRAM, CPU, available RAM, CUDA, driver,
  PyTorch, adapter, and runtime versions for every relevant run.

**Production**

Production CPU/GPU sizing, edge deployment, worker topology, and storage
infrastructure are deferred until a real deployment profile exists.
They must be selected from measured throughput, latency, availability,
and retention requirements rather than made prerequisites for the local
prototype.

**Storage**

Keep original uploads, extracted source data, processed dataset versions,
model checkpoints, inference artifacts, and reports separately. Use
checksums and manifests for traceability. Keep large binaries in local
file storage and database rows as metadata/references. Retention,
backup, and eventual object-storage policies are deployment decisions.

### 11.2.1 Local prototype hardware profile

The initial development target is a fully local machine with 16 GB system
RAM, a four-core CPU, an NVIDIA RTX 3050 GPU, and SQLite. RTX 3050 cards
exist in configurations with different VRAM capacities; the runtime must
detect the actual available VRAM and must not hardcode a presumed card
variant. The first release is a constrained development profile, not a
throughput guarantee.

Recommended initial policy defaults (all configurable and subject to
benchmarking):

| Setting | Prototype default |
|---|---|
| Concurrent model execution | 1 active model workload; sequential modules |
| Concurrent training jobs | 1 |
| Concurrent inference jobs | 1 GPU job; bounded small CPU queue |
| System RAM admission budget | At most 70% of currently available RAM; preserve OS reserve |
| GPU memory admission budget | At most 70% of currently free VRAM at job admission; preserve driver/display reserve |
| Initial inference batch size | 1; increase only after benchmark |
| Initial image policy | Adapter-defined; start with supported native size or a documented tile/resize policy |
| CPU fallback | Only if the adapter declares and tests CPU support |
| Queue behavior | Bounded queue; reject/defer work when limits are reached |

These are safe starting ceilings, not promises that every model will fit.
The execution manager must query live available RAM/VRAM, account for
estimated peak memory by adapter, workload, image dimensions, and batch
size, and refuse or defer jobs that exceed the configured admission
budget. If a GPU memory estimate is unavailable or unreliable, run a
small controlled benchmark or require an explicit conservative profile;
do not guess that the workload fits.

### 11.2.2 Hardware-aware execution manager

Add a local `ResourceManager`/execution admission component between job
submission and model execution. It is responsible for:

- Detecting CPU cores, system RAM, GPU device, free/total VRAM, CUDA,
  driver, PyTorch, and runtime versions.
- Reading adapter-declared memory estimates separately for training and
  inference, including image size and batch-size sensitivity.
- Applying configurable CPU, RAM, VRAM, queue-depth, job-count, timeout,
  and per-job resource limits.
- Prioritizing jobs (interactive inspection ahead of background
  evaluation/training by default), with starvation protection and
  cancellation handling.
- Loading only the model required for the next sequential stage; unloading
  it after the stage when it is not needed by a following operation.
- Releasing references, clearing framework caches where appropriate,
  and recording memory before/after execution. Cache cleanup is best
  effort and must not be represented as guaranteed physical VRAM release.
- Running CPU fallback only when declared by the adapter and selected
  configuration.
- Serializing GPU work by default. Parallel execution requires an explicit
  opt-in and benchmark evidence for the exact model combination, input
  dimensions, and concurrency setting.
- Recording admission decisions, observed peak memory, device, timings,
  and resource-limit failures in the execution trace.

A resource estimate is an admission aid, not a substitute for runtime
monitoring. Catch out-of-memory errors, mark the stage/job failed with a
specific reason, release resources, and do not silently retry at a
smaller size unless a documented retry policy allows it. Never claim that
all installed models can remain resident or execute simultaneously.

### 11.3 Operational resources

-   Dataset curation and annotation process
-   Domain expert to define acceptable/defective criteria
-   Camera/lighting/sensor setup and calibration
-   GPU/CPU capacity planning
-   Backup and recovery
-   Access control and audit trail
-   Model/data version retention
-   Human-review staffing and escalation
-   Deployment approval process
-   Monitoring for data drift and model degradation

A model cannot compensate for inconsistent capture conditions or unclear
defect definitions. Imaging setup and quality specifications are part of
the system.

------------------------------------------------------------------------

## 12. Suggested logical Python project structure

This is a **proposed target structure**, not a claim about the current
repository. The next step after agreeing on this document is to map the
existing files into these responsibilities and then redesign the actual
folder tree.

``` text
clockit/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   └── exceptions.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── scanners.py
│   │   │   │   ├── modules.py
│   │   │   │   ├── datasets.py
│   │   │   │   ├── training.py
│   │   │   │   ├── inspections.py
│   │   │   │   ├── reviews.py
│   │   │   │   ├── learning_iterations.py
│   │   │   │   ├── analytics.py
│   │   │   │   └── reports.py
│   │   │   └── schemas/
│   │   ├── domain/
│   │   │   ├── scanners/
│   │   │   ├── modules/
│   │   │   ├── datasets/
│   │   │   ├── inspections/
│   │   │   ├── findings/
│   │   │   ├── reviews/
│   │   │   ├── training/
│   │   │   └── deployments/
│   │   ├── services/
│   │   │   ├── scanner_service.py
│   │   │   ├── dataset_service.py
│   │   │   ├── training_service.py
│   │   │   ├── inspection_service.py
│   │   │   ├── review_service.py
│   │   │   ├── learning_service.py
│   │   │   └── evaluation_service.py
│   │   ├── orchestration/
│   │   │   ├── pipeline_executor.py
│   │   │   ├── stage_scheduler.py
│   │   │   ├── result_aggregator.py
│   │   │   └── decision_engine.py
│   │   ├── data/
│   │   │   ├── ingestion/
│   │   │   ├── validation/
│   │   │   ├── preprocessing/
│   │   │   ├── annotations/
│   │   │   ├── versioning/
│   │   │   └── splits/
│   │   ├── ml/
│   │   │   ├── contracts/
│   │   │   ├── registry/
│   │   │   ├── runtimes/
│   │   │   ├── training/
│   │   │   ├── inference/
│   │   │   ├── evaluation/
│   │   │   └── adapters/
│   │   │       ├── anomaly_detection/
│   │   │       │   ├── efficientad/
│   │   │       │   ├── patchcore/
│   │   │       │   └── padim/
│   │   │       ├── detection/
│   │   │       │   ├── yolo/
│   │   │       │   └── rtdetr/
│   │   │       ├── segmentation/
│   │   │       ├── classification/
│   │   │       ├── ocr/
│   │   │       ├── three_d/
│   │   │       └── time_series/
│   │   ├── industry_profiles/
│   │   │   ├── base.py
│   │   │   ├── steel/
│   │   │   ├── textiles/
│   │   │   └── automotive/
│   │   ├── database/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── migrations/
│   │   ├── storage/
│   │   │   ├── artifact_store.py
│   │   │   ├── dataset_store.py
│   │   │   └── inspection_store.py
│   │   ├── workers/
│   │   │   ├── training_worker.py
│   │   │   ├── inference_worker.py
│   │   │   └── evaluation_worker.py
│   │   └── tests/
│   ├── scripts/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   └── ...
├── storage/
│   ├── uploads/
│   ├── datasets/
│   ├── model_artifacts/
│   ├── inspection_results/
│   └── reports/
├── configs/
│   ├── models/
│   ├── industries/
│   └── pipelines/
├── docs/
│   ├── architecture/
│   ├── api/
│   └── user_guides/
└── README.md
```

### Python responsibility rules

-   `api/routes/`: HTTP endpoints only; no model training logic.
-   `services/`: application use cases and coordination.
-   `domain/`: core entities, validation rules, and business logic.
-   `ml/adapters/`: model-family-specific code; each adapter implements
    the common module contract.
-   `data/`: upload, extraction, validation, preprocessing, annotation,
    and dataset versioning.
-   `orchestration/`: executes configured modules and combines evidence.
-   `industry_profiles/`: industry-specific schemas, defect taxonomies,
    metadata, and default templates---not hardcoded model logic.
-   `workers/`: long-running asynchronous jobs.
-   `storage/`: controlled access to files and artifacts.
-   `database/`: persistence models and repository access.

Do not create one giant Python file per industry containing all logic.
Industry profiles should configure shared capabilities; model adapters
should remain reusable across industries.

------------------------------------------------------------------------

## 13. Core database entities

At minimum, plan for these entities:

  -----------------------------------------------------------------------
  Entity                              Important relationships / fields
  ----------------------------------- -----------------------------------
  User / Organization                 Ownership, permissions, teams

  ScannerUnit                         Name, description, industry,
                                      product scope, owner, status

  ScannerVersion                      Immutable configuration snapshot

  AnalysisModule                      Module type, model family, config,
                                      position/stage

  ModelDefinition                     Catalogue metadata and capabilities

  ModelArtifact                       Weights, checksums,
                                      framework/runtime version

  Dataset                             Logical dataset identity

  DatasetVersion                      Immutable snapshot, manifest,
                                      validation report

  DatasetSample                       File reference, modality, metadata,
                                      labels

  Annotation                          Boxes, masks, classes,
                                      measurements, provenance

  TrainingRun                         Config, dataset version, logs,
                                      status, metrics

  EvaluationRun                       Test set, metrics, comparison,
                                      acceptance decision

  Deployment                          Scanner version, environment,
                                      active status

  Inspection                          Input references, scanner version,
                                      status, timestamps

  ModuleExecution                     Per-module input/output, latency,
                                      status

  Finding                             Predicted
                                      defect/anomaly/object/measurement

  HumanReview                         Reviewer, outcome, notes, timestamp

  CorrectionRecord                    Corrected label/region and training
                                      eligibility

  LearningIteration                   Selected corrections, dataset
                                      snapshot, candidate artifact

  AuditEvent                          Who changed what, when, and why
  -----------------------------------------------------------------------

Use foreign keys and immutable version references. Store
image/mask/artifact data in file/object storage and reference it from
the database.

------------------------------------------------------------------------

## 14. Dashboard and Scanner detail requirements

### Main Scanner Workspace

Show:

-   Total Scanner Units
-   Active, draft, training, failed, and archived counts
-   Scanner cards/list with name, industry, product, module count,
    current version, last training, and status
-   Dataset name/version and sample count
-   Last inspection time and inspection volume
-   Recent findings and review backlog
-   Human-validated performance summary
-   Create Scanner Unit action

Do not show a single global accuracy figure without explaining its
evaluation source, sample size, date, and metric.

### Scanner detail page

Recommended sections:

1.  Overview
2.  Configuration and modules
3.  Datasets and versions
4.  Training runs
5.  Model versions and deployment
6.  Inspection history
7.  Findings and visual evidence
8.  Human review queue
9.  Learning iterations
10. Performance and evaluation
11. Audit/history

### Performance presentation

Display performance per module and per Scanner Version. Include sample
count, evaluation date, evaluation dataset version, metric definition,
and confidence interval where practical.

Separate: - Offline benchmark/evaluation metrics - Human-reviewed
operational metrics - Production throughput/latency metrics

Do not mix them into one score.

------------------------------------------------------------------------

## 15. Security, safety, and governance requirements

-   Authenticate users and enforce organization/project-level access.
-   Validate uploads and safely extract archives; prevent path traversal
    and archive bombs.
-   Restrict file types and enforce upload/storage quotas.
-   Scan uploads for malware where deployment requirements justify it.
-   Keep secrets out of source code and logs.
-   Encrypt network traffic and protect stored data according to
    deployment requirements.
-   Record dataset/model/configuration provenance.
-   Maintain audit logs for training, review, deployment, and
    configuration changes.
-   Use role-based permissions for model deployment and quality-rule
    changes.
-   Make model limitations and intended use visible.
-   Keep human approval in workflows where product risk or customer
    policy requires it.
-   Define retention and deletion policies for source images and derived
    artifacts.
-   Review all third-party model and dataset licences before commercial
    use.

Public benchmark datasets are useful for development and comparison, but
they are not a substitute for representative customer data. Check each
dataset's licence before using it in a commercial product.

------------------------------------------------------------------------

## 16. Recommended implementation phases

Do not implement every phase simultaneously. The local prototype must
prove one complete Scanner Unit lifecycle before expanding breadth.

### Phase 1 --- Functional Scanner Unit

- Scanner Unit CRUD and one-module configuration
- Module catalogue and capability registry/manifests
- ZIP upload, safe extraction, validation, preprocessing, and dataset
  versioning
- Hardware-aware local execution manager with sequential scheduling
- EfficientAD adapter with normal-only training, inference, anomaly score,
  and heatmap
- OpenCV deterministic processing primitives needed by the first use case
- Inspection history and exact Scanner Version/model artifact references
- SQLite persistence and local filesystem artifact storage

**Acceptance criterion:** Create a Scanner Unit, upload normal images,
validate and version the dataset, train EfficientAD within local resource
limits, inspect a new image, and reproduce the result using the same
Scanner Version and artifacts.

### Phase 2 --- Human Review and Learning

- False-positive/false-negative and other correction labels
- Corrected class/box/mask capture where applicable
- Traceable correction records and approval/eligibility state
- Correction batching and configurable minimum sample thresholds
- Immutable learning dataset snapshots
- Adapter-supported training strategy selection only
- Candidate training/evaluation against fixed validation and challenge sets
- Per-class/category regression checks and current-vs-candidate comparison
- Human approval/rejection and rollback

**Acceptance criterion:** A reviewer can correct an inspection, select
approved corrections into a learning iteration, evaluate a candidate,
and approve/reject it without altering the active artifact.

### Phase 3 --- Multi-Module Orchestration

- Multiple analysis modules per Scanner Unit
- Sequential execution by default; benchmark-gated parallel execution
- Standardized module output contracts and execution tracing
- Typed evidence aggregation and versioned decision rules
- PASS / FAIL / NEEDS_REVIEW decision handling
- Failure, timeout, missing-evidence, and retry policies

**Acceptance criterion:** One inspection executes multiple compatible
modules sequentially and produces one traceable consolidated decision.

### Phase 4 --- Supervised Models

- YOLO inference adapter and annotation import
- Defect taxonomy and annotation validation
- Supervised YOLO training where labelled examples are available
- Detection evaluation and regression checks
- YOLO segmentation when polygon/mask data and tests are ready

### Phase 5 --- Industry Profiles

- Steel, textiles, and automotive templates
- Reusable defect taxonomies and metadata schemas
- Scanner Unit templates and input modality recommendations
- Product-specific severity and acceptance-rule configuration

Industry profiles configure reusable modules and decision rules; they do
not hardcode industry behavior into core model architecture.

### Phase 6 --- Production and Advanced Modalities

- Bounded background workers and operational job management
- Production database migration and object storage only when justified
- Advanced GPU scheduling after workload benchmarks
- Multi-view and line-scan inspection
- Thermal, depth, 3D, and specialized modalities
- Monitoring, drift detection, backups, and production deployment controls

PostgreSQL, Redis, Docker, cloud services, and microservices are not
mandatory dependencies for the local prototype. Introduce them only as a
separate production decision supported by concrete operational needs.

------------------------------------------------------------------------

## 17. Decisions that must be made before the file-structure redesign

These are the main unresolved design decisions:

1.  **Initial input scope:** still images only for the first release, or
    line-scan images as well?
2.  **Initial training model:** should EfficientAD be the first fully
    supported normal-only model?
3.  **Model catalogue:** which models are trainable in CLOCKIT, and
    which are inference-only?
4.  **Training execution:** local bounded in-process job runner for the
    prototype; determine whether a separate worker is needed for production.
5.  **Storage:** local filesystem for the prototype; determine production
    object-storage requirements only when deployment scale is known.
6.  **Annotation:** build a basic internal annotation tool or initially
    import YOLO/COCO-style labels?
7.  **Human review:** can any trained user review corrections, or is
    approval role-restricted?
8.  **Deployment:** local workstation, factory edge machine, central
    server, or more than one?
9.  **Decision rules:** who defines pass/fail thresholds and
    product-specific tolerances?
10. **Industry order:** which first customer workflow should be
    implemented first---steel surface, textile fabric, or a specific
    automotive component?

The following are fixed for the prototype by this revision: local-only
execution, SQLite, local file storage, a four-core/16 GB RAM development
profile with runtime-detected RTX 3050 VRAM, sequential model execution,
and no mandatory PostgreSQL/Redis/Docker/microservices. Remaining
unresolved decisions are the first customer product/use case, exact image
capture scope, annotation editor versus import-first UX, approval roles,
production deployment topology, and product-specific acceptance-rule
ownership. The recommended default remains one end-to-end normal-only
image Scanner Unit first, then human corrections and supervised modules.

------------------------------------------------------------------------

## 18. Public datasets and reference resources

These resources can help with prototyping, benchmarking, and
understanding annotation formats. Verify the current terms before
downloading, redistributing, or using any dataset commercially.

### General industrial anomaly detection

-   [MVTec
    AD](https://www.mvtec.com/research-teaching/datasets/mvtec-ad) ---
    industrial objects and textures, normal training images, anomalous
    test images, and pixel-precise anomaly annotations. The published
    licence is non-commercial CC BY-NC-SA 4.0; do not assume it is
    cleared for commercial training.
-   [MVTec AD
    2](https://www.mvtec.com/research-teaching/datasets/mvtec-ad-2) ---
    more challenging industrial anomaly scenarios and evaluation
    tooling; check its licence terms.
-   [MVTec 3D-AD](https://www.mvtec.com/research-teaching/datasets) ---
    3D scans for anomaly detection/localization.
-   [VisA](https://github.com/amazon-science/spot-diff) --- visual
    anomaly dataset and research resources; verify dataset terms.
-   [Real-IAD](https://realiad4ad.github.io/Real-IAD/) --- large-scale
    multi-view industrial anomaly benchmark; verify current access and
    licence terms.

### Steel

-   [Severstal Steel Defect
    Detection](https://www.kaggle.com/c/severstal-steel-defect-detection)
    --- steel surface images with four defect classes and segmentation
    annotations.
-   [NEU Surface Defect
    Database](https://faculty.neu.edu.cn/songkc/en/zdylm/263265) ---
    hot-rolled steel surface defect benchmark.
-   [GC10-DET](https://github.com/lvxiaoming2019/GC10-DET-Metallic-Surface-Defect-Datasets)
    --- steel surface detection benchmark with multiple defect classes;
    verify repository terms.

### Textiles

-   [AITEX fabric defect dataset](https://www.aitex.es/afid/) --- fabric
    defect imagery and annotations; verify access and terms.
-   [ZJU-Leaper](https://github.com/cqwangzh/ZJU-Leaper-Dataset) ---
    fabric defect research dataset; verify the current official
    repository and terms.
-   [DAGM
    2007](https://hci.iwr.uni-heidelberg.de/content/weakly-supervised-learning-industrial-optical-inspection)
    --- synthetic/textured industrial inspection benchmark; verify
    access and terms.

### Automotive / components

-   [MVTec
    AD](https://www.mvtec.com/research-teaching/datasets/mvtec-ad) ---
    useful for component-like object and texture anomaly experiments,
    though it is not a complete automotive production dataset.
-   [MVTec 3D-AD](https://www.mvtec.com/research-teaching/datasets) ---
    useful for 3D industrial surface anomaly research.
-   [MVTec LOCO AD](https://www.mvtec.com/research-teaching/datasets)
    --- logical and structural anomaly benchmark, relevant to certain
    assembly/completeness concepts.
-   Customer-specific images and labels will ultimately be essential for
    actual automotive part/line performance.

### Model and framework references

-   [EfficientAD paper](https://arxiv.org/abs/2303.14535) --- efficient
    visual anomaly detection.
-   [PatchCore paper](https://arxiv.org/abs/2106.08265) --- use the
    official paper/repository reference selected during implementation;
    confirm exact implementation and licence before adoption.
-   [Ultralytics task
    documentation](https://docs.ultralytics.com/tasks/) --- detection,
    segmentation, classification, and other task workflows; review
    licensing for the intended commercial deployment.
-   [PyTorch](https://pytorch.org/) --- model development and training
    framework.
-   [OpenCV](https://opencv.org/) --- image acquisition and classical
    computer-vision processing.
-   [MLflow](https://mlflow.org/docs/latest/) --- experiment tracking
    and model lifecycle tooling.

------------------------------------------------------------------------

## 19. Key technical rules to preserve

1.  A Scanner Unit can have one module or many.
2.  Modules declare capabilities and data requirements; the UI must not
    invent unsupported outputs.
3.  Normal-only anomaly detection and supervised defect detection are
    different training paradigms.
4.  A normal-only ZIP can train compatible anomaly detectors, but it
    cannot by itself train a conventional supervised defect detector.
5.  Human corrections are versioned data, not automatic ground truth
    until reviewed/approved.
6.  False-positive corrections can contribute normal examples;
    false-negative corrections need defect labels/regions where
    possible.
7.  Training iterations create candidate versions; they do not overwrite
    the deployed model.
8.  Candidate models must be evaluated against stable holdout/challenge
    data before deployment.
9.  Keep model scores, confidence, severity, and final quality decision
    as distinct concepts.
10. Never average unrelated model scores without a defined calibration
    and aggregation method.
11. Every inspection must record the exact Scanner Version and model
    artifacts used.
12. Industry profiles configure reusable capabilities; they must not
    create three separate copies of the whole platform.
13. Store original data and derived artifacts with traceability and
    access controls.
14. Public datasets are benchmarks, not proof of customer-site
    performance.
15. Make one end-to-end Scanner Unit reliable before expanding the model
    catalogue or supported modalities.
16. Execute model modules sequentially by default; parallelism requires
    measured resource headroom and explicit enablement.
17. SQLite and local file storage remain the prototype persistence layer;
    external infrastructure is deferred.
18. Model integration requires a tested adapter and real inference, not
    merely downloaded weights or packages.
19. Preprocessing is model-specific, configurable, immutable by version,
    and traceable to original samples.
20. Human corrections never trigger automatic retraining; learning
    iterations are approved, batched, evaluated, and reversible.

------------------------------------------------------------------------

## 20. Final definition

CLOCKIT is a configurable industrial AI inspection platform in which
manufacturers create Scanner Units by combining compatible analysis
modules, supplying appropriate training data, configuring inspection
outputs, and defining quality rules. Each Scanner Unit has versioned
datasets, model artifacts, training runs, inspection records, findings,
and human corrections. Validated corrections can be used in controlled
learning iterations that produce candidate models, compare performance,
and support safe deployment and rollback.

The platform initially focuses on steel, textile, and automotive
inspection, while keeping its architecture extensible to additional
industries, sensors, and inspection modalities.

**The immediate engineering goal is not to build every possible model.
It is to build a sound Scanner Unit lifecycle and a model-adapter
architecture that allows new analysis capabilities to be added without
rewriting the platform.**


------------------------------------------------------------------------

## 21. Technical Audit Alignment Addendum (Version 1.1)

This addendum records the implementation constraints and acceptance
requirements introduced by the technical audit. It supplements the
existing product specification; it does not replace the Scanner Unit
concept, product vocabulary, or phased architecture.

### 21.1 Implementation status vocabulary

Documentation alone is not evidence that a feature exists. Until the
repository, running application, persisted data, and tests have been
inspected, all capabilities described in this specification must be
tracked as **Planned / Not yet validated** rather than marked complete.
Use these statuses in the engineering tracker and release notes:

- **Already implemented:** demonstrated in the current code and verified
  by a passing automated test or repeatable acceptance test.
- **Partially implemented:** some code path exists, but required behavior,
  error handling, persistence, or tests are incomplete.
- **Planned:** specified but not yet implemented.
- **Not yet validated:** implementation may exist, but has not passed the
  required integration/acceptance validation.

No implementation inventory or repository evidence was supplied with
this specification update. Therefore this document does not assert that
any of the audit requirements are already implemented. Each item must be
classified after a repository audit; absent that evidence, use Planned
or Not yet validated.

### 21.2 Updated architecture and component responsibilities

Keep the application as a modular local monolith for the prototype:

| Component | Responsibility |
|---|---|
| API/routes | Request validation, authentication/authorization hooks, response schemas; no model training logic |
| Application services | Scanner, dataset, training, inspection, review, learning-iteration use cases and transaction coordination |
| Domain layer | Scanner/version lifecycle, capability compatibility, review rules, decision semantics, invariants |
| Dataset ingestion | ZIP intake, quarantine, safe extraction, file manifests, validation report |
| Preprocessing | Configurable, versioned transforms and model-specific input preparation |
| Model registry | Capability manifests, adapter discovery, compatibility checks and integration status |
| Model adapters | Real model-specific training/inference/evaluation, input/output validation, artifact creation and error mapping |
| Resource manager | Hardware detection, admission control, bounded scheduling, sequential execution, cleanup and resource telemetry |
| Orchestrator | Module order, dependencies, stage state, timeout/failure policy and trace IDs |
| Evidence/decision engine | Typed output normalization, versioned rule evaluation, final inspection disposition |
| Review/learning service | Human corrections, approval, batching, immutable learning snapshots, candidate workflow |
| Persistence | SQLite metadata, foreign keys, immutable version references and audit events |
| Local artifact storage | Original uploads, extracted sources, processed datasets, checkpoints, predictions, heatmaps and reports |

These are logical boundaries within one application, not separate
services or deployment units. Preserve existing working code where it
already satisfies a contract; refactor only where necessary to establish
these responsibilities and testable interfaces.

### 21.3 Required model capability manifest

Each model adapter must expose a machine-readable, schema-validated
manifest containing at least:

- Stable model/adapter ID, display name, family, adapter version, model
  version, framework/runtime versions, licence and provenance.
- Supported tasks and modalities; accepted formats, channel order, colour
  space, dimensions/ranges, aspect ratios, tiling support and coordinate
  conventions.
- Dataset layout, required/optional folders, annotation formats,
  required labels, class mapping and split constraints.
- Training paradigm and independent flags for initial training,
  fine-tuning, incremental adaptation, full retraining and evaluation-only.
- Supported outputs and typed schemas, including score semantics,
  calibration state, localization representation and postprocessing.
- Preprocessing pipeline IDs, required parameters, defaults, bounds and
  compatibility constraints.
- CPU/GPU device support, minimum runtime requirements, estimated peak
  RAM/VRAM for training and inference at stated resolution/batch sizes,
  supported batch-size range and known memory variability.
- Dependencies, artifact paths/formats/checksums, compatibility rules,
  evaluation metrics, known limitations and supported export formats.
- Adapter integration state: `available`, `adapter_present`,
  `inference_validated`, `training_validated`, `fully_integrated`.

A manifest is not a claim of capability by itself: every declared
capability must be covered by tests. The UI must derive available actions
and outputs from the validated manifest and runtime integration state.

### 21.4 Hardware execution policy

The execution manager is the only component allowed to admit model jobs
to CPU/GPU resources. Its default is one active model workload and
sequential module execution. It must detect current free resources rather
than relying only on machine labels, enforce configurable limits, and
record requested/estimated/observed resource use. Interactive inspection
jobs receive higher priority than training/evaluation jobs, subject to
bounded queues and starvation protection. Training must not monopolize
the device while interactive inspection is pending unless an operator
explicitly changes policy.

Models are loaded on demand and unloaded after use when practical. GPU
cache cleanup is best effort; the scheduler must use actual free VRAM for
admission. Parallel execution remains disabled until repeatable
benchmarks prove safe concurrency for the exact workload profile.

### 21.5 Preprocessing and dataset integrity policy

Original archives and source images remain immutable. Derived samples
must be traceable to their source hashes and preprocessing configuration.
Dataset splits should be group-aware when samples share a physical part,
roll, lot, capture session, or near-duplicate source. Near-duplicate
checks are recorded as warnings/review candidates rather than silently
deleting data. Model-specific normalization and image sizing belong to
versioned preprocessing configurations. The validation report is a
required gate before a training run is created.

### 21.6 Learning iteration state machine

A Learning Iteration must progress through explicit states such as
`draft`, `corrections_selected`, `dataset_built`, `training_queued`,
`training`, `candidate_ready`, `evaluating`, `awaiting_approval`,
`approved`, `rejected`, `failed`, or `cancelled`. State transitions are
validated and audited. Correction records remain immutable; eligibility
and inclusion in a particular dataset snapshot are separate fields.

Minimum sample thresholds are configurable per adapter/strategy. A
reviewed correction may be stored immediately, but it does not trigger
training automatically. Candidate evaluation uses fixed holdout and
challenge datasets, per-class/per-defect metrics, false-positive and
false-negative operating metrics, latency/resource checks, and regression
gates. A candidate is activated only after human approval; rejection or
failure leaves the active deployment untouched.

### 21.7 Immutable version and reproducibility requirements

Every Scanner Version must pin:

- DatasetVersion and sample manifest checksum.
- Preprocessing configuration/version.
- Module definitions, ordering, parameters and adapter versions.
- Model artifact IDs, immutable paths and checksums.
- Training configuration, TrainingRun ID and seed where applicable.
- EvaluationRun, test dataset references, metrics and approval record.
- Decision-engine rule-set version and product acceptance criteria.
- Runtime/device metadata needed to interpret reproducibility limits.

Inspection records store the exact Scanner Version, model artifacts,
preprocessing configuration, input hashes, module execution trace,
decision-rule version and output references. Never overwrite deployed
artifacts or mutate a Scanner Version. Rollback changes the active
Deployment pointer to a prior approved version; it does not rewrite
history.

### 21.8 Minimum integration and acceptance test matrix

| Area | Required validation |
|---|---|
| ZIP ingestion | Traversal/archive-bomb rejection, limits, safe extraction and manifest integrity |
| Dataset preprocessing | EXIF, corrupt images, color modes, dimensions, hashes, near-duplicates, split/leakage checks and reproducible transforms |
| Adapter contracts | Manifest schema, input validation, output schema, unsupported capability rejection and error mapping |
| EfficientAD | Real normal-only training, artifact persistence, inference, score/heatmap output and repeatability |
| YOLO | Real inference; supervised training only with valid labelled data; detection output normalization |
| OpenCV | Deterministic processing/measurement tests with known inputs and expected tolerances |
| Output handling | Heatmap dimensions/alignment, boxes/masks, coordinate conversion and serialization |
| Orchestration | Sequential multi-module execution, ordering, timeout/failure behavior and trace IDs |
| Resource manager | RAM/VRAM admission, queue bounds, one-job policy, CPU fallback only when supported, cleanup and out-of-memory handling |
| Human review | False-positive, false-negative, incorrect class/localization, uncertain and approval workflows |
| Learning iteration | Correction selection, immutable snapshot, threshold enforcement, candidate training and cancellation/failure paths |
| Evaluation | Fixed validation/challenge sets, per-class metrics and regression gates |
| Release lifecycle | Candidate approval/rejection, active version preservation and rollback |
| Reproducibility | Re-run an inspection with pinned Scanner Version and verify matching configuration/artifact references |

A feature is not complete until its relevant automated tests pass and
its end-to-end acceptance path is demonstrated. Do not use mock outputs
or simulated training as evidence of model integration.

### 21.9 Updated phased implementation priority

The authoritative phase order and acceptance criteria are in Section 16.
The non-negotiable order is: (1) functional local Scanner Unit with
EfficientAD and dataset/resource controls; (2) reviewed corrections and
safe learning iterations; (3) sequential multi-module orchestration and
typed decision rules; (4) supervised YOLO and segmentation; (5) industry
profiles; (6) production infrastructure and advanced modalities.
Do not begin later-phase infrastructure merely to make the architecture
look production-scale.

### 21.10 Unresolved technical decisions

The audit fixes the prototype constraints but leaves these decisions open
for evidence-based resolution:

1. Exact first customer workflow and product/defect acceptance criteria.
2. Still-image-only scope versus adding line-scan ingestion in the first
   customer pilot.
3. Which EfficientAD implementation/repository and licence will be used.
4. Exact RTX 3050 VRAM capacity and measured memory profile on the target
   machine.
5. Annotation workflow: internal editor, import-first COCO/YOLO support,
   or staged combination.
6. Reviewer/approver roles and audit permissions.
7. Minimum correction batch sizes and acceptance thresholds per adapter.
8. Required reproducibility level across GPU/runtime versions.
9. Production deployment topology and when SQLite/local storage should be
   migrated.
10. Product-specific severity scales, calibrated confidence requirements,
    and who owns approval of decision rules.

These decisions must be recorded with an owner, rationale, evidence, and
review date. They must not block the initial local end-to-end workflow
unless they affect its correctness or safety.

------------------------------------------------------------------------

## 22. Final implementation directive

Build a genuinely functional local industrial inspection workflow, not a
catalogue of disconnected model names or simulated AI results. Preserve
the Scanner Unit as the central product concept, keep AI models as
interchangeable but capability-constrained building blocks, and prioritize
correct data handling, real adapter behavior, bounded hardware execution,
traceable human review, immutable versioning, and reproducible inspection
results.
