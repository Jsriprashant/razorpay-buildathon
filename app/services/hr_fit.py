"""Informational plan-fit / budget-fit badges shown in the HR inbox. These
are advisory only — HR may always approve regardless of what they say
(Section: hiring requests spec). The comparison is intentionally simple: it
compares the request against other already-APPROVED requests of the same
type active in the request's target month, versus that month's plan line.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import HiringRequest, PlanLine, RequestStatus, RequestType

NO_DATA = "NO_DATA"
WITHIN_PLAN = "WITHIN_PLAN"
EXCEEDS_PLAN = "EXCEEDS_PLAN"
WITHIN_BUDGET = "WITHIN_BUDGET"
OVER_BUDGET = "OVER_BUDGET"


def _monthly_cost_cents(req: HiringRequest) -> int:
    if req.type == RequestType.FTE:
        return (req.annual_salary_cents or 0) // 12
    return (req.hourly_rate_cents or 0) * (req.hours_per_month or 0) * req.quantity


def compute_fit(db: Session, req: HiringRequest) -> tuple[str, str]:
    month = date(req.target_start_date.year, req.target_start_date.month, 1)
    plan = db.query(PlanLine).filter(PlanLine.team_id == req.team_id, PlanLine.month_start == month).first()
    if plan is None:
        return NO_DATA, NO_DATA

    committed_hc = 0
    committed_cost = 0
    others = (
        db.query(HiringRequest)
        .filter(
            HiringRequest.team_id == req.team_id,
            HiringRequest.type == req.type,
            HiringRequest.status == RequestStatus.APPROVED,
            HiringRequest.id != req.id,
        )
        .all()
    )
    for other in others:
        other_start = date(other.target_start_date.year, other.target_start_date.month, 1)
        other_end = date(other.end_date.year, other.end_date.month, 1) if other.end_date else None
        if other_start <= month and (other_end is None or other_end >= month):
            committed_hc += other.quantity
            committed_cost += _monthly_cost_cents(other)

    planned_hc = plan.planned_fte_hc if req.type == RequestType.FTE else plan.planned_vendor_hc
    plan_fit = WITHIN_PLAN if committed_hc + req.quantity <= planned_hc else EXCEEDS_PLAN

    this_cost = _monthly_cost_cents(req)
    budget_fit = WITHIN_BUDGET if committed_cost + this_cost <= plan.planned_budget_cents else OVER_BUDGET

    return plan_fit, budget_fit
