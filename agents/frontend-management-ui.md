# Agent Module: Management Web Application (Frontend)

## Overview
Build the central React + TypeScript web interface for factory, quality, and ML teams to configure projects, upload data, build workflows, inspect results, and review flagged items.

## Core Responsibilities
- **Workspace & Project Setup**: Organization/factory/line/station/product navigation.
- **Dataset Management**: Drag-and-drop dataset upload, readiness report visualization, and warning inspection.
- **Model & Module Library**: Browse available modules, trigger normal-only training, and view evaluation metrics.
- **Visual Workflow Builder**: Node-based pipeline editor (React Flow) to connect modules and configure thresholds.
- **Inspection Results & Heatmap Viewer**: Interactive viewer showing original image, toggleable anomaly heatmap overlay, bounding boxes, severity, confidence, and quality score.
- **Human Review Queue**: Interface for factory operators to inspect flagged items and submit pass/fail overrides.

## Tech Stack
- React, TypeScript, Tailwind CSS, React Flow.

## Definition of Done
- Responsive web app connected to Platform API.
- Working visual workflow builder, heatmap overlay viewer, and human review queue.
