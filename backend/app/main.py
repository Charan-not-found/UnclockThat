"""CLOCKIT FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import api_router
from backend.app.core.config import BASE_DIR, get_settings
from backend.app.core.logging import setup_logging
from backend.app.database.connection import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize logging, runtime directories, and SQLite tables on startup."""
    settings = get_settings()
    setup_logging(settings.log_level)
    init_db()
    # Ensure storage dirs exist
    for sub in ("uploads", "inspection_results", "temporary"):
        (settings.storage_root / sub).mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    # Serve uploaded images and inspection heatmaps as static files
    uploads_dir = settings.storage_root / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    application.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    results_dir = settings.storage_root / "inspection_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    application.mount("/results", StaticFiles(directory=str(results_dir)), name="results")

    outputs_dir = BASE_DIR / "outputs"
    (outputs_dir / "visualizations").mkdir(parents=True, exist_ok=True)
    (outputs_dir / "reports").mkdir(parents=True, exist_ok=True)
    application.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

    return application


app = create_app()
