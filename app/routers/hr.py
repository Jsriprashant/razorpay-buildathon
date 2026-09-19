from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_hr
from app.models import AppUser, RequestType
from app.schemas.requests import BulkApproveRequest, DecisionRequest, HiringRequestOut
from app.services import hr_service

router = APIRouter(prefix="/hr", tags=["hr"])


@router.get("/inbox", response_model=list[HiringRequestOut])
def get_inbox(
    team_id: int | None = Query(default=None),
    type_filter: RequestType | None = Query(default=None, alias="type"),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return hr_service.list_inbox(db, team_id, type_filter, q)


@router.post("/requests/{request_id}/approve", response_model=HiringRequestOut)
def approve(
    request_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return hr_service.approve_request(db, request_id, user, payload.note)


@router.post("/requests/{request_id}/reject", response_model=HiringRequestOut)
def reject(
    request_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return hr_service.reject_request(db, request_id, user, payload.note)


@router.post("/requests/{request_id}/request-changes", response_model=HiringRequestOut)
def request_changes(
    request_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return hr_service.request_changes(db, request_id, user, payload.note)


@router.post("/requests/{request_id}/cancel", response_model=HiringRequestOut)
def cancel_approved(
    request_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return hr_service.cancel_approved_request(db, request_id, user, payload.note)


@router.post("/requests/bulk-approve")
def bulk_approve(
    payload: BulkApproveRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return hr_service.bulk_approve(db, payload.request_ids, user)
