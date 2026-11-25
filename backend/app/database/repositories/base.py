"""Generic base repository for dialect-agnostic CRUD."""

from __future__ import annotations

from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository providing standard CRUD operations."""

    def __init__(self, session: Session, model: Type[ModelT]) -> None:
        self.session = session
        self.model = model

    def create(self, **kwargs) -> ModelT:
        """Create and persist a new model instance."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def get_by_id(self, record_id: int) -> Optional[ModelT]:
        """Fetch a single record by primary key."""
        return self.session.get(self.model, record_id)

    def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        """Return paginated records."""
        stmt = select(self.model).offset(offset).limit(limit)
        return self.session.scalars(stmt).all()

    def update(self, instance: ModelT, **kwargs) -> ModelT:
        """Update attributes on an existing model instance."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        """Delete a model instance."""
        self.session.delete(instance)
        self.session.flush()
