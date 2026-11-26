"""CLOCKIT FastAPI application entry point."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is importable when invoked directly as `python backend/app/main.py`
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sqlalchemy import text  # noqa: E402

from backend.app.api.router import api_router  # noqa: E402
from backend.app.core.config import BASE_DIR, get_settings  # noqa: E402
from backend.app.core.logging import setup_logging  # noqa: E402
from backend.app.database.base import Base  # noqa: E402
from backend.app.database.connection import engine, init_db  # noqa: E402


def reset_brand_new() -> None:
    """Reset SQLite database and clear all runtime uploads, datasets, checkpoints, and outputs."""
    settings = get_settings()
    engine.dispose()

    unlinked = True
    for suffix in ("", "-wal", "-shm"):
        db_file = BASE_DIR / f"clockit.db{suffix}"
        if db_file.is_file():
            try:
                db_file.unlink()
            except PermissionError:
                unlinked = False

    if not unlinked:
        from backend.app.database import models  # noqa: F401
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))

    runtime_dirs = (
        settings.storage_root / "uploads",
        settings.storage_root / "inspection_results",
        settings.storage_root / "temporary",
        settings.data_root / "datasets",
        settings.data_root / "training",
        settings.data_root / "false_positives",
        settings.artifact_root / "trained",
        settings.artifact_root / "checkpoints",
        BASE_DIR / "outputs" / "reports",
        BASE_DIR / "outputs" / "visualizations",
    )
    for folder in runtime_dirs:
        if folder.is_dir():
            for item in folder.iterdir():
                if item.name == ".gitkeep":
                    continue
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    try:
                        item.unlink(missing_ok=True)
                    except OSError:
                        pass

    init_db()
    print("[CLOCKIT] Brand-new reset complete (DB + runtime files cleared; pretrained weights preserved).")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize logging, runtime directories, and SQLite tables on startup."""
    settings = get_settings()
    setup_logging(settings.log_level)
    if os.environ.pop("CLOCKIT_RESET_DB", None) == "1":
        reset_brand_new()
    else:
        init_db()
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CLOCKIT backend server")
    parser.add_argument(
        "--resetdb",
        action="store_true",
        help="Reset database and clear all runtime uploads, datasets, checkpoints, and outputs before starting.",
    )
    parser.add_argument(
        "--reset-only",
        action="store_true",
        help="Reset everything brand new and exit without starting the server.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument("--no-reload", action="store_true", help="Disable uvicorn auto-reload")
    args = parser.parse_args()

    if args.resetdb or args.reset_only:
        reset_brand_new()

    if not args.reset_only:
        import uvicorn
        uvicorn.run("backend.app.main:app", host=args.host, port=args.port, reload=not args.no_reload)
