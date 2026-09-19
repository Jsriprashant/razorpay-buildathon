"""Demo Panel endpoints: advance the simulated clock, or wipe + reseed. Open
to every role -- see app/services/demo_service.py."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.deps import current_user, get_db
from app.models import AppUser
from app.schemas.settings import SettingsOut
from app.services import demo_service, settings_service

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/advance-month", response_model=SettingsOut)
def advance_month(db: Session = Depends(get_db), user: AppUser = Depends(current_user)):
    return settings_service.to_settings_out(demo_service.advance_month(db))


@router.post("/reset", response_model=SettingsOut)
def reset(db: Session = Depends(get_db), user: AppUser = Depends(current_user)):
    # Release this request's own session (and the lock its earlier SELECTs
    # hold) before drop_all/create_all needs an exclusive lock on every table.
    db.close()
    demo_service.reset_demo_data()
    fresh_db = SessionLocal()
    try:
        return settings_service.to_settings_out(settings_service.get_all(fresh_db))
    finally:
        fresh_db.close()
