# Agent Module: Severity, Confidence & Distribution Shift

## Overview
Provide operational risk estimation, model reliability calibration, and input distribution-shift monitoring so AI outputs are never presented as raw, uncalibrated probabilities.

## Core Responsibilities
- **Severity Estimation Module**:
  - Combine anomaly magnitude, area, region count, location, and product-specific critical zones.
  - Map to categories: `Informational`, `Low`, `Medium`, `High`, `Critical` using transparent, configurable rules.
- **Confidence & Uncertainty Module**:
  - Calibrate scores on held-out validation sets (e.g., temperature scaling, Expected Calibration Error).
  - Keep anomaly score, confidence, severity, and quality score strictly distinct.
- **Distribution-Shift Detection Module**:
  - Monitor image brightness/contrast, color histograms, sharpness, and feature-embedding distances.
  - Apply statistical checks (PSI, KS test) and output status: `no_shift`, `warning`, `significant_shift`, `severe_shift`.

## Definition of Done
- Rule-based severity estimator with configurable critical-zone weights.
- Confidence calibration utility and ECE reporting.
- Distribution-shift detector comparing incoming batches against baseline validation statistics.
