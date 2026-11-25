# CLOCKIT — Data & Output Types Specification

## 1. Dataset Storage

Location: `data/datasets/`

Store original uploaded datasets without modifying them.

Supported input formats:
- `.zip`
- `.tar`
- `.tar.gz`

Supported image formats:
- `.jpg`
- `.jpeg`
- `.png`
- `.bmp`
- `.tiff`
- `.tif`
- `.webp`

Dataset categories:
- Normal / defect-free images
- Defective images
- Mixed datasets
- Unlabelled datasets
- Reference images
- Validation datasets
- Test datasets

## 2. Extracted Training Data

Location: `data/training/`

Store extracted images and their associated annotations.

Supported data types:

### Image data
- RGB images
- Grayscale images
- High-resolution industrial images
- Multi-channel images (where supported)

### Annotation data
- Image-level classification labels
- Bounding-box annotations
- Pixel-level segmentation masks
- Polygon annotations
- Defect class labels
- Normal / abnormal labels
- Severity labels
- Image metadata

### Dataset metadata
- Dataset name
- Dataset ID
- Industry
- Product category
- Image dimensions
- Image count
- Class distribution
- Training / validation / test split
- Upload timestamp
- Dataset version

## 3. False Positive Training Data

Location: `data/false_positives/`

Store images incorrectly identified as defective.

Supported feedback types:
- False positive: normal image incorrectly flagged as defective
- Incorrect localization: defect prediction in the wrong location
- Incorrect segmentation: incorrect defect mask
- Incorrect classification: wrong defect category
- Incorrect severity: incorrect severity estimation
- Incorrect confidence: misleading confidence score

Each feedback record should contain:
- Original image
- Inspection ID
- Scanner unit ID
- Module ID
- Model version
- Predicted result
- Operator-corrected result
- Feedback category
- Timestamp
- Review status

Important: False-positive images must be reviewed and labelled before being incorporated into training. They should not automatically be treated as normal training samples without verification.

## 4. AI Model Outputs

Location: `outputs/`

CLOCKIT must support the following output types.

### 4.1 Anomaly Detection

Purpose: Identify whether an inspected object is normal or anomalous.

Outputs:
- Normal / anomalous classification
- Anomaly score
- Anomaly threshold
- Detection confidence
- Inspection status

### 4.2 Defect Localization

Purpose: Identify where defects are located.

Outputs:
- Bounding boxes
- Defect coordinates
- Region of interest (ROI)
- Defect location coordinates
- Localization confidence
- Annotated images

### 4.3 Defect Segmentation

Purpose: Identify the exact pixels belonging to a defect.

Outputs:
- Binary segmentation masks
- Multi-class segmentation masks
- Pixel-level defect maps
- Defect area
- Defect perimeter
- Segmentation confidence
- Mask overlays

### 4.4 Defect Classification

Purpose: Identify the type of defect.

Outputs:
- Defect category
- Predicted class
- Class probabilities
- Top-k predictions
- Classification confidence
- Multi-label classifications

Example defect categories:
- Crack
- Scratch
- Dent
- Corrosion
- Discoloration
- Surface irregularity
- Missing component
- Contamination
- Deformation
- Other / unknown

Categories must be configurable for different industries.

### 4.5 Severity Estimation

Purpose: Determine how serious a detected defect is.

Outputs:
- Severity score
- Severity category
- Defect size
- Defect area percentage
- Defect count
- Defect density
- Risk classification

Default severity levels:
- Critical
- High
- Medium
- Low
- Informational

Severity thresholds must be configurable according to product and industry requirements.

### 4.6 Confidence Estimation and Calibration

Purpose: Measure the reliability of AI predictions.

Outputs:
- Prediction confidence
- Anomaly confidence
- Classification confidence
- Localization confidence
- Calibration score
- Uncertainty estimate
- Prediction reliability
- Out-of-distribution warning

Confidence values must not automatically be interpreted as calibrated probabilities.

### 4.7 Similarity and Reference Comparison

Purpose: Compare inspected objects against learned normal references.

Outputs:
- Similarity score
- Reference image ID
- Feature similarity
- Embedding distance
- Nearest reference images
- Difference maps

### 4.8 Object and Component Detection

Purpose: Identify and inspect specific components in a product.

Outputs:
- Detected objects
- Object classes
- Object coordinates
- Object counts
- Missing component detection
- Incorrect component placement
- Component confidence

### 4.9 Image Quality Assessment

Purpose: Determine whether an image is suitable for inspection.

Outputs:
- Blur score
- Brightness score
- Contrast score
- Image resolution
- Noise estimation
- Lighting assessment
- Image usability status
- Rejection reason

### 4.10 Reconstruction and Difference Analysis

Purpose: Compare an input image with its reconstructed or reference representation.

Outputs:
- Reconstructed image
- Reconstruction error map
- Difference image
- Pixel-level error
- Reconstruction anomaly score

## 5. Combined Inspection Outputs

Location: `outputs/reports/`

Multiple modules must be able to contribute to one consolidated inspection result.

Supported combined outputs:

- Overall inspection score
- Overall pass / fail decision
- Total defect count
- Defect categories
- Maximum severity
- Average severity
- Defect locations
- Defect area percentage
- Module-level scores
- Module-level decisions
- Confidence summary
- Warnings
- Recommendations
- Inspection metadata

The combined result must preserve the original outputs from every individual module.

The final decision should use configurable industry-specific rules rather than blindly averaging all model scores.

## 6. Visualization Outputs

Location: `outputs/visualizations/`

Supported visual outputs:

- Original image
- Anomaly heatmap
- Bounding-box overlay
- Segmentation overlay
- Defect mask
- Reconstruction image
- Difference map
- Classification annotations
- Severity visualization
- Confidence visualization
- Side-by-side comparison
- Combined inspection visualization

Preferred formats:
- PNG
- JPEG
- TIFF

## 7. Structured Output Formats

All modules must support standardized machine-readable outputs.

### JSON
Primary format for:
- Predictions
- Anomaly scores
- Classification results
- Localization coordinates
- Severity estimates
- Confidence values
- Inspection reports
- Module metadata

### CSV
For:
- Inspection summaries
- Defect statistics
- Batch inspection results
- Performance metrics
- Dataset statistics

### PNG / TIFF
For:
- Segmentation masks
- Heatmaps
- Annotated images
- Difference maps

### NPY / NPZ
For:
- Numerical arrays
- Feature embeddings
- Anomaly maps
- Intermediate model outputs

### ONNX / PT
For model artifacts and deployment, where applicable.

### PDF
For human-readable inspection reports.

## 8. Training and Evaluation Outputs

CLOCKIT must retain training and model evaluation information.

Supported outputs:
- Training loss
- Validation loss
- Epoch history
- Training duration
- Model checkpoints
- Best model weights
- Confusion matrix
- Precision
- Recall
- F1 score
- AUROC
- AUPRC
- Image-level detection metrics
- Pixel-level segmentation metrics
- Localization metrics
- False-positive rate
- False-negative rate
- Calibration metrics
- Inference time
- GPU / CPU utilization

Metrics should be selected according to the capabilities and task of each model.

## 9. Model and Version Metadata

Every trained model must have associated metadata.

Required fields:
- Model ID
- Model name
- Model architecture
- Model type
- Model version
- Dataset ID
- Training configuration
- Training timestamp
- Input dimensions
- Supported output types
- Performance metrics
- Model checkpoint path
- Model status

## 10. Standardized Inspection Metadata

Every inspection should carry:

- Inspection ID
- Scanner unit ID
- Module ID
- Product ID (where available)
- Batch ID (where available)
- Image ID
- Model ID
- Model version
- Inspection timestamp
- Processing duration
- Inspection status

## 11. Output Compatibility Requirements

All modules must follow a common output interface.

Each module should declare:

1. Input data types.
2. Supported image formats.
3. Processing requirements.
4. Output data types.
5. Output file formats.
6. Confidence availability.
7. Visualization availability.
8. Supported evaluation metrics.

Modules must not be required to produce every output type.

For example:
- An anomaly detection module may produce an anomaly score and heatmap.
- A YOLO module may produce bounding boxes and defect classifications.
- A segmentation module may produce masks and defect area measurements.

CLOCKIT should combine whatever outputs are available.

## 12. Core Architecture Principle

CLOCKIT is a modular industrial inspection platform, not a single-purpose defect detection model.

Its storage and output architecture must support:

- Multiple industries
- Multiple product categories
- Multiple scanner units
- Multiple AI models
- Multiple inspection modules
- Custom training datasets
- Operator feedback and model refinement
- Individual module outputs
- Consolidated inspection reports
- Different inspection pipelines

**The most important requirement:** Every AI module must produce standardized, identifiable outputs while retaining its own model-specific information.

This allows CLOCKIT to add new AI architectures and inspection capabilities without redesigning the entire application.
