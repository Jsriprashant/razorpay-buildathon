"""The 12-month fiscal-year plan grid (FTE HC, vendor HC, budget) per team."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.calc.dates import fiscal_year_months
from app.models import PlanLine
from app.schemas.plan import PlanLineIn, PlanLineOut, PlanOut


def get_plan(db: Session, team_id: int, today: date, fy_start_month: int) -> PlanOut:
    months = fiscal_year_months(today, fy_start_month)
    existing = {
        row.month_start: row
        for row in db.query(PlanLine).filter(PlanLine.team_id == team_id, PlanLine.month_start.in_(months)).all()
    }
    lines = [
        PlanLineOut(
            month_start=m,
            planned_fte_hc=existing[m].planned_fte_hc if m in existing else 0,
            planned_vendor_hc=existing[m].planned_vendor_hc if m in existing else 0,
            planned_budget_cents=existing[m].planned_budget_cents if m in existing else 0,
        )
        for m in months
    ]
    return PlanOut(team_id=team_id, lines=lines)


def upsert_plan(db: Session, team_id: int, lines: list[PlanLineIn]) -> PlanOut:
    for line in lines:
        row = (
            db.query(PlanLine)
            .filter(PlanLine.team_id == team_id, PlanLine.month_start == line.month_start)
            .first()
        )
        if row is None:
            row = PlanLine(team_id=team_id, month_start=line.month_start)
            db.add(row)
        row.planned_fte_hc = line.planned_fte_hc
        row.planned_vendor_hc = line.planned_vendor_hc
        row.planned_budget_cents = line.planned_budget_cents
    db.commit()

    months = sorted(line.month_start for line in lines)
    rows = {
        row.month_start: row
        for row in db.query(PlanLine).filter(PlanLine.team_id == team_id, PlanLine.month_start.in_(months)).all()
    }
    return PlanOut(
        team_id=team_id,
        lines=[
            PlanLineOut(
                month_start=m,
                planned_fte_hc=rows[m].planned_fte_hc,
                planned_vendor_hc=rows[m].planned_vendor_hc,
                planned_budget_cents=rows[m].planned_budget_cents,
            )
            for m in months
        ],
    )
