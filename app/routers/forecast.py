from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, resolve_team_id
from app.models import AppUser
from app.schemas.forecast import ForecastOut, WhatIfOut, WhatIfRequest
from app.services import forecast_service
from app.services.clock import get_today

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=ForecastOut)
def get_forecast(
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    today = get_today(db)
    scoped_team_id = resolve_team_id(db, user, team_id)
    return forecast_service.compute_forecast(db, scoped_team_id, today)


@router.post("/what-if", response_model=WhatIfOut)
def what_if(
    payload: WhatIfRequest,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    today = get_today(db)
    scoped_team_id = resolve_team_id(db, user, team_id)
    return forecast_service.compute_what_if(db, scoped_team_id, today, payload)
