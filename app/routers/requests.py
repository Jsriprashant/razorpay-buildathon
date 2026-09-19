from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, require_manager_or_hr, resolve_team_id
from app.models import AppUser, RequestStatus, RequestType
from app.schemas.requests import HiringRequestCreate, HiringRequestUpdate, RequestDetailOut
from app.services import request_service

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=list[RequestDetailOut])
def list_requests(
    team_id: int | None = Query(default=None),
    status_filter: RequestStatus | None = Query(default=None, alias="status"),
    type_filter: RequestType | None = Query(default=None, alias="type"),
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return request_service.list_requests(db, scoped_team_id, status_filter, type_filter, q, sort)


@router.post("", response_model=RequestDetailOut)
def create_request(
    payload: HiringRequestCreate,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return request_service.create_request(db, scoped_team_id, payload, user)


@router.get("/{request_id}", response_model=RequestDetailOut)
def get_request(
    request_id: int,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return request_service.get_request(db, scoped_team_id, request_id)


@router.patch("/{request_id}", response_model=RequestDetailOut)
def update_request(
    request_id: int,
    payload: HiringRequestUpdate,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return request_service.update_request(db, scoped_team_id, request_id, payload, user)


@router.post("/{request_id}/submit", response_model=RequestDetailOut)
def submit_request(
    request_id: int,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return request_service.submit_request(db, scoped_team_id, request_id, user)


@router.post("/{request_id}/resubmit", response_model=RequestDetailOut)
def resubmit_request(
    request_id: int,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return request_service.resubmit_request(db, scoped_team_id, request_id, user)


@router.post("/{request_id}/cancel", response_model=RequestDetailOut)
def cancel_request(
    request_id: int,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    return request_service.cancel_request(db, scoped_team_id, request_id, user)
