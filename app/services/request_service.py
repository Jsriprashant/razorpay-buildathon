"""Hiring request state machine (DRAFT -> SUBMITTED -> APPROVED / REJECTED /
CHANGES_REQUESTED; CHANGES_REQUESTED -> SUBMITTED; DRAFT/SUBMITTED ->
CANCELLED by the manager). Every transition writes an approval_event,
a notification, and an audit_log row. Illegal transitions return 409.

HR-only decisions (approve/reject/request-changes/cancel-an-approved-request)
live in hr_service.py; this module owns the manager-facing half of the
pipeline plus the shared list/detail readers used by both.
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.calc.money import vendor_contract_value_cents
from app.models import (
    AppUser,
    ApprovalAction,
    ApprovalEvent,
    Cycle,
    CycleStatus,
    HiringRequest,
    JobPosting,
    Position,
    RequestStatus,
    RequestType,
    Role,
    Team,
    VendorCompany,
    VendorEngagement,
    VendorMessage,
    Worker,
)
from app.schemas.requests import HiringRequestCreate, HiringRequestUpdate, RequestDetailOut
from app.schemas.vendors import VendorMessageOut
from app.services.audit_service import write_audit
from app.services.hr_fit import compute_fit
from app.services.notification_service import notify_role


def _current_cycle(db: Session, team_id: int) -> Cycle:
    cycle = (
        db.query(Cycle)
        .filter(Cycle.team_id == team_id, Cycle.status == CycleStatus.OPEN)
        .order_by(Cycle.month_start.desc())
        .first()
    )
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No open cycle for this team")
    return cycle


def _contract_value(req: HiringRequest) -> int | None:
    if req.type != RequestType.VENDOR or req.end_date is None:
        return None
    return vendor_contract_value_cents(
        req.quantity, req.hourly_rate_cents or 0, req.hours_per_month or 0, req.target_start_date, req.end_date
    )


def _to_out(db: Session, req: HiringRequest, with_fit: bool = False) -> RequestDetailOut:
    team = db.get(Team, req.team_id)
    creator = db.get(AppUser, req.created_by)
    vendor_company = db.get(VendorCompany, req.vendor_company_id) if req.vendor_company_id else None
    posting = db.query(JobPosting).filter(JobPosting.request_id == req.id).first()
    engagement = db.query(VendorEngagement).filter(VendorEngagement.request_id == req.id).first()

    events = (
        db.query(ApprovalEvent).filter(ApprovalEvent.request_id == req.id).order_by(ApprovalEvent.at.asc()).all()
    )
    event_outs = []
    for e in events:
        actor = db.get(AppUser, e.actor_id)
        event_outs.append(
            {
                "id": e.id,
                "actor_id": e.actor_id,
                "actor_name": actor.name if actor else None,
                "action": e.action,
                "note": e.note,
                "at": e.at,
            }
        )

    positions = db.query(Position).filter(Position.request_id == req.id).all()
    position_outs = []
    for p in positions:
        worker = db.get(Worker, p.filled_worker_id) if p.filled_worker_id else None
        position_outs.append(
            {
                "id": p.id,
                "status": p.status,
                "filled_worker_id": p.filled_worker_id,
                "filled_worker_name": worker.name if worker else None,
                "filled_on": p.filled_on,
            }
        )

    plan_fit = budget_fit = None
    if with_fit:
        plan_fit, budget_fit = compute_fit(db, req)

    vendor_messages: list[VendorMessageOut] = []
    if engagement is not None:
        messages = (
            db.query(VendorMessage)
            .filter(VendorMessage.engagement_id == engagement.id)
            .order_by(VendorMessage.sent_at.asc())
            .all()
        )
        vendor_messages = [VendorMessageOut.model_validate(m) for m in messages]

    return RequestDetailOut(
        id=req.id,
        team_id=req.team_id,
        team_name=team.name if team else None,
        cycle_id=req.cycle_id,
        type=req.type,
        role_title=req.role_title,
        grade=req.grade,
        quantity=req.quantity,
        annual_salary_cents=req.annual_salary_cents,
        hourly_rate_cents=req.hourly_rate_cents,
        hours_per_month=req.hours_per_month,
        vendor_company_id=req.vendor_company_id,
        vendor_company_name=vendor_company.name if vendor_company else None,
        target_start_date=req.target_start_date,
        end_date=req.end_date,
        justification=req.justification,
        source=req.source,
        status=req.status,
        decided_by=req.decided_by,
        decision_note=req.decision_note,
        created_by=req.created_by,
        created_by_name=creator.name if creator else None,
        created_at=req.created_at,
        submitted_at=req.submitted_at,
        approved_at=req.approved_at,
        posting_slug=posting.slug if posting else None,
        posting_status=posting.status.value if posting else None,
        vendor_engagement_id=engagement.id if engagement else None,
        vendor_engagement_status=engagement.status.value if engagement else None,
        contract_value_cents=_contract_value(req),
        plan_fit=plan_fit,
        budget_fit=budget_fit,
        approval_events=event_outs,
        positions=position_outs,
        vendor_messages=vendor_messages,
    )


to_out = _to_out  # public alias used by hr_service.py and other callers


def list_requests(
    db: Session,
    team_id: int,
    status_filter: RequestStatus | None,
    type_filter: RequestType | None,
    q: str | None,
    sort: str | None,
) -> list[RequestDetailOut]:
    query = db.query(HiringRequest).filter(HiringRequest.team_id == team_id)
    if status_filter is not None:
        query = query.filter(HiringRequest.status == status_filter)
    if type_filter is not None:
        query = query.filter(HiringRequest.type == type_filter)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(HiringRequest.role_title.ilike(like) | HiringRequest.justification.ilike(like))

    sort_map = {
        "created_at": HiringRequest.created_at,
        "target_start_date": HiringRequest.target_start_date,
        "status": HiringRequest.status,
        "role_title": HiringRequest.role_title,
    }
    sort_field = sort_map.get((sort or "").lstrip("-"), HiringRequest.created_at)
    if (sort or "").startswith("-") or not sort:
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())

    return [_to_out(db, r) for r in query.all()]


def get_request(db: Session, team_id: int, request_id: int) -> RequestDetailOut:
    req = db.get(HiringRequest, request_id)
    if req is None or req.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return _to_out(db, req, with_fit=True)


def create_request(db: Session, team_id: int, payload: HiringRequestCreate, actor: AppUser) -> RequestDetailOut:
    cycle = _current_cycle(db, team_id)
    if payload.vendor_company_id is not None:
        vendor = db.get(VendorCompany, payload.vendor_company_id)
        if vendor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor company not found")

    req = HiringRequest(
        team_id=team_id,
        cycle_id=cycle.id,
        type=payload.type,
        role_title=payload.role_title,
        grade=payload.grade,
        quantity=payload.quantity,
        annual_salary_cents=payload.annual_salary_cents,
        hourly_rate_cents=payload.hourly_rate_cents,
        hours_per_month=payload.hours_per_month,
        vendor_company_id=payload.vendor_company_id,
        target_start_date=payload.target_start_date,
        end_date=payload.end_date,
        justification=payload.justification,
        source=payload.source,
        status=RequestStatus.DRAFT,
        created_by=actor.id,
        created_at=datetime.utcnow(),
    )
    db.add(req)
    db.flush()
    write_audit(db, actor.id, "hiring_request", req.id, "CREATE", detail=f"Created draft: {req.role_title}")
    db.commit()
    db.refresh(req)
    return _to_out(db, req)


def update_request(db: Session, team_id: int, request_id: int, payload: HiringRequestUpdate, actor: AppUser) -> RequestDetailOut:
    req = db.get(HiringRequest, request_id)
    if req is None or req.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status not in (RequestStatus.DRAFT, RequestStatus.CHANGES_REQUESTED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot edit a request in status {req.status.value}"
        )

    updates = payload.model_dump(exclude_unset=True)
    if "vendor_company_id" in updates and updates["vendor_company_id"] is not None:
        vendor = db.get(VendorCompany, updates["vendor_company_id"])
        if vendor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor company not found")

    for field, value in updates.items():
        setattr(req, field, value)

    _validate_type_invariants(req)

    write_audit(db, actor.id, "hiring_request", req.id, "UPDATE", detail="Edited request fields")
    db.commit()
    db.refresh(req)
    return _to_out(db, req)


def _validate_type_invariants(req: HiringRequest) -> None:
    """Re-checks the FTE/vendor field invariants enforced on create. Edits
    can only change field values, never `type`, but a partial PATCH could
    otherwise leave a request with nulled-out fields its type requires."""
    if req.type == RequestType.FTE:
        if req.annual_salary_cents is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="annual_salary_cents is required for FTE requests")
        if not req.grade:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="grade is required for FTE requests")
    else:
        if req.vendor_company_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="vendor_company_id is required for vendor requests")
        if req.hourly_rate_cents is None or req.hours_per_month is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="hourly_rate_cents and hours_per_month are required for vendor requests"
            )
        if req.end_date is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date is required for vendor requests")
        if req.end_date < req.target_start_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be on/after target_start_date")


def submit_request(db: Session, team_id: int, request_id: int, actor: AppUser) -> RequestDetailOut:
    req = db.get(HiringRequest, request_id)
    if req is None or req.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status != RequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot submit a request in status {req.status.value}"
        )
    _do_submit(db, req, actor)
    db.commit()
    db.refresh(req)
    return _to_out(db, req)


def resubmit_request(db: Session, team_id: int, request_id: int, actor: AppUser) -> RequestDetailOut:
    req = db.get(HiringRequest, request_id)
    if req is None or req.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status != RequestStatus.CHANGES_REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot resubmit a request in status {req.status.value}"
        )
    _do_submit(db, req, actor, action=ApprovalAction.RESUBMIT)
    db.commit()
    db.refresh(req)
    return _to_out(db, req)


def _do_submit(db: Session, req: HiringRequest, actor: AppUser, action: ApprovalAction = ApprovalAction.SUBMIT) -> None:
    req.status = RequestStatus.SUBMITTED
    req.submitted_at = datetime.utcnow()
    req.decision_note = None
    db.add(ApprovalEvent(request_id=req.id, actor_id=actor.id, action=action, note=None, at=datetime.utcnow()))
    write_audit(db, actor.id, "hiring_request", req.id, action.value, detail=f"{req.role_title} submitted for approval")
    notify_role(db, Role.HR, f"New hiring request awaiting review: {req.role_title}", link="/hr/inbox")


def cancel_request(db: Session, team_id: int, request_id: int, actor: AppUser) -> RequestDetailOut:
    req = db.get(HiringRequest, request_id)
    if req is None or req.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status not in (RequestStatus.DRAFT, RequestStatus.SUBMITTED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot cancel a request in status {req.status.value}"
        )
    req.status = RequestStatus.CANCELLED
    db.add(
        ApprovalEvent(request_id=req.id, actor_id=actor.id, action=ApprovalAction.CANCEL, note=None, at=datetime.utcnow())
    )
    write_audit(db, actor.id, "hiring_request", req.id, "CANCEL", detail=f"{req.role_title} cancelled by manager")
    db.commit()
    db.refresh(req)
    return _to_out(db, req)
