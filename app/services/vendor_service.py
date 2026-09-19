"""Vendor company directory, the dispatch queue (composer -> simulated send
-> confirm/decline), and the manager-facing vendor engagements view where
ACTIVE/ENDED is derived from dates and never stored.
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.calc.money import vendor_contract_value_cents
from app.services.clock import get_today
from app.models import (
    EngagementStatus,
    HiringRequest,
    Role,
    Team,
    VendorCompany,
    VendorEngagement,
    VendorMessage,
    VendorMessageStatus,
)
from app.schemas.vendors import VendorCompanyCreate, VendorCompanyOut, VendorEngagementOut, VendorMessageOut
from app.services.audit_service import write_audit
from app.services.notification_service import notification_exists, notify_role, notify_user

EXPIRY_WARNING_DAYS = 30


def list_vendor_companies(db: Session, q: str | None = None) -> list[VendorCompanyOut]:
    query = db.query(VendorCompany)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(VendorCompany.name.ilike(like) | VendorCompany.contact_name.ilike(like))
    return [VendorCompanyOut.model_validate(c) for c in query.order_by(VendorCompany.name.asc()).all()]


def create_vendor_company(db: Session, payload: VendorCompanyCreate, actor_id: int) -> VendorCompanyOut:
    company = VendorCompany(name=payload.name, contact_name=payload.contact_name, contact_email=payload.contact_email)
    db.add(company)
    db.flush()
    write_audit(db, actor_id, "vendor_company", company.id, "CREATE", detail=company.name)
    db.commit()
    db.refresh(company)
    return VendorCompanyOut.model_validate(company)


def _engagement_out(db: Session, eng: VendorEngagement, today: date) -> VendorEngagementOut:
    request = db.get(HiringRequest, eng.request_id)
    team = db.get(Team, request.team_id) if request else None
    company = db.get(VendorCompany, eng.vendor_company_id)
    if eng.status == EngagementStatus.CANCELLED:
        lifecycle = "CANCELLED"
    elif eng.start_date > today:
        lifecycle = "UPCOMING"
    elif eng.end_date is not None and eng.end_date < today:
        lifecycle = "ENDED"
    else:
        lifecycle = "ACTIVE"
    contract_value = None
    if eng.end_date is not None:
        contract_value = vendor_contract_value_cents(
            eng.headcount, eng.hourly_rate_cents, eng.hours_per_month, eng.start_date, eng.end_date
        )
    messages = (
        db.query(VendorMessage).filter(VendorMessage.engagement_id == eng.id).order_by(VendorMessage.sent_at.asc()).all()
    )
    return VendorEngagementOut(
        id=eng.id,
        request_id=eng.request_id,
        team_id=request.team_id if request else 0,
        team_name=team.name if team else None,
        role_title=request.role_title if request else None,
        vendor_company_id=eng.vendor_company_id,
        vendor_company_name=company.name if company else None,
        vendor_contact_email=company.contact_email if company else None,
        headcount=eng.headcount,
        hourly_rate_cents=eng.hourly_rate_cents,
        hours_per_month=eng.hours_per_month,
        start_date=eng.start_date,
        end_date=eng.end_date,
        status=eng.status,
        lifecycle=lifecycle,
        contract_value_cents=contract_value,
        messages=[VendorMessageOut.model_validate(m) for m in messages],
    )


def list_dispatch_queue(db: Session, today: date, q: str | None = None) -> list[VendorEngagementOut]:
    ensure_expiry_notifications(db, today)
    query = db.query(VendorEngagement).filter(
        VendorEngagement.status.in_([EngagementStatus.AWAITING_DISPATCH, EngagementStatus.MESSAGE_SENT])
    )
    if q:
        like = f"%{q.lower()}%"
        query = (
            query.join(HiringRequest, HiringRequest.id == VendorEngagement.request_id)
            .join(VendorCompany, VendorCompany.id == VendorEngagement.vendor_company_id)
            .filter(HiringRequest.role_title.ilike(like) | VendorCompany.name.ilike(like))
        )
    engagements = query.all()
    db.commit()
    return [_engagement_out(db, e, today) for e in engagements]


def list_team_vendors(db: Session, team_id: int, today: date, q: str | None = None) -> list[VendorEngagementOut]:
    ensure_expiry_notifications(db, today)
    query = (
        db.query(VendorEngagement)
        .join(HiringRequest, HiringRequest.id == VendorEngagement.request_id)
        .filter(HiringRequest.team_id == team_id)
    )
    if q:
        like = f"%{q.lower()}%"
        query = query.join(VendorCompany, VendorCompany.id == VendorEngagement.vendor_company_id).filter(
            HiringRequest.role_title.ilike(like) | VendorCompany.name.ilike(like)
        )
    engagements = query.all()
    db.commit()
    return [_engagement_out(db, e, today) for e in engagements]


def default_message(db: Session, eng: VendorEngagement) -> tuple[str, str]:
    request = db.get(HiringRequest, eng.request_id)
    team = db.get(Team, request.team_id) if request else None
    company = db.get(VendorCompany, eng.vendor_company_id)
    subject = f"Vendor engagement confirmation - {team.name if team else 'our team'} / {request.role_title if request else ''}"
    end_txt = eng.end_date.isoformat() if eng.end_date else "open-ended"
    body = (
        f"Hi {company.contact_name if company else ''},\n\n"
        f"Please confirm the following engagement:\n"
        f"- Role: {request.role_title if request else ''}\n"
        f"- Headcount: {eng.headcount}\n"
        f"- Rate: {eng.hourly_rate_cents / 100:.2f}/hr, {eng.hours_per_month} hrs/month\n"
        f"- Dates: {eng.start_date.isoformat()} to {end_txt}\n\n"
        f"Thanks,\n{team.name if team else 'CONTINUUM'} HR"
    )
    return subject, body


def send_message(db: Session, engagement_id: int, subject: str, body: str, actor_id: int) -> VendorEngagementOut:
    eng = db.get(VendorEngagement, engagement_id)
    if eng is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    if eng.status not in (EngagementStatus.AWAITING_DISPATCH, EngagementStatus.MESSAGE_SENT):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot send a message for status {eng.status.value}"
        )
    company = db.get(VendorCompany, eng.vendor_company_id)
    db.add(
        VendorMessage(
            engagement_id=eng.id,
            to_email=company.contact_email if company else "",
            subject=subject,
            body=body,
            status=VendorMessageStatus.SENT,
            sent_by=actor_id,
            sent_at=datetime.utcnow(),
        )
    )
    eng.status = EngagementStatus.MESSAGE_SENT
    write_audit(db, actor_id, "vendor_engagement", eng.id, "MESSAGE_SENT", detail="Sent (simulated)")
    request = db.get(HiringRequest, eng.request_id)
    if request is not None:
        notify_user(
            db, request.created_by, f"Vendor message sent to {company.name if company else 'vendor'} for {request.role_title}.", link="/vendors"
        )
    db.commit()
    db.refresh(eng)
    return _engagement_out(db, eng, get_today(db))


def confirm_engagement(db: Session, engagement_id: int, actor_id: int) -> VendorEngagementOut:
    eng = db.get(VendorEngagement, engagement_id)
    if eng is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    if eng.status != EngagementStatus.MESSAGE_SENT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot confirm from status {eng.status.value}"
        )
    eng.status = EngagementStatus.CONFIRMED
    write_audit(db, actor_id, "vendor_engagement", eng.id, "CONFIRM")
    request = db.get(HiringRequest, eng.request_id)
    if request is not None:
        notify_user(db, request.created_by, f"Vendor engagement confirmed for {request.role_title}.", link="/vendors")
    db.commit()
    db.refresh(eng)
    return _engagement_out(db, eng, get_today(db))


def decline_engagement(db: Session, engagement_id: int, actor_id: int, note: str | None) -> VendorEngagementOut:
    eng = db.get(VendorEngagement, engagement_id)
    if eng is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found")
    if eng.status != EngagementStatus.MESSAGE_SENT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Cannot decline from status {eng.status.value}"
        )
    eng.status = EngagementStatus.DECLINED
    write_audit(db, actor_id, "vendor_engagement", eng.id, "DECLINE", detail=note)
    request = db.get(HiringRequest, eng.request_id)
    if request is not None:
        notify_user(
            db, request.created_by, f"Vendor declined the engagement for {request.role_title}.", link="/vendors"
        )
    db.commit()
    db.refresh(eng)
    return _engagement_out(db, eng, get_today(db))


def ensure_expiry_notifications(db: Session, today: date) -> None:
    """Idempotent check-and-notify: a vendor engagement ending within 30 days
    notifies the manager and HR once. Runs on relevant page loads rather than
    a cron, since scheduled/rollover jobs are a later task."""
    from datetime import timedelta

    horizon = today + timedelta(days=EXPIRY_WARNING_DAYS)
    expiring = (
        db.query(VendorEngagement)
        .filter(
            VendorEngagement.status.in_([EngagementStatus.CONFIRMED, EngagementStatus.MESSAGE_SENT]),
            VendorEngagement.end_date.isnot(None),
            VendorEngagement.end_date >= today,
            VendorEngagement.end_date <= horizon,
        )
        .all()
    )
    for eng in expiring:
        request = db.get(HiringRequest, eng.request_id)
        if request is None:
            continue
        message = f"Vendor engagement for {request.role_title} expires on {eng.end_date.isoformat()}."
        if not notification_exists(db, request.created_by, message):
            notify_user(db, request.created_by, message, link="/vendors")
        from app.models import AppUser

        for hr_user in db.query(AppUser).filter(AppUser.role == Role.HR).all():
            if not notification_exists(db, hr_user.id, message):
                notify_user(db, hr_user.id, message, link="/hr/vendor-dispatch")
