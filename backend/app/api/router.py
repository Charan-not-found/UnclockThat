"""Versioned API router registration."""

from fastapi import APIRouter

from backend.app.api.v1 import health, inspections, models

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(inspections.router)
api_router.include_router(models.router)
