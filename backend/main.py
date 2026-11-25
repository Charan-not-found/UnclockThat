"""CLOCKIT / PROMETHEUS-X backend entry point with automatic SQLite initialization."""

from __future__ import annotations

from backend.database.connection import (
    DATABASE_URL,
    DATASETS_DIR,
    INSPECTIONS_DIR,
    MODEL_WEIGHTS_DIR,
    init_db,
)


def main() -> None:
    """Initialize the local storage directories and SQLite database."""
    init_db()
    print(f"Database initialized at: {DATABASE_URL}")
    print(f"Datasets storage:      {DATASETS_DIR}")
    print(f"Inspections storage:   {INSPECTIONS_DIR}")
    print(f"Model weights storage: {MODEL_WEIGHTS_DIR}")


if __name__ == "__main__":
    main()
