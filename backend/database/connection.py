"""Database configuration, session management, and automatic SQLite initialization."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Project root: c:\ClockIT\UnclockThat
BASE_DIR: Path = Path(__file__).resolve().parents[2]
STORAGE_DIR: Path = BASE_DIR / "backend" / "storage"
DATASETS_DIR: Path = STORAGE_DIR / "datasets"
INSPECTIONS_DIR: Path = STORAGE_DIR / "inspections"
MODEL_WEIGHTS_DIR: Path = STORAGE_DIR / "model_weights"

DEFAULT_SQLITE_PATH: Path = BASE_DIR / "clockit.db"
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}",
)

IS_SQLITE: bool = DATABASE_URL.startswith("sqlite")


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


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


def ensure_storage_dirs() -> None:
    """Ensure local storage directories exist for datasets, inspections, and model weights."""
    for directory in (DATASETS_DIR, INSPECTIONS_DIR, MODEL_WEIGHTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    """Initialize storage directories and create all database tables if they do not exist."""
    ensure_storage_dirs()
    # Import models so SQLAlchemy registers every table on Base.metadata
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for dependency injection (e.g., FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of database operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
