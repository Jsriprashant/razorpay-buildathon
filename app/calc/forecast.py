"""Pure forecast math (Section on Forecast in the spec). No DB access.

All money math routes through app/calc/money.py; all date math routes
through app/calc/dates.py. This module only combines already-computed
headcount/date inputs into projected headcount, gaps, suggestions and
scenario costs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from fractions import Fraction

from app.calc.money import round_half_up


def attrition_loss_hc(actual_fte_hc_today: int, attrition_pct_monthly: float, months_ahead: int) -> int:
    """round_half_up(actual_fte_hc_today * attrition_pct_monthly * k). Shared
    by the headcount projection and the no-action cost curve so the two never
    disagree on how many heads attrition is expected to remove."""
    return round_half_up(
        Fraction(actual_fte_hc_today) * Fraction(attrition_pct_monthly).limit_denominator(1_000_000) * months_ahead
    )


def projected_fte_hc(
    roster_hc_at_month_end: int,
    actual_fte_hc_today: int,
    attrition_pct_monthly: float,
    months_ahead: int,
    open_approved_positions_count: int,
) -> int:
    """projected_fte_hc[m] = roster_hc(L) - round_half_up(actual_fte_hc_today *
    attrition_pct_monthly * k) + count of OPEN positions of APPROVED FTE
    requests with target_start <= L.

    `attrition_pct_monthly` is a fraction (e.g. 0.02 for 2%/month), applied
    once per month-ahead (k), not compounded.
    """
    attrition_loss = attrition_loss_hc(actual_fte_hc_today, attrition_pct_monthly, months_ahead)
    return roster_hc_at_month_end - attrition_loss + open_approved_positions_count


def projected_vendor_hc(active_non_declined_cancelled_headcount: int) -> int:
    """projected_vendor_hc[m] = sum of headcount of non-DECLINED/CANCELLED
    engagements active on L. The caller does the "active on L" + status
    filtering against vendor_engagement rows; this function is a pass-through
    kept for symmetry/testability with projected_fte_hc."""
    return active_non_declined_cancelled_headcount


def month_gap(plan_hc: int, projected_hc: int) -> int:
    """gap[m] = plan_hc[m] - projected_hc[m]."""
    return plan_hc - projected_hc


@dataclass(frozen=True)
class MonthGap:
    month_start: date
    gap: int


@dataclass(frozen=True)
class Suggestion:
    type: str  # "FTE" or "VENDOR"
    month_start: date
    quantity: int
    start: date
    request_by: date
    urgent: bool


def compute_suggestions(
    type_: str,
    month_gaps: list[MonthGap],
    lead_days: int,
    today: date,
) -> list[Suggestion]:
    """Cumulative-need suggestion algorithm, iterating months in order:

        cum = 0
        for each month m (in order):
            need = max(0, gap[m])
            new = max(0, need - cum)
            cum += new
            if new > 0: suggest {type, quantity: new, start: month m,
                                  request_by: start - lead_days(type)}

    request_by < today => URGENT.
    """
    suggestions: list[Suggestion] = []
    cum = 0
    for mg in sorted(month_gaps, key=lambda x: x.month_start):
        need = max(0, mg.gap)
        new = max(0, need - cum)
        cum += new
        if new > 0:
            request_by = mg.month_start - timedelta(days=lead_days)
            suggestions.append(
                Suggestion(
                    type=type_,
                    month_start=mg.month_start,
                    quantity=new,
                    start=mg.month_start,
                    request_by=request_by,
                    urgent=request_by < today,
                )
            )
    return suggestions


def cumulative_suggested_hc_by_month(suggestions: list[Suggestion], months: list[date]) -> dict[date, int]:
    """Running total of suggested quantity that has taken effect by each
    month in `months` (a suggestion with start <= m contributes to m)."""
    result: dict[date, int] = {}
    running = 0
    sorted_months = sorted(months)
    for m in sorted_months:
        running += sum(s.quantity for s in suggestions if s.start == m)
        result[m] = running
    return result


def fte_monthly_cost_for_hc(hc: int, avg_annual_salary_cents: int) -> int:
    """A full month's FTE cost for `hc` headcount at the team's average
    current annual salary — used for forward-looking scenario cost curves
    (not actuals, which use fte_month_cost_cents with real proration)."""
    if hc <= 0:
        return 0
    return round_half_up(Fraction(avg_annual_salary_cents, 12) * hc)


def vendor_monthly_cost_for_hc(hc: int, hourly_rate_cents: int, hours_per_month: int) -> int:
    """A full month's vendor cost for `hc` headcount at the given rate."""
    if hc <= 0:
        return 0
    return hc * hourly_rate_cents * hours_per_month
