"""Golden tests for app/calc/money.py, values taken verbatim from Section 4
of the spec."""
from app.calc.money import fte_month_cost_cents, format_cents, round_half_up_cents, vendor_month_cost_cents
from decimal import Decimal


def test_fte_cost_mid_month_start_30_day_month():
    # FTE at 120,000/yr starting the 16th of a 30-day month = 5,000.00
    # active_days = 30 - 16 + 1 = 15
    annual_salary_cents = 120_000 * 100
    active_days = 15
    days_in_month = 30
    assert fte_month_cost_cents(annual_salary_cents, active_days, days_in_month) == 5_000_00


def test_fte_cost_full_month():
    annual_salary_cents = 120_000 * 100
    assert fte_month_cost_cents(annual_salary_cents, 30, 30) == 10_000_00


def test_vendor_cost_full_month_two_vendors():
    # 2 vendors at $50/hr x 160h for the whole month = 16,000.00
    assert vendor_month_cost_cents(2, 50_00, 160, 30, 30) == 16_000_00


def test_vendor_cost_partial_month():
    # active 10 of 30 days = 5,333.33
    assert vendor_month_cost_cents(2, 50_00, 160, 10, 30) == 5_333_33


def test_round_half_up_not_banker_rounding():
    # Python's round() would round 0.5 to 0 (round-half-to-even); we require
    # ROUND_HALF_UP, i.e. 0.5 always rounds away from zero.
    assert round_half_up_cents(Decimal("2.5")) == 3
    assert round_half_up_cents(Decimal("3.5")) == 4
    assert round_half_up_cents(Decimal("0.5")) == 1


def test_format_cents():
    assert format_cents(500_000) == "$5,000.00"
    assert format_cents(533_333) == "$5,333.33"
    assert format_cents(-500) == "-$5.00"
