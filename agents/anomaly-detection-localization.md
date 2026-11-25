# Agent Module: AI Anomaly Detection & Localization

## Overview
Implement normal-only industrial anomaly detection training, inference, and spatial localization (heatmaps, masks, bounding boxes).

## Core Responsibilities
- **Normal-Only Training**:
  - Support PatchCore (MVP baseline), with extensibility for PaDiM / EfficientAD.
  - Train strictly on defect-free examples; enforce train/val/test separation.
  - Save versioned model artifacts to Object Storage and register in Model Registry.
- **Inference & Anomaly Detection Module**:
  - Output image-level anomaly score, pixel-level anomaly map, model/version IDs, and processing time.
- **Localization Module**:
  - Generate pixel-level anomaly heatmap preserving the original image.
  - Produce binary anomaly mask via configurable thresholding.
  - Extract bounding boxes, region area, and location for connected suspicious regions.
- **Evaluation**: Compute image-level (AUROC, F1) and pixel-level (pixel AUROC, PRO) metrics on held-out test sets.

## Definition of Done
- Training pipeline for PatchCore on normal-only image datasets.
- Inference & localization service returning standardized JSON + heatmap/mask artifacts.
- Evaluation script reporting image-level and pixel-level metrics.
