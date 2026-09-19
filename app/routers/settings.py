from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, require_hr
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_out(values: dict[str, str | None]) -> SettingsOut:
    return SettingsOut(
        currency=values.get("currency") or "USD",
        fy_start_month=int(values.get("fy_start_month") or 1),
        vendor_hours_per_month=int(values.get("vendor_hours_per_month") or 160),
        attrition_pct_monthly=float(values.get("attrition_pct_monthly") or 0),
        fte_lead_days=int(values.get("fte_lead_days") or 45),
        vendor_lead_days=int(values.get("vendor_lead_days") or 14),
        demo_today=values.get("demo_today"),
    )


@router.get("", response_model=SettingsOut, dependencies=[Depends(current_user)])
def get_settings(db: Session = Depends(get_db)):
    """Readable by any logged-in role — the manager UI needs currency, lead
    times, etc. Only HR may change them (enforced on PUT)."""
    return _to_out(settings_service.get_all(db))


@router.put("", response_model=SettingsOut, dependencies=[Depends(require_hr)])
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    updates = {k: (str(v) if v is not None else None) for k, v in payload.model_dump(exclude_unset=True).items()}
    return _to_out(settings_service.update(db, updates))
