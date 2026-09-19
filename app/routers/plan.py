from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, require_manager_or_hr, resolve_team_id
from app.models import AppUser
from app.schemas.plan import PlanOut, PlanUpdateRequest
from app.services import plan_service, settings_service
from app.services.clock import get_today

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("", response_model=PlanOut)
def get_plan(
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    today = get_today(db)
    scoped_team_id = resolve_team_id(db, user, team_id)
    fy_start_month = settings_service.get_int(db, "fy_start_month", 1)
    return plan_service.get_plan(db, scoped_team_id, today, fy_start_month)


@router.put("", response_model=PlanOut)
def update_plan(
    payload: PlanUpdateRequest,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return plan_service.upsert_plan(db, scoped_team_id, payload.lines)
