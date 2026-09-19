from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, require_hr, resolve_team_id
from app.models import AppUser, VendorEngagement
from app.schemas.vendors import (
    DeclineRequest,
    SendMessageRequest,
    VendorCompanyCreate,
    VendorCompanyOut,
    VendorEngagementOut,
)
from app.services import vendor_service
from app.services.clock import get_today

router = APIRouter(tags=["vendors"])


@router.get("/hr/vendor-companies", response_model=list[VendorCompanyOut])
def list_vendor_companies(
    q: str | None = None, db: Session = Depends(get_db), user: AppUser = Depends(current_user)
):
    return vendor_service.list_vendor_companies(db, q)


@router.post("/hr/vendor-companies", response_model=VendorCompanyOut)
def create_vendor_company(
    payload: VendorCompanyCreate, db: Session = Depends(get_db), user: AppUser = Depends(require_hr)
):
    return vendor_service.create_vendor_company(db, payload, user.id)


@router.get("/hr/vendor-dispatch", response_model=list[VendorEngagementOut])
def dispatch_queue(q: str | None = None, db: Session = Depends(get_db), user: AppUser = Depends(require_hr)):
    today = get_today(db)
    return vendor_service.list_dispatch_queue(db, today, q)


@router.get("/hr/engagements/{engagement_id}/default-message")
def default_message(engagement_id: int, db: Session = Depends(get_db), user: AppUser = Depends(require_hr)):
    eng = db.get(VendorEngagement, engagement_id)
    if eng is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    subject, body = vendor_service.default_message(db, eng)
    return {"subject": subject, "body": body}


@router.post("/hr/engagements/{engagement_id}/send", response_model=VendorEngagementOut)
def send_message(
    engagement_id: int,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return vendor_service.send_message(db, engagement_id, payload.subject, payload.body, user.id)


@router.post("/hr/engagements/{engagement_id}/confirm", response_model=VendorEngagementOut)
def confirm(engagement_id: int, db: Session = Depends(get_db), user: AppUser = Depends(require_hr)):
    return vendor_service.confirm_engagement(db, engagement_id, user.id)


@router.post("/hr/engagements/{engagement_id}/decline", response_model=VendorEngagementOut)
def decline(
    engagement_id: int,
    payload: DeclineRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return vendor_service.decline_engagement(db, engagement_id, user.id, payload.note)


@router.get("/vendors", response_model=list[VendorEngagementOut])
def team_vendors(
    team_id: int | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    today = get_today(db)
    return vendor_service.list_team_vendors(db, scoped_team_id, today, q)
