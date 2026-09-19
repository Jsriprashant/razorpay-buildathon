"""The deterministic (non-ML) forecast: projected headcount, month-over-month
gaps, cumulative-need suggestions, and plan/no-action/with-suggestions cost
scenarios. All the actual math lives in app/calc/forecast.py (pure); this
module only pulls the DB inputs those functions need."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.calc.dates import active_days_in_month, add_months, days_in_month, fiscal_year_months, is_active_on, month_end, months_between
from app.calc.forecast import (
    MonthGap,
    Suggestion,
    attrition_loss_hc,
    compute_suggestions,
    cumulative_suggested_hc_by_month,
    fte_monthly_cost_for_hc,
    month_gap,
    projected_fte_hc as calc_projected_fte_hc,
    projected_vendor_hc as calc_projected_vendor_hc,
    vendor_monthly_cost_for_hc,
)
from app.calc.money import fte_month_cost_cents, vendor_month_cost_cents
from app.models import (
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
from app.schemas.forecast import ForecastOut, MonthPoint, SuggestionOut, WhatIfMonthPoint, WhatIfOut, WhatIfRequest
from app.services import settings_service

DISCLOSURE_TEXT = """How this forecast is calculated (no AI/ML — pure formulas on your data):

For each future month, projected FTE headcount = your current roster's headcount on that month's last day (already
known hires and already-recorded future exits) minus expected attrition (today's active FTE count x monthly
attrition % x months ahead, rounded once) plus any OPEN position on an APPROVED FTE request whose target start date
falls on or before that month.

Projected vendor headcount = the total headcount of every vendor engagement that isn't DECLINED or CANCELLED and is
active on that month's last day (confirmed and not-yet-confirmed engagements are broken out separately).

The gap for a month is your plan for that month minus the projection. Suggestions walk the months in order,
tracking how much headcount has already been suggested (cum): each month only suggests the *new* amount needed
beyond what's already queued up, dated to start at the beginning of that month, with a "raise request by" date
equal to the start date minus the type's lead time (45 days for FTE, 14 days for vendor, both configurable in
Settings). If that date has already passed, the suggestion is flagged URGENT.

Cost curves are built line by line, not from a single blended rate: each currently-employed worker is costed at
their own salary for the days they're still active in the month; each OPEN position on an approved request is
costed at that request's own salary from its target start date; each vendor engagement is costed at its own hourly
rate for the days it's active. Attrition's cost impact (since it isn't tied to any specific named worker) is removed
at the team's current average salary. Suggested future hires — which don't have a real position yet — are costed at
the same team averages. No compounding, no random variation, the same numbers every time you load this page."""


def _team_open_approved_fte_positions(db: Session, team_id: int) -> list[tuple[Position, HiringRequest]]:
    return (
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


def _team_vendor_engagements(db: Session, team_id: int, exclude_statuses: set) -> list[VendorEngagement]:
    return (
        db.query(VendorEngagement)
        .join(HiringRequest, VendorEngagement.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id, ~VendorEngagement.status.in_(exclude_statuses))
        .all()
    )


def _avg_fte_annual_salary_cents(db: Session, team_id: int, today: date) -> int:
    workers = db.query(Worker).filter(Worker.team_id == team_id).all()
    active = [w for w in workers if is_active_on(w.hire_date, w.termination_date, today)]
    if not active:
        return 0
    return round(sum(w.annual_salary_cents for w in active) / len(active))


def _latest_vendor_hourly_rate_cents(db: Session, team_id: int) -> int:
    engagement = (
        db.query(VendorEngagement)
        .join(HiringRequest, VendorEngagement.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id)
        .order_by(VendorEngagement.start_date.desc())
        .first()
    )
    return engagement.hourly_rate_cents if engagement else 0


def _future_months(today: date, fy_start_month: int) -> list[date]:
    fy_months = fiscal_year_months(today, fy_start_month)
    current_month = date(today.year, today.month, 1)
    return [m for m in fy_months if m > current_month]


def _fte_no_action_cost_cents(
    workers_today: list[Worker],
    open_positions: list[tuple[Position, HiringRequest]],
    month: date,
    L: date,
    actual_fte_hc_today: int,
    attrition_pct_monthly: float,
    k: int,
    avg_salary: int,
    position_target_cutoff: date | None = None,
) -> int:
    """Line-item FTE cost for a future month: each still-active worker at
    their own salary, plus each OPEN approved position at its own request
    salary from its target start date, minus attrition's cost impact valued
    at the team average (attrition isn't tied to a specific named worker).
    `position_target_cutoff` lets what-if scenarios shift *when* a position's
    target start counts as "reached" (hiring delay) without faking day math.
    """
    dim = days_in_month(month.year, month.month)
    cost = 0
    for w in workers_today:
        active_days = active_days_in_month(w.hire_date, w.termination_date, month)
        if active_days > 0 and is_active_on(w.hire_date, w.termination_date, L):
            cost += fte_month_cost_cents(w.annual_salary_cents, active_days, dim)

    cutoff = position_target_cutoff if position_target_cutoff is not None else L
    for position, req in open_positions:
        if req.target_start_date <= cutoff:
            active_days = active_days_in_month(req.target_start_date, None, month)
            if active_days > 0:
                salary = req.annual_salary_cents or avg_salary
                if salary:
                    cost += fte_month_cost_cents(salary, active_days, dim)

    loss_hc = attrition_loss_hc(actual_fte_hc_today, attrition_pct_monthly, k)
    if loss_hc > 0 and avg_salary:
        cost -= fte_monthly_cost_for_hc(loss_hc, avg_salary)

    return max(cost, 0)


def _vendor_no_action_cost_cents(engagements: list[VendorEngagement], month: date) -> int:
    dim = days_in_month(month.year, month.month)
    cost = 0
    for eng in engagements:
        active_days = active_days_in_month(eng.start_date, eng.end_date, month)
        if active_days > 0:
            cost += vendor_month_cost_cents(eng.headcount, eng.hourly_rate_cents, eng.hours_per_month, active_days, dim)
    return cost


def compute_forecast(db: Session, team_id: int, today: date) -> ForecastOut:
    fy_start_month = settings_service.get_int(db, "fy_start_month", 1)
    attrition_pct_monthly = settings_service.get_float(db, "attrition_pct_monthly", 0.0)
    fte_lead_days = settings_service.get_int(db, "fte_lead_days", 45)
    vendor_lead_days = settings_service.get_int(db, "vendor_lead_days", 14)
    vendor_hours_per_month = settings_service.get_int(db, "vendor_hours_per_month", 160)

    future_months = _future_months(today, fy_start_month)
    current_month = date(today.year, today.month, 1)

    workers_today = db.query(Worker).filter(Worker.team_id == team_id).all()
    actual_fte_hc_today = sum(1 for w in workers_today if is_active_on(w.hire_date, w.termination_date, today))
    avg_salary = _avg_fte_annual_salary_cents(db, team_id, today)
    vendor_rate = _latest_vendor_hourly_rate_cents(db, team_id)
    open_positions = _team_open_approved_fte_positions(db, team_id)
    vendor_engagements = _team_vendor_engagements(db, team_id, {EngagementStatus.DECLINED, EngagementStatus.CANCELLED})

    plan_by_month = {
        row.month_start: row
        for row in db.query(PlanLine).filter(PlanLine.team_id == team_id, PlanLine.month_start.in_(future_months)).all()
    }

    projected_fte_by_month: dict[date, int] = {}
    projected_vendor_by_month: dict[date, int] = {}
    no_action_fte_cost_by_month: dict[date, int] = {}
    no_action_vendor_cost_by_month: dict[date, int] = {}
    fte_gaps: list[MonthGap] = []
    vendor_gaps: list[MonthGap] = []

    for m in future_months:
        k = months_between(current_month, m)
        L = month_end(m)
        roster_hc_at_L = sum(1 for w in workers_today if is_active_on(w.hire_date, w.termination_date, L))
        open_positions_count = sum(1 for _p, req in open_positions if req.target_start_date <= L)
        projected_fte = calc_projected_fte_hc(roster_hc_at_L, actual_fte_hc_today, attrition_pct_monthly, k, open_positions_count)
        projected_vendor = calc_projected_vendor_hc(
            sum(e.headcount for e in vendor_engagements if is_active_on(e.start_date, e.end_date, L))
        )
        projected_fte_by_month[m] = projected_fte
        projected_vendor_by_month[m] = projected_vendor

        no_action_fte_cost_by_month[m] = _fte_no_action_cost_cents(
            workers_today, open_positions, m, L, actual_fte_hc_today, attrition_pct_monthly, k, avg_salary
        )
        no_action_vendor_cost_by_month[m] = _vendor_no_action_cost_cents(vendor_engagements, m)

        plan_line = plan_by_month.get(m)
        plan_fte_hc = plan_line.planned_fte_hc if plan_line else 0
        plan_vendor_hc = plan_line.planned_vendor_hc if plan_line else 0
        fte_gaps.append(MonthGap(m, month_gap(plan_fte_hc, projected_fte)))
        vendor_gaps.append(MonthGap(m, month_gap(plan_vendor_hc, projected_vendor)))

    fte_suggestions = compute_suggestions("FTE", fte_gaps, fte_lead_days, today)
    vendor_suggestions = compute_suggestions("VENDOR", vendor_gaps, vendor_lead_days, today)

    fte_cum = cumulative_suggested_hc_by_month(fte_suggestions, future_months)
    vendor_cum = cumulative_suggested_hc_by_month(vendor_suggestions, future_months)

    months_out: list[MonthPoint] = []
    for m in future_months:
        plan_line = plan_by_month.get(m)
        plan_fte_hc = plan_line.planned_fte_hc if plan_line else 0
        plan_vendor_hc = plan_line.planned_vendor_hc if plan_line else 0
        plan_cost = plan_line.planned_budget_cents if plan_line else 0

        projected_fte = projected_fte_by_month[m]
        projected_vendor = projected_vendor_by_month[m]
        with_sugg_fte = projected_fte + fte_cum.get(m, 0)
        with_sugg_vendor = projected_vendor + vendor_cum.get(m, 0)

        no_action_cost = no_action_fte_cost_by_month[m] + no_action_vendor_cost_by_month[m]
        with_sugg_cost = (
            no_action_fte_cost_by_month[m]
            + fte_monthly_cost_for_hc(fte_cum.get(m, 0), avg_salary)
            + no_action_vendor_cost_by_month[m]
            + vendor_monthly_cost_for_hc(vendor_cum.get(m, 0), vendor_rate, vendor_hours_per_month)
        )

        months_out.append(
            MonthPoint(
                month_start=m,
                plan_fte_hc=plan_fte_hc,
                plan_vendor_hc=plan_vendor_hc,
                projected_fte_hc=projected_fte,
                projected_vendor_hc=projected_vendor,
                with_suggestions_fte_hc=with_sugg_fte,
                with_suggestions_vendor_hc=with_sugg_vendor,
                plan_cost_cents=plan_cost,
                no_action_cost_cents=no_action_cost,
                with_suggestions_cost_cents=with_sugg_cost,
            )
        )

    suggestions_out = _suggestions_to_out(fte_suggestions, vendor_suggestions, avg_salary, vendor_rate, vendor_hours_per_month)

    return ForecastOut(
        team_id=team_id,
        generated_on=today,
        months=months_out,
        suggestions=suggestions_out,
        disclosure=DISCLOSURE_TEXT,
    )


def _suggestions_to_out(
    fte_suggestions: list[Suggestion],
    vendor_suggestions: list[Suggestion],
    avg_salary: int,
    vendor_rate: int,
    vendor_hours_per_month: int,
) -> list[SuggestionOut]:
    suggestions_out: list[SuggestionOut] = []
    for s in sorted(fte_suggestions + vendor_suggestions, key=lambda x: x.start):
        unit_cost = avg_salary if s.type == "FTE" else vendor_rate
        prefill = {
            "type": s.type,
            "role_title": "",
            "grade": None,
            "quantity": s.quantity,
            "target_start_date": s.start.isoformat(),
            "source": "FORECAST_SUGGESTION",
        }
        if s.type == "FTE":
            prefill["annual_salary_cents"] = avg_salary or None
        else:
            prefill["hourly_rate_cents"] = vendor_rate or None
            prefill["hours_per_month"] = vendor_hours_per_month
            prefill["vendor_company_id"] = None
        suggestions_out.append(
            SuggestionOut(
                type=s.type,
                quantity=s.quantity,
                start=s.start,
                request_by=s.request_by,
                urgent=s.urgent,
                unit_cost_cents=unit_cost or None,
                request_prefill=prefill,
            )
        )
    return suggestions_out


def compute_what_if(db: Session, team_id: int, today: date, payload: WhatIfRequest) -> WhatIfOut:
    fy_start_month = settings_service.get_int(db, "fy_start_month", 1)
    base_attrition = settings_service.get_float(db, "attrition_pct_monthly", 0.0)
    attrition = payload.attrition_pct_override if payload.attrition_pct_override is not None else base_attrition
    fte_lead_days = settings_service.get_int(db, "fte_lead_days", 45)
    vendor_lead_days = settings_service.get_int(db, "vendor_lead_days", 14)
    vendor_hours_per_month = settings_service.get_int(db, "vendor_hours_per_month", 160)

    future_months = _future_months(today, fy_start_month)
    current_month = date(today.year, today.month, 1)
    extra_hires_start = payload.extra_hires_start_month or (future_months[0] if future_months else current_month)

    workers_today = db.query(Worker).filter(Worker.team_id == team_id).all()
    actual_fte_hc_today = sum(1 for w in workers_today if is_active_on(w.hire_date, w.termination_date, today))
    avg_salary = _avg_fte_annual_salary_cents(db, team_id, today)
    vendor_rate = _latest_vendor_hourly_rate_cents(db, team_id)
    open_positions = _team_open_approved_fte_positions(db, team_id)
    vendor_engagements = _team_vendor_engagements(db, team_id, {EngagementStatus.DECLINED, EngagementStatus.CANCELLED})

    extra_unit_cost = payload.extra_hires_unit_cost_cents
    if extra_unit_cost is None:
        extra_unit_cost = avg_salary if payload.extra_hires_type == "FTE" else vendor_rate

    plan_by_month = {
        row.month_start: row
        for row in db.query(PlanLine).filter(PlanLine.team_id == team_id, PlanLine.month_start.in_(future_months)).all()
    }

    months_out: list[WhatIfMonthPoint] = []
    fte_gaps: list[MonthGap] = []
    vendor_gaps: list[MonthGap] = []
    per_month: dict[date, dict] = {}

    for m in future_months:
        k = months_between(current_month, m)
        L = month_end(m)
        roster_hc_at_L = sum(1 for w in workers_today if is_active_on(w.hire_date, w.termination_date, L))

        baseline_open_count = sum(1 for _p, req in open_positions if req.target_start_date <= L)
        baseline_fte = calc_projected_fte_hc(roster_hc_at_L, actual_fte_hc_today, base_attrition, k, baseline_open_count)
        baseline_vendor = sum(e.headcount for e in vendor_engagements if is_active_on(e.start_date, e.end_date, L))
        baseline_cost = _fte_no_action_cost_cents(
            workers_today, open_positions, m, L, actual_fte_hc_today, base_attrition, k, avg_salary
        ) + _vendor_no_action_cost_cents(vendor_engagements, m)

        # Hiring delay: a position whose target start would land it by month m
        # under the normal timeline now only counts once we reach a month
        # `hiring_delay_months` later — modeled as a whole-month shift of the
        # comparison boundary, not an approximate day count.
        delay_cutoff = month_end(add_months(m, -payload.hiring_delay_months)) if payload.hiring_delay_months else L
        whatif_open_count = sum(1 for _p, req in open_positions if req.target_start_date <= delay_cutoff)
        # Hiring freeze: no open-position contribution from the freeze month on.
        frozen = payload.hiring_freeze_from_month is not None and m >= payload.hiring_freeze_from_month
        if frozen:
            whatif_open_count = 0
        elif payload.hiring_pct_adjustment:
            # Scale the approved open-position pipeline for an explicit
            # scenario. Positive values model additional equivalent hires;
            # negative values model fewer of the approved hires landing.
            whatif_open_count = max(
                0,
                round(whatif_open_count * (1 + payload.hiring_pct_adjustment / 100)),
            )

        whatif_fte = calc_projected_fte_hc(roster_hc_at_L, actual_fte_hc_today, attrition, k, whatif_open_count)
        whatif_vendor = baseline_vendor

        whatif_cost = _fte_no_action_cost_cents(
            workers_today,
            [] if frozen else open_positions,
            m,
            L,
            actual_fte_hc_today,
            attrition,
            k,
            avg_salary,
            position_target_cutoff=delay_cutoff,
        ) + _vendor_no_action_cost_cents(vendor_engagements, m)
        delayed_open_count = sum(1 for _p, req in open_positions if req.target_start_date <= delay_cutoff)
        pipeline_hc_delta = whatif_open_count - (0 if frozen else delayed_open_count)
        if pipeline_hc_delta and avg_salary:
            whatif_cost = max(
                0,
                whatif_cost + fte_monthly_cost_for_hc(pipeline_hc_delta, avg_salary),
            )

        if m >= extra_hires_start and payload.extra_hires > 0:
            if payload.extra_hires_type == "VENDOR":
                whatif_vendor += payload.extra_hires
                whatif_cost += vendor_monthly_cost_for_hc(payload.extra_hires, extra_unit_cost, vendor_hours_per_month)
            else:
                whatif_fte += payload.extra_hires
                whatif_cost += fte_monthly_cost_for_hc(payload.extra_hires, extra_unit_cost)

        per_month[m] = {
            "baseline_fte": baseline_fte,
            "whatif_fte": whatif_fte,
            "baseline_vendor": baseline_vendor,
            "whatif_vendor": whatif_vendor,
            "baseline_cost": baseline_cost,
            "whatif_cost": whatif_cost,
        }

        plan_line = plan_by_month.get(m)
        plan_fte_hc = plan_line.planned_fte_hc if plan_line else 0
        plan_vendor_hc = plan_line.planned_vendor_hc if plan_line else 0
        fte_gaps.append(MonthGap(m, month_gap(plan_fte_hc, whatif_fte)))
        vendor_gaps.append(MonthGap(m, month_gap(plan_vendor_hc, whatif_vendor)))

        months_out.append(
            WhatIfMonthPoint(
                month_start=m,
                baseline_fte_hc=baseline_fte,
                whatif_fte_hc=whatif_fte,
                baseline_vendor_hc=baseline_vendor,
                whatif_vendor_hc=whatif_vendor,
                baseline_cost_cents=baseline_cost,
                whatif_cost_cents=whatif_cost,
                delta_hc=(whatif_fte + whatif_vendor) - (baseline_fte + baseline_vendor),
                delta_cost_cents=whatif_cost - baseline_cost,
            )
        )

    # Suggestions recomputed against the scenario's own gaps, so a delay,
    # freeze, or attrition change visibly shifts what (and when) needs to be
    # requested — not just the headcount/cost lines.
    whatif_fte_suggestions = compute_suggestions("FTE", fte_gaps, fte_lead_days, today)
    whatif_vendor_suggestions = compute_suggestions("VENDOR", vendor_gaps, vendor_lead_days, today)
    suggestions_out = _suggestions_to_out(
        whatif_fte_suggestions, whatif_vendor_suggestions, avg_salary, vendor_rate, vendor_hours_per_month
    )

    return WhatIfOut(team_id=team_id, months=months_out, suggestions=suggestions_out)
