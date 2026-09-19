from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_hr
from app.models import AppUser
from app.schemas.postings import ApplicationOut, ApplicationStatusUpdate, HireRequest
from app.services import application_service

router = APIRouter(prefix="/hr/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    team_id: int | None = Query(default=None),
    posting_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return application_service.list_applications(db, team_id, posting_id, q)


@router.post("/{application_id}/status", response_model=ApplicationOut)
def update_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return application_service.update_status(db, application_id, payload.status, user.id)


@router.post("/{application_id}/hire", response_model=ApplicationOut)
def hire(
    application_id: int,
    payload: HireRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return application_service.hire_applicant(db, application_id, payload, user.id)
