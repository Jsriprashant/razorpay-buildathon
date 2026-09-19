from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db, require_hr
from app.models import AppUser, PostingStatus
from app.schemas.postings import ApplyRequest, JobPostingOut, JobPostingUpdate, PublicPostingDetail, PublicPostingListItem
from app.services import posting_service

router = APIRouter(tags=["postings"])


@router.get("/hr/postings", response_model=list[JobPostingOut])
def list_postings(
    team_id: int | None = Query(default=None),
    status_filter: PostingStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return posting_service.list_postings(db, team_id, status_filter, q)


@router.patch("/hr/postings/{posting_id}", response_model=JobPostingOut)
def update_posting(
    posting_id: int,
    payload: JobPostingUpdate,
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_hr),
):
    return posting_service.update_posting_status(db, posting_id, payload.status, user.id)


@router.get("/public/postings", response_model=list[PublicPostingListItem])
def list_public_postings(q: str | None = Query(default=None), db: Session = Depends(get_db)):
    return posting_service.list_public_postings(db, q)


@router.get("/public/postings/{slug}", response_model=PublicPostingDetail)
def get_public_posting(slug: str, db: Session = Depends(get_db)):
    return posting_service.get_public_posting(db, slug)


@router.post("/public/postings/{slug}/apply", status_code=204)
def apply(slug: str, payload: ApplyRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    posting_service.apply_to_posting(db, slug, payload, client_ip)
    return None
