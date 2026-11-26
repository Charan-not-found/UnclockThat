"""FastAPI main router — registers all v1 sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1 import (
    admin,
    analytics,
    datasets,
    engine_api,
    health,
    inspections,
    models,
    pipelines,
    scanner_units,
    settings,
    training,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(scanner_units.router)
api_router.include_router(datasets.router)
api_router.include_router(training.router)
api_router.include_router(inspections.router)
api_router.include_router(models.router)
api_router.include_router(pipelines.router)
api_router.include_router(analytics.router)
api_router.include_router(settings.router)
api_router.include_router(admin.router)
api_router.include_router(engine_api.router)
