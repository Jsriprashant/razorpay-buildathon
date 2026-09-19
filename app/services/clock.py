"""The only place allowed to fall back to the real wall-clock date.

get_today() is what every router/service must call instead of date.today():
it returns the `demo_today` setting when one is set, otherwise the real date.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.models import Setting


def get_today(db: Session) -> date:
    row = db.get(Setting, "demo_today")
    if row is not None and row.value:
        return date.fromisoformat(row.value)
    return date.today()
