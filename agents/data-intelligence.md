
# Agent Module: Data Ingestion & Data Intelligence

## Overview
Handle manufacturer-provided dataset uploads, integrity validation, metadata extraction, and readiness reporting before model training or inference.

## Core Responsibilities
- **Ingestion & Storage**: Accept image/metadata uploads, store raw assets in Object Storage (S3/MinIO), and record metadata in PostgreSQL.
- **Data Intelligence Module**:
  - Identify file formats and modalities; detect corrupt or unreadable files.
  - Extract image dimensions, channels, timestamps, and camera/station metadata.
  - Detect duplicate or near-duplicate images (e.g., perceptual hashing).
  - Flag extremely dark, bright, blurry, or low-resolution images.
  - Detect potential train/validation/test split leakage.
- **Readiness Report**: Output structured JSON (`file_count`, `valid_count`, `invalid_count`, `duplicate_count`, `warnings`, `readiness` status).
- **Dataset Versioning**: Track immutable dataset versions for reproducible training.

## Standard Output Contract
Must conform to the platform's standardized module output format with `module: "data_intelligence"`, `status`, `warnings`, and `readiness`.

## Definition of Done
- Upload pipeline storing files in object storage and metadata in DB.
- Automated validation script/service producing the dataset readiness JSON report.
- Tests covering corrupt files, duplicates, and brightness/blur warnings.
