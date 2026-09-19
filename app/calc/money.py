"""The one and only place rounding happens for money.

Rule (Section 2 of the spec): money is always integer cents. Never use float
for money and never use Python's built-in round() (it's banker's rounding —
round-half-to-even — which silently disagrees with the ROUND_HALF_UP the spec
requires). Every other module must route through this file to turn a
fractional-cents quantity into a whole number of cents.

This module has no DB access and no side effects — pure math only.
"""
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction


def round_half_up_cents(amount: Decimal | Fraction | int) -> int:
    """Round a (possibly fractional) cents amount to the nearest whole cent,
    rounding .5 up (away from zero for positive amounts), per spec.
    """
    if isinstance(amount, Fraction):
        amount = Decimal(amount.numerator) / Decimal(amount.denominator)
    elif isinstance(amount, int):
        return amount
    quantized = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(quantized)


# Alias: the same ROUND_HALF_UP helper, used outside a strictly "cents"
# context (e.g. rounding a headcount number in the forecast). Keeping one
# function and two names avoids a second rounding implementation existing
# anywhere in the codebase.
round_half_up = round_half_up_cents


def prorate_cents(total_cents: int, active_days: int, days_in_month: int) -> int:
    """Prorate a whole-period amount (e.g. a full month's cost) down to the
    portion covered by active_days out of days_in_month, rounded once to the
    nearest whole cent (ROUND_HALF_UP).

    Uses exact fraction math (no floats) before the single rounding step.
    """
    if days_in_month <= 0:
        raise ValueError("days_in_month must be positive")
    if active_days < 0 or active_days > days_in_month:
        raise ValueError("active_days must be between 0 and days_in_month")
    fraction = Fraction(total_cents, 1) * Fraction(active_days, days_in_month)
    return round_half_up_cents(fraction)


def fte_month_cost_cents(annual_salary_cents: int, active_days: int, days_in_month: int) -> int:
    """FTE cost(m) = annual_salary_cents / 12 * (active_days / days_in_month),
    rounded once to whole cents (ROUND_HALF_UP). Matches the spec's example:
    annual_salary_cents * active_days / (12 * days_in_month).
    """
    if days_in_month <= 0:
        raise ValueError("days_in_month must be positive")
    if active_days < 0 or active_days > days_in_month:
        raise ValueError("active_days must be between 0 and days_in_month")
    fraction = Fraction(annual_salary_cents * active_days, 12 * days_in_month)
    return round_half_up_cents(fraction)


def vendor_month_cost_cents(
    headcount: int, hourly_rate_cents: int, hours_per_month: int, active_days: int, days_in_month: int
) -> int:
    """Vendor cost(m) = headcount * hourly_rate_cents * hours_per_month * (active_days / days_in_month),
    rounded once to whole cents (ROUND_HALF_UP).
    """
    if days_in_month <= 0:
        raise ValueError("days_in_month must be positive")
    if active_days < 0 or active_days > days_in_month:
        raise ValueError("active_days must be between 0 and days_in_month")
    total = headcount * hourly_rate_cents * hours_per_month
    fraction = Fraction(total * active_days, days_in_month)
    return round_half_up_cents(fraction)


def vendor_contract_value_cents(
    headcount: int,
    hourly_rate_cents: int,
    hours_per_month: int,
    start_date,
    end_date,
) -> int:
    """Total contract value across every calendar month the engagement
    spans: the sum of vendor_month_cost_cents(...) for each month from
    start_date to end_date inclusive, prorated for partial first/last months.
    Used for the live contract-value figure on the vendor request form and
    the vendor engagement detail view.
    """
    from app.calc.dates import active_days_in_month, add_months, days_in_month, month_start

    if end_date < start_date:
        raise ValueError("end_date must be on/after start_date")
    total = 0
    m = month_start(start_date)
    last_month = month_start(end_date)
    while m <= last_month:
        dim = days_in_month(m.year, m.month)
        active_days = active_days_in_month(start_date, end_date, m)
        total += vendor_month_cost_cents(headcount, hourly_rate_cents, hours_per_month, active_days, dim)
        m = add_months(m, 1)
    return total


def format_cents(cents: int, currency: str = "USD") -> str:
    """One shared display formatter for whole-cent integers -> "$1,234.56"."""
    sign = "-" if cents < 0 else ""
    magnitude = abs(cents)
    dollars, remainder = divmod(magnitude, 100)
    symbol = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "INR": "\u20b9"}.get(currency, currency + " ")
    return f"{sign}{symbol}{dollars:,}.{remainder:02d}"
