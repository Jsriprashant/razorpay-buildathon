"""HR-only decisions on hiring requests: approve (with FTE/vendor fulfilment
fan-out), reject, request-changes, cancel-an-approved-request, bulk-approve.
Only HR may call any of these (enforced in the router).
"""
from __future__ import annotations

import re
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    AppUser,
    ApprovalAction,
    ApprovalEvent,
    EngagementStatus,
    HiringRequest,
    JobPosting,
    Position,
    PositionStatus,
    PostingStatus,
    RequestStatus,
    RequestType,
    Role,
    Team,
    VendorEngagement,
)
from app.schemas.requests import RequestDetailOut
from app.services.audit_service import write_audit
from app.services.hr_fit import compute_fit
from app.services.notification_service import notify_role, notify_user
from app.services.request_service import to_out as _to_out

DEFAULT_POSTING_LOCATION = "Remote"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "role"


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    n = 2
    while db.query(JobPosting.id).filter(JobPosting.slug == slug).first() is not None:
        slug = f"{base}-{n}"
        n += 1
    return slug


def list_inbox(
    db: Session,
    team_id: int | None,
    type_filter: RequestType | None,
    q: str | None,
) -> list[RequestDetailOut]:
    query = db.query(HiringRequest).filter(HiringRequest.status == RequestStatus.SUBMITTED)
    if team_id is not None:
        query = query.filter(HiringRequest.team_id == team_id)
    if type_filter is not None:
        query = query.filter(HiringRequest.type == type_filter)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(HiringRequest.role_title.ilike(like) | HiringRequest.justification.ilike(like))
    reqs = query.order_by(HiringRequest.submitted_at.asc()).all()
    out = []
    for r in reqs:
        item = _to_out(db, r)
        item.plan_fit, item.budget_fit = compute_fit(db, r)
        out.append(item)
    return out


def _get_submitted(db: Session, request_id: int) -> HiringRequest:
    req = db.get(HiringRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status != RequestStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot decide a request in status {req.status.value}"
        )
    return req


def approve_request(db: Session, request_id: int, actor: AppUser, note: str | None) -> RequestDetailOut:
    req = _get_submitted(db, request_id)
    _do_approve(db, req, actor, note)
    db.commit()
    db.refresh(req)
    return _to_out(db, req)


def _do_approve(db: Session, req: HiringRequest, actor: AppUser, note: str | None) -> None:
    req.status = RequestStatus.APPROVED
    req.decided_by = actor.id
    req.decision_note = note
    req.approved_at = datetime.utcnow()
    db.add(
        ApprovalEvent(request_id=req.id, actor_id=actor.id, action=ApprovalAction.APPROVE, note=note, at=req.approved_at)
    )
    write_audit(db, actor.id, "hiring_request", req.id, "APPROVE", detail=note)
    notify_user(db, req.created_by, f"Your request for {req.role_title} was approved.", link=f"/requests/{req.id}")

    if req.type == RequestType.FTE:
        team = db.get(Team, req.team_id)
        for _ in range(req.quantity):
            db.add(Position(request_id=req.id, status=PositionStatus.OPEN))
        base_slug = _slugify(f"{req.role_title}-{team.name if team else ''}")
        slug = _unique_slug(db, base_slug)
        grade_txt = f" (Grade {req.grade})" if req.grade else ""
        description = (
            f"{team.name if team else 'Our team'} is hiring a {req.role_title}{grade_txt}. "
            f"Join us and help grow the team. We are looking for {req.quantity} "
            f"{'person' if req.quantity == 1 else 'people'} to start around {req.target_start_date.isoformat()}."
        )
        posting = JobPosting(
            request_id=req.id,
            slug=slug,
            title=req.role_title,
            description=description,
            location=DEFAULT_POSTING_LOCATION,
            openings=req.quantity,
            status=PostingStatus.PUBLISHED,
            published_at=datetime.utcnow(),
        )
        db.add(posting)
        db.flush()  # visible to _unique_slug on the next bulk-approve iteration
        write_audit(db, actor.id, "job_posting", req.id, "PUBLISH", detail=f"Published posting for {req.role_title}")
        notify_user(
            db, req.created_by, f"Job posting published for {req.role_title}.", link=f"/careers/{slug}"
        )
    else:
        engagement = VendorEngagement(
            request_id=req.id,
            vendor_company_id=req.vendor_company_id,
            headcount=req.quantity,
            hourly_rate_cents=req.hourly_rate_cents,
            hours_per_month=req.hours_per_month,
            start_date=req.target_start_date,
            end_date=req.end_date,
            status=EngagementStatus.AWAITING_DISPATCH,
        )
        db.add(engagement)
        write_audit(db, actor.id, "vendor_engagement", req.id, "CREATE", detail=f"Engagement created for {req.role_title}")
        notify_role(db, Role.HR, f"New vendor engagement awaiting dispatch: {req.role_title}", link="/hr/vendor-dispatch")


def reject_request(db: Session, request_id: int, actor: AppUser, note: str | None) -> RequestDetailOut:
    req = _get_submitted(db, request_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A note is required to reject a request")
    req.status = RequestStatus.REJECTED
    req.decided_by = actor.id
    req.decision_note = note
    db.add(ApprovalEvent(request_id=req.id, actor_id=actor.id, action=ApprovalAction.REJECT, note=note, at=datetime.utcnow()))
    write_audit(db, actor.id, "hiring_request", req.id, "REJECT", detail=note)
    notify_user(db, req.created_by, f"Your request for {req.role_title} was rejected.", link=f"/requests/{req.id}")
    db.commit()
    db.refresh(req)
    return _to_out(db, req)


def request_changes(db: Session, request_id: int, actor: AppUser, note: str | None) -> RequestDetailOut:
    req = _get_submitted(db, request_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A note is required to request changes")
    req.status = RequestStatus.CHANGES_REQUESTED
    req.decided_by = actor.id
    req.decision_note = note
    db.add(
        ApprovalEvent(
            request_id=req.id, actor_id=actor.id, action=ApprovalAction.REQUEST_CHANGES, note=note, at=datetime.utcnow()
        )
    )
    write_audit(db, actor.id, "hiring_request", req.id, "REQUEST_CHANGES", detail=note)
    notify_user(
        db, req.created_by, f"Changes were requested on your request for {req.role_title}.", link=f"/requests/{req.id}"
    )
    db.commit()
    db.refresh(req)
    return _to_out(db, req)


def bulk_approve(db: Session, request_ids: list[int], actor: AppUser) -> dict:
    approved: list[int] = []
    failed: list[dict] = []
    for rid in request_ids:
        req = db.get(HiringRequest, rid)
        if req is None:
            failed.append({"id": rid, "detail": "Not found"})
            continue
        if req.status != RequestStatus.SUBMITTED:
            failed.append({"id": rid, "detail": f"Not submitted (status={req.status.value})"})
            continue
        _do_approve(db, req, actor, note=None)
        approved.append(rid)
    db.commit()
    return {"approved": approved, "failed": failed}


def cancel_approved_request(db: Session, request_id: int, actor: AppUser, note: str | None) -> RequestDetailOut:
    req = db.get(HiringRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status != RequestStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot cancel a request in status {req.status.value}"
        )

    req.status = RequestStatus.CANCELLED
    db.add(ApprovalEvent(request_id=req.id, actor_id=actor.id, action=ApprovalAction.CANCEL, note=note, at=datetime.utcnow()))
    write_audit(db, actor.id, "hiring_request", req.id, "CANCEL", detail=note or "Cancelled by HR")

    if req.type == RequestType.FTE:
        open_positions = (
            db.query(Position)
            .filter(Position.request_id == req.id, Position.status == PositionStatus.OPEN)
            .all()
        )
        for p in open_positions:
            p.status = PositionStatus.CANCELLED
        posting = db.query(JobPosting).filter(JobPosting.request_id == req.id).first()
        if posting is not None and posting.status != PostingStatus.CLOSED:
            posting.status = PostingStatus.CLOSED
            write_audit(db, actor.id, "job_posting", posting.id, "CLOSE", detail="Closed: request cancelled")
    else:
        engagement = db.query(VendorEngagement).filter(VendorEngagement.request_id == req.id).first()
        if engagement is not None:
            engagement.status = EngagementStatus.CANCELLED
            write_audit(db, actor.id, "vendor_engagement", engagement.id, "CANCEL", detail="Cancelled: request cancelled")

    notify_user(db, req.created_by, f"Your approved request for {req.role_title} was cancelled by HR.", link=f"/requests/{req.id}")
    db.commit()
    db.refresh(req)
    return _to_out(db, req)
