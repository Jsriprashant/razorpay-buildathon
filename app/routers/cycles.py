from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, require_manager_or_hr, resolve_team_id
from app.models import AppUser
from app.schemas.cycles import CycleCurrentOut, CycleOut, RolloverOut
from app.services import cycle_service
from app.services.clock import get_today

router = APIRouter(prefix="/cycles", tags=["cycles"])


@router.get("/current", response_model=CycleCurrentOut)
def current_cycle(
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    today = get_today(db)
    return cycle_service.get_current_status(db, scoped_team_id, today)


@router.get("", response_model=list[CycleOut])
def history(
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return cycle_service.list_history(db, scoped_team_id)


@router.get("/{cycle_id}", response_model=CycleOut)
def get_cycle(
    cycle_id: int,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return cycle_service.get_cycle(db, scoped_team_id, cycle_id)


@router.post("/rollover", response_model=RolloverOut)
def do_rollover(
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    today = get_today(db)
    return cycle_service.rollover(db, scoped_team_id, user, today)
