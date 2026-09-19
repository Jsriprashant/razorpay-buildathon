"""Golden tests for app/calc/forecast.py, per the foundation task's spec:

1. Incremental suggestions across months (cumulative-need algorithm only
   suggests the *new* gap once it exceeds what's already been suggested).
2. A future termination lowers projected FTE headcount for the month it
   takes effect and every month after.
3. An OPEN position on an APPROVED FTE request with a future target_start
   raises projected FTE headcount for months on/after that start (it isn't
   in the roster yet, so it wouldn't otherwise show up).
"""
from datetime import date

from app.calc.dates import is_active_on, month_end
from app.calc.forecast import MonthGap, attrition_loss_hc, compute_suggestions, month_gap, projected_fte_hc


def test_incremental_suggestions_across_months():
    # Plan grows to 2 in month 1 and stays at 2 through month 4; the gap
    # should be fully suggested by month 1 (qty 2), with no further
    # suggestions needed until the plan grows again in month 3.
    months = [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]
    projected = {months[0]: 0, months[1]: 1, months[2]: 1, months[3]: 1}
    plan = {months[0]: 1, months[1]: 1, months[2]: 3, months[3]: 3}

    gaps = [MonthGap(m, month_gap(plan[m], projected[m])) for m in months]
    suggestions = compute_suggestions("FTE", gaps, lead_days=45, today=date(2025, 10, 1))

    # Month 1: gap=1 -> suggest 1 (cum=1).
    # Month 2: gap=0 -> nothing.
    # Month 3: gap=2, cum=1 -> suggest only the *new* 1 (cum=2).
    # Month 4: gap=2, cum=2 -> nothing (already covered).
    assert [(s.start, s.quantity) for s in suggestions] == [
        (months[0], 1),
        (months[2], 1),
    ]
    assert suggestions[0].request_by == date(2025, 11, 17)  # Jan 1 - 45 days
    assert suggestions[0].urgent is False


def test_suggestion_request_by_in_past_is_urgent():
    months = [date(2026, 1, 1)]
    gaps = [MonthGap(months[0], 1)]
    # today is well after request_by (Jan 1 - 45 days), so it's overdue.
    suggestions = compute_suggestions("FTE", gaps, lead_days=45, today=date(2026, 1, 1))
    assert suggestions[0].urgent is True


def test_future_termination_lowers_projected_hc():
    today = date(2026, 9, 19)
    # Two workers active today; one is terminated at the end of next month.
    workers = [
        (date(2020, 1, 1), None),
        (date(2020, 1, 1), date(2026, 10, 31)),
    ]
    next_month_end = month_end(date(2026, 10, 1))
    two_months_end = month_end(date(2026, 11, 1))

    roster_hc_next_month = sum(1 for hire, term in workers if is_active_on(hire, term, next_month_end))
    roster_hc_two_months = sum(1 for hire, term in workers if is_active_on(hire, term, two_months_end))

    # The termination is exactly on next_month_end (inclusive last working
    # day), so the worker is still active *through* month 1 and drops out by
    # month 2.
    assert roster_hc_next_month == 2
    assert roster_hc_two_months == 1

    projected_month_1 = projected_fte_hc(roster_hc_next_month, 2, 0.0, 1, 0)
    projected_month_2 = projected_fte_hc(roster_hc_two_months, 2, 0.0, 2, 0)

    assert projected_month_1 == 2
    assert projected_month_2 == 1  # lower, because of the future termination


def test_open_approved_position_raises_projected_hc():
    today = date(2026, 9, 19)
    # Roster today has 5 active FTEs; an APPROVED request has 1 OPEN
    # position with target_start next month (not yet a worker, so it's
    # absent from roster_hc but must still show up in the projection).
    roster_hc_today = 5
    next_month_end = month_end(date(2026, 10, 1))
    open_positions_with_target_start_le = 1  # target_start (Oct 1) <= next_month_end

    projected_without_position = projected_fte_hc(roster_hc_today, roster_hc_today, 0.0, 1, 0)
    projected_with_position = projected_fte_hc(
        roster_hc_today, roster_hc_today, 0.0, 1, open_positions_with_target_start_le
    )

    assert projected_without_position == 5
    assert projected_with_position == 6  # raised by the pending open position


def test_attrition_loss_hc_rounds_half_up_and_scales_with_months_ahead():
    # 24 heads * 2%/month * 1 month = 0.48 -> rounds down to 0.
    assert attrition_loss_hc(24, 0.02, 1) == 0
    # 24 heads * 2%/month * 2 months = 0.96 -> rounds up to 1.
    assert attrition_loss_hc(24, 0.02, 2) == 1
    # Exactly on the .5 boundary rounds up (ROUND_HALF_UP, not banker's).
    assert attrition_loss_hc(20, 0.025, 1) == 1
    # No attrition configured -> no loss regardless of months ahead.
    assert attrition_loss_hc(50, 0.0, 12) == 0


def test_attrition_loss_hc_matches_projected_fte_hc_reduction():
    # projected_fte_hc's internal attrition math must stay in lockstep with
    # the standalone helper the no-action cost curve now shares.
    roster_hc = 30
    actual_today = 28
    pct = 0.03
    months_ahead = 3
    loss = attrition_loss_hc(actual_today, pct, months_ahead)
    assert projected_fte_hc(roster_hc, actual_today, pct, months_ahead, 0) == roster_hc - loss
