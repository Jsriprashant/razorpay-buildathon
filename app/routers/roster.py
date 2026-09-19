from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, require_manager_or_hr, resolve_team_id
from app.models import AppUser
from app.schemas.roster import PositionMatchOut, WorkerCreate, WorkerExitRequest, WorkerOut, WorkerUpdate
from app.services import roster_service
from app.services.clock import get_today

router = APIRouter(prefix="/roster", tags=["roster"])


@router.get("", response_model=list[WorkerOut])
def get_roster(
    month: date | None = Query(default=None, description="Any day in the target month; defaults to today"),
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    today = get_today(db)
    scoped_team_id = resolve_team_id(db, user, team_id)
    target_month = month or today
    return roster_service.get_roster(db, scoped_team_id, target_month, today)


@router.get("/workers/propose-match", response_model=list[PositionMatchOut])
def propose_match(
    job_title: str,
    grade: str | None = None,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return roster_service.propose_position_matches(db, scoped_team_id, job_title, grade)


@router.post("/workers", response_model=WorkerOut)
def add_worker(
    payload: WorkerCreate,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return roster_service.add_worker(db, scoped_team_id, payload, user)


@router.patch("/workers/{worker_id}", response_model=WorkerOut)
def update_worker(
    worker_id: int,
    payload: WorkerUpdate,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    today = get_today(db)
    return roster_service.update_worker(db, worker_id, scoped_team_id, payload, user, today)


@router.post("/workers/{worker_id}/exit", response_model=WorkerOut)
def record_exit(
    worker_id: int,
    payload: WorkerExitRequest,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return roster_service.record_exit(db, worker_id, scoped_team_id, payload, user)
