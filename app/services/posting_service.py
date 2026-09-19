"""Job posting management (HR) and the public careers site (unauthenticated).
Public responses never expose salary, cost, or internal IDs — only slug,
title, description, location, openings and published_at.
"""
from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Application, ApplicationStatus, JobPosting, Position, PositionStatus, PostingStatus, Role
from app.schemas.postings import ApplyRequest, JobPostingOut, PublicPostingDetail, PublicPostingListItem
from app.services.audit_service import write_audit
from app.services.notification_service import notify_role
from app.services.rate_limit import is_rate_limited

_TAG_RE = re.compile(r"<[^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(value: str | None) -> str | None:
    """Strip HTML-ish tags and control characters from free-text applicant
    input before it is stored or rendered anywhere (defense in depth; React
    already escapes text content, but the note is also read by HR tooling)."""
    if value is None:
        return None
    return _CONTROL_RE.sub("", _TAG_RE.sub("", value)).strip()


def _posting_out(db: Session, posting: JobPosting) -> JobPostingOut:
    applicant_count = db.query(Application.id).filter(Application.posting_id == posting.id).count()
    open_position_count = (
        db.query(Position.id)
        .filter(Position.request_id == posting.request_id, Position.status == PositionStatus.OPEN)
        .count()
    )
    return JobPostingOut(
        id=posting.id,
        request_id=posting.request_id,
        slug=posting.slug,
        title=posting.title,
        description=posting.description,
        location=posting.location,
        openings=posting.openings,
        status=posting.status,
        published_at=posting.published_at,
        applicant_count=applicant_count,
        open_position_count=open_position_count,
    )


def list_postings(
    db: Session, team_id: int | None, status_filter: PostingStatus | None, q: str | None = None
) -> list[JobPostingOut]:
    from app.models import HiringRequest

    query = db.query(JobPosting)
    if team_id is not None:
        query = query.join(HiringRequest, HiringRequest.id == JobPosting.request_id).filter(
            HiringRequest.team_id == team_id
        )
    if status_filter is not None:
        query = query.filter(JobPosting.status == status_filter)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(JobPosting.title.ilike(like) | JobPosting.location.ilike(like))
    postings = query.order_by(JobPosting.published_at.desc()).all()
    return [_posting_out(db, p) for p in postings]


def update_posting_status(db: Session, posting_id: int, new_status: PostingStatus, actor_id: int) -> JobPostingOut:
    posting = db.get(JobPosting, posting_id)
    if posting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posting not found")
    if posting.status == PostingStatus.CLOSED and new_status != PostingStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot reopen a closed posting")
    posting.status = new_status
    write_audit(db, actor_id, "job_posting", posting.id, f"SET_{new_status.value}")
    db.commit()
    db.refresh(posting)
    return _posting_out(db, posting)


def list_public_postings(db: Session, q: str | None) -> list[PublicPostingListItem]:
    query = db.query(JobPosting).filter(JobPosting.status == PostingStatus.PUBLISHED)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(JobPosting.title.ilike(like) | JobPosting.location.ilike(like))
    postings = query.order_by(JobPosting.published_at.desc()).all()
    return [
        PublicPostingListItem(
            slug=p.slug, title=p.title, location=p.location, openings=p.openings, published_at=p.published_at
        )
        for p in postings
    ]


def get_public_posting(db: Session, slug: str) -> PublicPostingDetail:
    posting = db.query(JobPosting).filter(JobPosting.slug == slug, JobPosting.status == PostingStatus.PUBLISHED).first()
    if posting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posting not found")
    return PublicPostingDetail(
        slug=posting.slug,
        title=posting.title,
        description=posting.description,
        location=posting.location,
        openings=posting.openings,
        published_at=posting.published_at,
    )


def apply_to_posting(db: Session, slug: str, payload: ApplyRequest, client_ip: str) -> None:
    if is_rate_limited(f"apply:{client_ip}"):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many applications, please try again later")

    posting = db.query(JobPosting).filter(JobPosting.slug == slug, JobPosting.status == PostingStatus.PUBLISHED).first()
    if posting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posting not found")

    if payload.website.strip():
        # Honeypot tripped — pretend success without writing anything.
        return

    existing = (
        db.query(Application.id)
        .filter(Application.posting_id == posting.id, Application.email == payload.email)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already applied to this posting")

    from datetime import datetime

    application = Application(
        posting_id=posting.id,
        name=sanitize_text(payload.name) or payload.name,
        email=payload.email,
        phone=sanitize_text(payload.phone),
        profile_url=sanitize_text(payload.profile_url),
        note=sanitize_text(payload.note),
        status=ApplicationStatus.NEW,
        created_at=datetime.utcnow(),
    )
    db.add(application)
    db.flush()
    write_audit(db, None, "application", application.id, "CREATE", detail=f"Applied to {posting.slug}")
    notify_role(db, Role.HR, f"New application for {posting.title}", link="/hr/applications")
    db.commit()
