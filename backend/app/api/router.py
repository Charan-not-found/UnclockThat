"""FastAPI main router — registers all v1 sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1 import health, inspections, models, pipelines, analytics, admin

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(inspections.router)
api_router.include_router(models.router)
api_router.include_router(pipelines.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
