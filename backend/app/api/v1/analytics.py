"""Analytics endpoints — server-side aggregated per Scanner Unit or globally."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.database.models.inspection import InspectionRecord, SeverityScore
from backend.app.database.models.scanner import ScannerUnit

router = APIRouter(prefix="/analytics", tags=["analytics"])


class DailyPoint(BaseModel):
    day: str
    inspections: int
    anomalies: int
    reviews: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class StatusCount(BaseModel):
    status: str
    count: int


class AnalyticsSummaryOut(BaseModel):
    total_inspections: int
    pass_count: int
    fail_count: int
    review_count: int
    pass_rate_pct: Optional[float]
    anomaly_rate_pct: Optional[float]
    date_range_days: int
    scanner_unit_id: Optional[int] = None
    note: str = "All metrics computed from persisted inspection records."


class ScannerUnitStatsOut(BaseModel):
    scanner_unit_id: Optional[int]
    scanner_unit_name: str
    total_inspections: int
    pass_count: int
    fail_count: int
    review_count: int
    pass_rate_pct: Optional[float]
    anomaly_rate_pct: Optional[float]


def _filtered_records(db: Session, days: int, scanner_unit_id: Optional[int]) -> list[InspectionRecord]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(InspectionRecord)
    if scanner_unit_id is not None:
        stmt = stmt.where(InspectionRecord.scanner_unit_id == scanner_unit_id)
    records = list(db.scalars(stmt).all())
    in_range: list[InspectionRecord] = []
    for r in records:
        ts = r.inspected_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= since:
            in_range.append(r)
    return in_range


@router.get("/summary", response_model=AnalyticsSummaryOut)
def get_summary(
    days: int = 30,
    scanner_unit_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> AnalyticsSummaryOut:
    in_range = _filtered_records(db, days, scanner_unit_id)
    total = len(in_range)
    pass_count = sum(1 for r in in_range if r.overall_decision == "PASS")
    fail_count = sum(1 for r in in_range if r.overall_decision == "FAIL")
    review_count = sum(1 for r in in_range if r.overall_decision == "REVIEW_REQUIRED")

    return AnalyticsSummaryOut(
        total_inspections=total,
        pass_count=pass_count,
        fail_count=fail_count,
        review_count=review_count,
        pass_rate_pct=round(pass_count / total * 100, 1) if total else None,
        anomaly_rate_pct=round((fail_count + review_count) / total * 100, 1) if total else None,
        date_range_days=days,
        scanner_unit_id=scanner_unit_id,
    )


@router.get("/trend", response_model=list[DailyPoint])
def get_trend(
    days: int = 7,
    scanner_unit_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> list[DailyPoint]:
    in_range = _filtered_records(db, days, scanner_unit_id)
    day_map: dict[str, dict] = {}
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%a %d")
        day_map[d] = {"inspections": 0, "anomalies": 0, "reviews": 0}

    for r in in_range:
        ts = r.inspected_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        label = ts.strftime("%a %d")
        if label in day_map:
            day_map[label]["inspections"] += 1
            if r.overall_decision == "FAIL":
                day_map[label]["anomalies"] += 1
            if r.overall_decision == "REVIEW_REQUIRED":
                day_map[label]["reviews"] += 1

    return [DailyPoint(day=k, **v) for k, v in day_map.items()]


@router.get("/severity-distribution", response_model=list[SeverityCount])
def severity_distribution(
    days: int = 30,
    scanner_unit_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> list[SeverityCount]:
    in_range_ids = {r.id for r in _filtered_records(db, days, scanner_unit_id)}
    if not in_range_ids:
        return []
    all_sev = list(db.scalars(select(SeverityScore)).all())
    counts: Counter = Counter()
    for s in all_sev:
        if s.inspection_id in in_range_ids:
            counts[s.severity_level] += 1
    return [SeverityCount(severity=k, count=v) for k, v in counts.most_common()]


@router.get("/status-distribution", response_model=list[StatusCount])
def status_distribution(
    days: int = 30,
    scanner_unit_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> list[StatusCount]:
    in_range = _filtered_records(db, days, scanner_unit_id)
    counts: Counter = Counter()
    label_map = {"PASS": "Completed", "FAIL": "Failed", "REVIEW_REQUIRED": "Needs review"}
    for r in in_range:
        label = label_map.get(r.overall_decision or "PASS", "Completed")
        counts[label] += 1
    return [StatusCount(status=k, count=v) for k, v in counts.most_common()]


@router.get("/by-scanner-unit", response_model=list[ScannerUnitStatsOut])
def analytics_by_scanner_unit(
    days: int = 30,
    db: Session = Depends(get_db),
) -> list[ScannerUnitStatsOut]:
    """Return inspection breakdown grouped by Scanner Unit."""
    in_range = _filtered_records(db, days, scanner_unit_id=None)
    units = {u.id: u.name for u in db.scalars(select(ScannerUnit)).all()}

    grouped: dict[Optional[int], list[InspectionRecord]] = {}
    for uid in units:
        grouped[uid] = []
    for r in in_range:
        grouped.setdefault(r.scanner_unit_id, []).append(r)

    out: list[ScannerUnitStatsOut] = []
    for uid, recs in grouped.items():
        total = len(recs)
        pass_c = sum(1 for r in recs if r.overall_decision == "PASS")
        fail_c = sum(1 for r in recs if r.overall_decision == "FAIL")
        rev_c = sum(1 for r in recs if r.overall_decision == "REVIEW_REQUIRED")
        name = units.get(uid, "Unassigned / Default") if uid is not None else "Unassigned / Default"
        if uid is None and total == 0:
            continue
        out.append(ScannerUnitStatsOut(
            scanner_unit_id=uid,
            scanner_unit_name=name,
            total_inspections=total,
            pass_count=pass_c,
            fail_count=fail_c,
            review_count=rev_c,
            pass_rate_pct=round(pass_c / total * 100, 1) if total else None,
            anomaly_rate_pct=round((fail_c + rev_c) / total * 100, 1) if total else None,
        ))
    return out
