"""Demo-mode controls (Demo Panel): advancing the simulated clock and
resetting all data back to the seed baseline. Available to every role —
there's no real production data in this app to protect from a demo action.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.calc.dates import add_months, month_start
from app.services import settings_service
from app.services.clock import get_today


def advance_month(db: Session) -> dict[str, str | None]:
    """Jumps the demo clock to the 1st of the month after the current one.
    Does not roll cycles over itself — the next page load's /cycles/current
    check (or an explicit rollover call) does that, same as a real month
    boundary passing."""
    today = get_today(db)
    next_month = add_months(month_start(today), 1)
    return settings_service.update(db, {"demo_today": next_month.isoformat()})


def reset_demo_data() -> None:
    """Drops and recreates every table, then reseeds — the same script the
    workflow runs on first boot. Callers must ensure their own DB session is
    closed before calling this (drop_all needs an exclusive lock that an
    idle-in-transaction session on the same tables would block)."""
    from app.scripts.seed_reset import main as seed_reset_main

    seed_reset_main()
