# Agent Module: Platform API & Multi-Tenancy

## Overview
Build the core FastAPI backend that serves as the central control plane for **PROMETHEUS-X**, handling authentication, tenant isolation, resource management, and audit logging.

## Core Responsibilities
- **Authentication & Authorization**: JWT/session-based auth, role-based access control (Plant Admin, Quality Manager, Manufacturing Engineer, ML Engineer, Factory Operator, Auditor, Platform Admin).
- **Tenant & Hierarchy Management**: Organizations -> Factories -> Production Lines -> Inspection Stations -> Products & Projects.
- **Resource Endpoints**:
  - `POST /api/v1/projects`, `GET /api/v1/projects`
  - `POST /api/v1/datasets`, `POST /api/v1/datasets/{id}/validate`
  - `POST /api/v1/models/train`, `GET /api/v1/models/{id}`
  - `POST /api/v1/workflows`, `POST /api/v1/inspections/run`
  - `GET /api/v1/inspections/{id}/results`
  - `POST /api/v1/reviews/{id}/decision`
- **Audit Logging**: Record all configuration changes, threshold updates, model promotions, and human review overrides.

## Tech Stack
- Python, FastAPI, Pydantic, SQLAlchemy / Alembic, PostgreSQL.

## Definition of Done
- OpenAPI/Swagger docs available at `/docs`.
- Tenant-isolated CRUD endpoints for organizations, projects, datasets, workflows, and inspections.
- Unit and integration tests for auth, RBAC, and core endpoints.
