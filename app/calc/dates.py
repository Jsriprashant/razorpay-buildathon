"""Pure date/proration helpers (no DB access). See app/services/clock.py for
the stateful get_today() that reads the demo_today setting.
"""
import calendar
from datetime import date


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def month_end(d: date) -> date:
    return date(d.year, d.month, days_in_month(d.year, d.month))


def add_months(d: date, months: int) -> date:
    """Shift a date by `months`, clamped to the 1st of the resulting month
    (callers that need month_start/month_end should re-derive from the
    returned year/month rather than relying on day-of-month semantics)."""
    total = (d.year * 12 + (d.month - 1)) + months
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, 1)


def months_between(start_month: date, end_month: date) -> int:
    """Number of month steps between two month_start dates (end - start)."""
    return (end_month.year - start_month.year) * 12 + (end_month.month - start_month.month)


def is_active_on(hire_date: date, termination_date: date | None, d: date) -> bool:
    """A worker/engagement is ACTIVE on date d if it started on/before d and
    (no end date, or the end date is on/after d). termination_date is the
    LAST working day (inclusive)."""
    if hire_date > d:
        return False
    if termination_date is not None and termination_date < d:
        return False
    return True


def active_days_in_month(start_date: date, end_date: date | None, month: date) -> int:
    """Active days within the calendar month containing `month`, for an item
    active from start_date to end_date inclusive (end_date=None => open-ended).
    Returns 0 if there's no overlap.
    """
    m_start = month_start(month)
    m_end = month_end(month)
    overlap_start = max(m_start, start_date)
    overlap_end = min(m_end, end_date) if end_date is not None else m_end
    if overlap_start > overlap_end:
        return 0
    return (overlap_end - overlap_start).days + 1


def fiscal_year_months(today: date, fy_start_month: int) -> list[date]:
    """The 12 month_start dates of the fiscal year (containing `today`) that
    starts on fy_start_month."""
    if today.month >= fy_start_month:
        fy_start_year = today.year
    else:
        fy_start_year = today.year - 1
    start = date(fy_start_year, fy_start_month, 1)
    return [add_months(start, i) for i in range(12)]
