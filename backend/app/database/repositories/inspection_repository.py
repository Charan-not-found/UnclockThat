"""Repositories for inspection records, anomaly results, and severity scores."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.database.models.inspection import AnomalyResult, InspectionRecord, SeverityScore
from backend.app.database.repositories.base import BaseRepository


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
