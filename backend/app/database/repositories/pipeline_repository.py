"""Repository for inspection pipeline configurations."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.models.pipeline import PipelineConfig
from backend.app.database.repositories.base import BaseRepository


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
