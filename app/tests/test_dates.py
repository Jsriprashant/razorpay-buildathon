from datetime import date

from app.calc.dates import (
    active_days_in_month,
    add_months,
    days_in_month,
    fiscal_year_months,
    is_active_on,
    month_end,
    month_start,
    months_between,
)


def test_days_in_month():
    assert days_in_month(2024, 2) == 29  # leap year
    assert days_in_month(2023, 2) == 28
    assert days_in_month(2024, 4) == 30


def test_month_start_end():
    d = date(2026, 3, 17)
    assert month_start(d) == date(2026, 3, 1)
    assert month_end(d) == date(2026, 3, 31)


def test_add_months_wraps_year():
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 1)
    assert add_months(date(2026, 3, 1), -5) == date(2025, 10, 1)


def test_months_between():
    assert months_between(date(2026, 1, 1), date(2026, 4, 1)) == 3
    assert months_between(date(2026, 4, 1), date(2026, 1, 1)) == -3


def test_is_active_on():
    assert is_active_on(date(2026, 1, 1), None, date(2026, 6, 1)) is True
    assert is_active_on(date(2026, 7, 1), None, date(2026, 6, 1)) is False
    # termination_date is the LAST working day (inclusive)
    assert is_active_on(date(2026, 1, 1), date(2026, 6, 1), date(2026, 6, 1)) is True
    assert is_active_on(date(2026, 1, 1), date(2026, 6, 1), date(2026, 6, 2)) is False


def test_active_days_in_month_full_month():
    assert active_days_in_month(date(2026, 1, 1), None, date(2026, 6, 15)) == 30


def test_active_days_in_month_partial_start():
    # started the 16th of a 30-day month => 15 active days (matches the
    # money golden test's premise)
    assert active_days_in_month(date(2026, 4, 16), None, date(2026, 4, 1)) == 15


def test_active_days_in_month_no_overlap():
    assert active_days_in_month(date(2026, 8, 1), None, date(2026, 6, 1)) == 0
    assert active_days_in_month(date(2026, 1, 1), date(2026, 5, 31), date(2026, 6, 1)) == 0


def test_fiscal_year_months_jan_start():
    months = fiscal_year_months(date(2026, 9, 19), fy_start_month=1)
    assert months[0] == date(2026, 1, 1)
    assert months[-1] == date(2026, 12, 1)
    assert len(months) == 12


def test_fiscal_year_months_mid_year_start():
    months = fiscal_year_months(date(2026, 3, 1), fy_start_month=7)
    assert months[0] == date(2025, 7, 1)
    assert months[-1] == date(2026, 6, 1)
