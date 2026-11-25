"""Repository layer abstracting database CRUD and queries across dialects."""

from __future__ import annotations

from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.database.connection import Base
from backend.database.models import (
    AnomalyResult,
    InspectionRecord,
    ManufacturerProfile,
    ModelConfig,
    PipelineConfig,
    SeverityScore,
    User,
)

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


class PipelineConfigRepository(BaseRepository[PipelineConfig]):
    """Repository for inspection pipeline configurations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, PipelineConfig)

    def list_active_by_manufacturer(self, manufacturer_id: int) -> Sequence[PipelineConfig]:
        stmt = select(PipelineConfig).where(
            PipelineConfig.manufacturer_id == manufacturer_id,
            PipelineConfig.is_active.is_(True),
        )
        return self.session.scalars(stmt).all()


class InspectionRepository(BaseRepository[InspectionRecord]):
    """Repository for inspection records."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, InspectionRecord)

    def get_with_results(self, inspection_id: int) -> Optional[InspectionRecord]:
        stmt = (
            select(InspectionRecord)
            .options(
                selectinload(InspectionRecord.anomaly_results),
                selectinload(InspectionRecord.severity_scores),
            )
            .where(InspectionRecord.id == inspection_id)
        )
        return self.session.scalar(stmt)

    def list_by_manufacturer(
        self, manufacturer_id: int, limit: int = 100, offset: int = 0
    ) -> Sequence[InspectionRecord]:
        stmt = (
            select(InspectionRecord)
            .where(InspectionRecord.manufacturer_id == manufacturer_id)
            .order_by(InspectionRecord.inspected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.scalars(stmt).all()


class AnomalyResultRepository(BaseRepository[AnomalyResult]):
    """Repository for anomaly detection results."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, AnomalyResult)

    def list_by_inspection(self, inspection_id: int) -> Sequence[AnomalyResult]:
        stmt = select(AnomalyResult).where(AnomalyResult.inspection_id == inspection_id)
        return self.session.scalars(stmt).all()


class SeverityScoreRepository(BaseRepository[SeverityScore]):
    """Repository for severity score records."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, SeverityScore)

    def list_requiring_review(self, limit: int = 100) -> Sequence[SeverityScore]:
        stmt = (
            select(SeverityScore)
            .where(SeverityScore.requires_human_review.is_(True))
            .order_by(SeverityScore.created_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()
