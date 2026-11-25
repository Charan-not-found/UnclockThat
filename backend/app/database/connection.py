"""Database engine, session management, and automatic SQLite initialization."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import BASE_DIR, get_settings
from backend.app.database.base import Base

settings = get_settings()
DATABASE_URL: str = settings.database_url
IS_SQLITE: bool = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=True,
    future=True,
)

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        """Enable SQLite foreign key constraint enforcement."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def ensure_runtime_dirs() -> None:
    """Ensure active local data, artifacts, storage, and outputs directories exist."""
    dirs = [
        settings.data_root / sub
        for sub in ("datasets", "training", "false_positives", "raw")
    ] + [
        settings.artifact_root / sub
        for sub in ("pretrained", "trained", "checkpoints")
    ] + [
        settings.storage_root / sub
        for sub in ("uploads", "inspection_results", "temporary")
    ] + [
        BASE_DIR / "outputs" / sub
        for sub in ("reports", "visualizations")
    ]
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    """Initialize runtime directories and create all database tables if missing."""
    ensure_runtime_dirs()
    from backend.app.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Transactional context manager for service/script database operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
