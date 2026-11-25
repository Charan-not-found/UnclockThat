"""Pytest fixtures for CLOCKIT backend tests."""

from __future__ import annotations

import pytest

from backend.app.database import init_db


@pytest.fixture(scope="session", autouse=True)
def initialize_database() -> None:
    """Ensure SQLite tables and runtime directories exist before tests run."""
    init_db()
