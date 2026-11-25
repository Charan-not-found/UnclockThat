# Agent Module: Decision Aggregation & Human Review

## Overview
Aggregate multi-scan module outputs into a traceable product-level quality assessment, manage false-positive thresholds, and route uncertain cases to human reviewers.

## Core Responsibilities
- **Decision & Aggregation Module**:
  - Verify all required scan results and module/model versions are present.
  - Normalize compatible risk signals and apply configurable weights/business rules.
  - Apply critical-defect overrides and handle missing/failed scans.
  - Produce a traceable product-level quality score and final decision (`PASS`, `FAIL`, `REVIEW_REQUIRED`).
- **False-Positive Management**:
  - Support per-product/per-station thresholds and region-specific rules.
  - Group duplicate alerts and maintain suppression rules with audit history.
- **Human-in-the-Loop Review**:
  - Route low-confidence, high-severity, or out-of-distribution cases to a review queue.
  - Capture reviewer feedback/overrides to inform threshold tuning.

## Definition of Done
- Aggregation engine producing product-level quality reports with full traceability.
- Review queue API/logic supporting operator decisions and override logging.
- Unit tests for critical-defect overrides and missing-scan handling.
