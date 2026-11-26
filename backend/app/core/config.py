"""Application settings loaded from environment variables and defaults."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: c:\ClockIT\UnclockThat
BASE_DIR: Path = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Typed application settings for CLOCKIT."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PROMETHEUS-X"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = f"sqlite:///{(BASE_DIR / 'clockit.db').as_posix()}"

    data_root: Path = BASE_DIR / "data"
    artifact_root: Path = BASE_DIR / "artifacts"
    models_root: Path = BASE_DIR / "models"
    base_models_dir: Path = BASE_DIR / "models" / "base"
    custom_models_dir: Path = BASE_DIR / "models" / "custom"
    storage_root: Path = BASE_DIR / "storage"

    default_device: str = "auto"
    log_level: str = "INFO"
    max_upload_mb: int = 50


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
