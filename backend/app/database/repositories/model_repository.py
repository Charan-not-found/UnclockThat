"""Repositories for manufacturer profiles, users, and model configurations."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.models.manufacturer import ManufacturerProfile, User
from backend.app.database.models.model_config import ModelConfig
from backend.app.database.repositories.base import BaseRepository


class ManufacturerRepository(BaseRepository[ManufacturerProfile]):
    """Repository for manufacturer profiles."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ManufacturerProfile)

    def get_by_name(self, name: str) -> Optional[ManufacturerProfile]:
        stmt = select(ManufacturerProfile).where(ManufacturerProfile.name == name)
        return self.session.scalar(stmt)


class UserRepository(BaseRepository[User]):
    """Repository for platform users."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.session.scalar(stmt)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.session.scalar(stmt)

    def list_by_manufacturer(self, manufacturer_id: int) -> Sequence[User]:
        stmt = select(User).where(User.manufacturer_id == manufacturer_id)
        return self.session.scalars(stmt).all()


class ModelConfigRepository(BaseRepository[ModelConfig]):
    """Repository for AI model configurations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ModelConfig)

    def list_active_by_manufacturer(self, manufacturer_id: int) -> Sequence[ModelConfig]:
        stmt = select(ModelConfig).where(
            ModelConfig.manufacturer_id == manufacturer_id,
            ModelConfig.is_active.is_(True),
        )
        return self.session.scalars(stmt).all()
