"""Settings are the only place configurable values live (Section 2 rule:
"anything configurable lives in the setting table, never hardcoded")."""
from sqlalchemy.orm import Session

from app.models import Setting

DEFAULT_SETTINGS: dict[str, str | None] = {
    "currency": "USD",
    "fy_start_month": "1",
    "vendor_hours_per_month": "160",
    "attrition_pct_monthly": "0",
    "fte_lead_days": "45",
    "vendor_lead_days": "14",
    "demo_today": None,
}


def ensure_defaults(db: Session) -> None:
    """Insert any missing setting keys with their documented defaults. Never
    overwrites a value that's already present."""
    existing = {row.key for row in db.query(Setting).all()}
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            db.add(Setting(key=key, value=value))
    db.commit()


def get_all(db: Session) -> dict[str, str | None]:
    ensure_defaults(db)
    return {row.key: row.value for row in db.query(Setting).all()}


def get_value(db: Session, key: str) -> str | None:
    row = db.get(Setting, key)
    if row is not None:
        return row.value
    return DEFAULT_SETTINGS.get(key)


def get_int(db: Session, key: str, default: int = 0) -> int:
    value = get_value(db, key)
    return int(value) if value not in (None, "") else default


def get_float(db: Session, key: str, default: float = 0.0) -> float:
    value = get_value(db, key)
    return float(value) if value not in (None, "") else default


def update(db: Session, values: dict[str, str | None]) -> dict[str, str | None]:
    ensure_defaults(db)
    for key, value in values.items():
        row = db.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=value)
            db.add(row)
        else:
            row.value = value
    db.commit()
    return get_all(db)
