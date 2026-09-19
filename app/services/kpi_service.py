"""Home KPI cards — all computed live from the roster/plan/request/vendor
tables, never stored. See the 12-card list in the task spec."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.calc.dates import active_days_in_month, days_in_month, is_active_on
from app.calc.money import fte_month_cost_cents, format_cents, vendor_month_cost_cents
from app.models import (
    Cycle,
    CycleSummary,
    EngagementStatus,
    HiringRequest,
    PlanLine,
    Position,
    PositionStatus,
    RequestStatus,
    RequestType,
    VendorEngagement,
    Worker,
)
from app.schemas.kpi import KpiCard, KpiOut
from app.services import forecast_service, recon_service, settings_service


def _month_actual_and_committed_cost(db: Session, team_id: int, today: date) -> tuple[int, int, int, int]:
    """Returns (actual_fte_hc, actual_vendor_hc, actual_cost_cents, committed_cost_cents) for the current month."""
    current_month = date(today.year, today.month, 1)
    dim = days_in_month(current_month.year, current_month.month)

    workers = db.query(Worker).filter(Worker.team_id == team_id).all()
    actual_fte_hc = sum(1 for w in workers if is_active_on(w.hire_date, w.termination_date, today))
    actual_cost = 0
    for w in workers:
        active_days = active_days_in_month(w.hire_date, w.termination_date, current_month)
        if active_days > 0:
            actual_cost += fte_month_cost_cents(w.annual_salary_cents, active_days, dim)

    engagements = (
        db.query(VendorEngagement)
        .join(HiringRequest, VendorEngagement.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id)
        .all()
    )
    actual_vendor_hc = 0
    committed_cost = 0
    for eng in engagements:
        if eng.status == EngagementStatus.CONFIRMED:
            if is_active_on(eng.start_date, eng.end_date, today):
                actual_vendor_hc += eng.headcount
            active_days = active_days_in_month(eng.start_date, eng.end_date, current_month)
            if active_days > 0:
                actual_cost += vendor_month_cost_cents(eng.headcount, eng.hourly_rate_cents, eng.hours_per_month, active_days, dim)
        elif eng.status not in (EngagementStatus.DECLINED, EngagementStatus.CANCELLED):
            active_days = active_days_in_month(eng.start_date, eng.end_date, current_month)
            if active_days > 0:
                committed_cost += vendor_month_cost_cents(eng.headcount, eng.hourly_rate_cents, eng.hours_per_month, active_days, dim)

    open_fte_positions = (
        db.query(Position, HiringRequest)
        .join(HiringRequest, Position.request_id == HiringRequest.id)
        .filter(
            HiringRequest.team_id == team_id,
            HiringRequest.type == RequestType.FTE,
            HiringRequest.status == RequestStatus.APPROVED,
            Position.status == PositionStatus.OPEN,
        )
        .all()
    )
    for _position, req in open_fte_positions:
        if req.target_start_date <= date(current_month.year, current_month.month, dim):
            active_days = active_days_in_month(req.target_start_date, None, current_month)
            if active_days > 0 and req.annual_salary_cents:
                committed_cost += fte_month_cost_cents(req.annual_salary_cents, active_days, dim)

    return actual_fte_hc, actual_vendor_hc, actual_cost, committed_cost


def compute_kpis(db: Session, team_id: int, today: date) -> KpiOut:
    currency = settings_service.get_value(db, "currency") or "USD"
    current_month = date(today.year, today.month, 1)

    plan_line = db.query(PlanLine).filter(PlanLine.team_id == team_id, PlanLine.month_start == current_month).first()
    plan_fte_hc = plan_line.planned_fte_hc if plan_line else 0
    plan_vendor_hc = plan_line.planned_vendor_hc if plan_line else 0
    plan_budget = plan_line.planned_budget_cents if plan_line else 0

    actual_fte_hc, actual_vendor_hc, actual_cost, committed_cost = _month_actual_and_committed_cost(db, team_id, today)

    # actual - plan: positive = over budget, negative = under budget.
    variance = actual_cost - plan_budget
    variance_pct = (variance / plan_budget * 100) if plan_budget else 0.0
    available_budget = plan_budget - actual_cost - committed_cost

    closed_summaries = (
        db.query(Cycle, CycleSummary)
        .join(CycleSummary, CycleSummary.cycle_id == Cycle.id)
        .filter(Cycle.team_id == team_id)
        .all()
    )
    unspent_earlier = sum(s.plan_budget_cents - s.actual_cost_cents for _c, s in closed_summaries)
    ytd_actual = sum(s.actual_cost_cents for _c, s in closed_summaries) + actual_cost
    ytd_plan = sum(s.plan_budget_cents for _c, s in closed_summaries) + plan_budget

    forecast = forecast_service.compute_forecast(db, team_id, today)
    fy_plan_sum = ytd_plan + sum(mp.plan_cost_cents for mp in forecast.months)
    year_end_no_action = ytd_actual + sum(mp.no_action_cost_cents for mp in forecast.months)
    year_end_with_suggestions = ytd_actual + sum(mp.with_suggestions_cost_cents for mp in forecast.months)

    pipeline_requests = (
        db.query(HiringRequest)
        .filter(
            HiringRequest.team_id == team_id,
            HiringRequest.status == RequestStatus.SUBMITTED,
        )
        .count()
    )
    approved_unfilled = (
        db.query(Position)
        .join(HiringRequest, Position.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id, Position.status == PositionStatus.OPEN)
        .count()
    )
    pipeline_count = pipeline_requests + approved_unfilled
    months_elapsed = max(1, len(closed_summaries) + 1)
    pipeline_run_rate = round(pipeline_count / months_elapsed, 2)

    open_positions = (
        db.query(Position, HiringRequest)
        .join(HiringRequest, Position.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id, Position.status == PositionStatus.OPEN)
        .all()
    )
    open_positions_count = len(open_positions)

    def _opened_on(req: HiringRequest) -> date:
        # "Days open" measures how long the position has been open for hiring,
        # i.e. since it was approved — not since its (possibly future or past)
        # target start date.
        if req.approved_at:
            return req.approved_at.date()
        if req.submitted_at:
            return req.submitted_at.date()
        return req.created_at.date()

    avg_days_open = (
        round(sum((today - _opened_on(req)).days for _p, req in open_positions) / open_positions_count, 1)
        if open_positions_count
        else 0
    )

    engagements = (
        db.query(VendorEngagement)
        .join(HiringRequest, VendorEngagement.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id, VendorEngagement.status == EngagementStatus.CONFIRMED)
        .all()
    )

    def _expiring_within(days: int) -> int:
        return sum(
            1
            for e in engagements
            if e.end_date is not None and 0 <= (e.end_date - today).days <= days
        )

    expiring_30 = _expiring_within(30)
    expiring_60 = _expiring_within(60)
    expiring_90 = _expiring_within(90)

    recon = recon_service.get_recon(db, team_id, current_month, today)
    unresolved_flags = recon.unresolved_flag_count

    cards = [
        KpiCard(
            key="headcount_vs_plan",
            label="Headcount vs plan",
            formula="Active FTE/vendor headcount today vs this month's plan_line.",
            value=actual_fte_hc,
            display=f"{actual_fte_hc} / {plan_fte_hc} FTE · {actual_vendor_hc} / {plan_vendor_hc} vendor",
            click_through="/roster",
        ),
        KpiCard(
            key="cost_this_month",
            label="Cost this month",
            formula="FTE cost(month) for active workers + vendor cost(month) for CONFIRMED engagements.",
            value=actual_cost,
            display=format_cents(actual_cost, currency),
            click_through="/recon",
        ),
        KpiCard(
            key="plan_this_month",
            label="Plan this month",
            formula="plan_line.planned_budget_cents for the current month.",
            value=plan_budget,
            display=format_cents(plan_budget, currency),
            click_through="/plan",
        ),
        KpiCard(
            key="variance",
            label="Variance",
            formula="Cost this month - plan this month (positive = over plan, negative = under plan).",
            value=variance,
            display=f"{format_cents(variance, currency)} ({variance_pct:+.1f}%)",
            click_through="/recon",
        ),
        KpiCard(
            key="available_budget",
            label="Available budget",
            formula="Plan - actual cost - committed cost (open positions + unconfirmed vendor engagements).",
            value=available_budget,
            display=format_cents(available_budget, currency),
            click_through="/plan",
        ),
        KpiCard(
            key="unspent_earlier",
            label="Unspent from earlier months",
            formula="Sum over closed cycles this fiscal year of (plan_budget - actual_cost). Informational only.",
            value=unspent_earlier,
            display=format_cents(unspent_earlier, currency),
            secondary="Info only — not added back to this month's budget.",
            click_through="/history",
        ),
        KpiCard(
            key="ytd_actual_vs_plan",
            label="YTD actual vs plan",
            formula="Closed cycle_summary sums + current month.",
            value=ytd_actual,
            display=f"{format_cents(ytd_actual, currency)} / {format_cents(ytd_plan, currency)}",
            click_through="/history",
        ),
        KpiCard(
            key="year_end_outlook",
            label="Year-end outlook",
            formula="YTD actual + projected remaining months (no action / with suggestions) vs fiscal-year plan.",
            value=year_end_with_suggestions,
            display=(
                f"{format_cents(year_end_with_suggestions, currency)} (with suggestions) · "
                f"{format_cents(year_end_no_action, currency)} (no action) vs plan "
                f"{format_cents(fy_plan_sum, currency)}"
            ),
            click_through="/forecast",
        ),
        KpiCard(
            key="pipeline",
            label="Pipeline",
            formula="Submitted requests + approved-unfilled positions; run-rate = pipeline / months elapsed.",
            value=pipeline_count,
            display=f"{pipeline_count} in flight · {pipeline_run_rate}/month",
            click_through="/requests",
        ),
        KpiCard(
            key="open_positions",
            label="Open positions",
            formula="Count of OPEN positions; average days open = today - approved_at (date the request was approved), averaged.",
            value=open_positions_count,
            display=f"{open_positions_count} open · avg {avg_days_open}d",
            click_through="/recon",
        ),
        KpiCard(
            key="vendor_expiring",
            label="Vendor contracts expiring",
            formula="CONFIRMED engagements with end_date within 30/60/90 days.",
            value=expiring_30,
            display=f"{expiring_30} in 30d · {expiring_60} in 60d · {expiring_90} in 90d",
            click_through="/vendors",
        ),
        KpiCard(
            key="unresolved_recon_flags",
            label="Unresolved recon flags",
            formula="Count of UNPLANNED_HIRE / UNFILLED_OVERDUE / PLAN_VARIANCE flags without a recon_resolution.",
            value=unresolved_flags,
            display=str(unresolved_flags),
            click_through="/recon",
        ),
    ]

    summary = (
        f"This month, actual headcount is {actual_fte_hc} FTE and {actual_vendor_hc} vendor against a plan of "
        f"{plan_fte_hc} FTE and {plan_vendor_hc} vendor. Spend is {format_cents(actual_cost, currency)} against a "
        f"{format_cents(plan_budget, currency)} plan, a variance of {format_cents(variance, currency)} "
        f"({variance_pct:+.1f}%). Year-end outlook is {format_cents(year_end_with_suggestions, currency)} with "
        f"suggestions applied versus a fiscal-year plan of {format_cents(fy_plan_sum, currency)}. "
        f"There {'is' if unresolved_flags == 1 else 'are'} {unresolved_flags} unresolved reconciliation "
        f"flag{'s' if unresolved_flags != 1 else ''} to review."
    )

    return KpiOut(team_id=team_id, period_month=current_month, cards=cards, variance_summary=summary)
