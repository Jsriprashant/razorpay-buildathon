"""HR review of applicants (kanban) and the Hire action, which creates a
worker, fills the next open position for the request, and closes the
posting once every opening is filled."""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationStatus,
    HiringRequest,
    JobPosting,
    Position,
    PositionStatus,
    PostingStatus,
    Team,
    Worker,
    WorkerSource,
)
from app.schemas.postings import ApplicationOut, HireRequest
from app.services.audit_service import write_audit
from app.services.notification_service import notify_user
from app.services.posting_service import sanitize_text

DEFAULT_HIRE_LOCATION = "Remote"


def _application_out(db: Session, app_row: Application) -> ApplicationOut:
    posting = db.get(JobPosting, app_row.posting_id)
    request = db.get(HiringRequest, posting.request_id) if posting else None
    return ApplicationOut(
        id=app_row.id,
        posting_id=app_row.posting_id,
        posting_title=posting.title if posting else None,
        name=app_row.name,
        email=app_row.email,
        phone=app_row.phone,
        profile_url=app_row.profile_url,
        note=app_row.note,
        status=app_row.status,
        created_at=app_row.created_at,
        suggested_annual_salary_cents=request.annual_salary_cents if request else None,
    )


def list_applications(
    db: Session, team_id: int | None, posting_id: int | None, q: str | None = None
) -> list[ApplicationOut]:
    query = db.query(Application)
    if posting_id is not None:
        query = query.filter(Application.posting_id == posting_id)
    if team_id is not None:
        query = query.join(JobPosting, JobPosting.id == Application.posting_id).join(
            HiringRequest, HiringRequest.id == JobPosting.request_id
        ).filter(HiringRequest.team_id == team_id)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(Application.name.ilike(like) | Application.email.ilike(like))
    apps = query.order_by(Application.created_at.desc()).all()
    return [_application_out(db, a) for a in apps]


def update_status(db: Session, application_id: int, new_status: ApplicationStatus, actor_id: int) -> ApplicationOut:
    app_row = db.get(Application, application_id)
    if app_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if app_row.status == ApplicationStatus.HIRED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application is already hired")
    if new_status == ApplicationStatus.HIRED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use the hire endpoint to hire an applicant")
    app_row.status = new_status
    write_audit(db, actor_id, "application", app_row.id, f"SET_{new_status.value}")
    db.commit()
    db.refresh(app_row)
    return _application_out(db, app_row)


def hire_applicant(db: Session, application_id: int, payload: HireRequest, actor_id: int) -> ApplicationOut:
    app_row = db.get(Application, application_id)
    if app_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if app_row.status == ApplicationStatus.HIRED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application is already hired")

    posting = db.get(JobPosting, app_row.posting_id)
    if posting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Posting not found")
    request = db.get(HiringRequest, posting.request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Underlying request not found")

    open_position = (
        db.query(Position)
        .filter(Position.request_id == request.id, Position.status == PositionStatus.OPEN)
        .order_by(Position.id.asc())
        .first()
    )
    if open_position is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No open positions remain for this posting")

    team = db.get(Team, request.team_id)
    worker = Worker(
        worker_id=_next_worker_id(db),
        team_id=request.team_id,
        name=sanitize_text(app_row.name) or app_row.name,
        job_title=request.role_title,
        grade=request.grade or "G1",
        hire_date=payload.hire_date,
        manager_worker_id=team.manager_worker_id if team else None,
        cost_center=team.cost_center if team else "",
        location=DEFAULT_HIRE_LOCATION,
        annual_salary_cents=payload.annual_salary_cents,
        position_id=open_position.id,
        source=WorkerSource.HIRED_FROM_POSTING,
    )
    db.add(worker)
    db.flush()

    open_position.status = PositionStatus.FILLED
    open_position.filled_worker_id = worker.id
    open_position.filled_on = payload.hire_date

    app_row.status = ApplicationStatus.HIRED
    write_audit(db, actor_id, "application", app_row.id, "HIRE", detail=f"Hired into position {open_position.id}")
    write_audit(db, actor_id, "worker", worker.id, "CREATE", detail=f"Hired from posting {posting.slug}")

    db.flush()
    remaining_open = (
        db.query(Position.id)
        .filter(Position.request_id == request.id, Position.status == PositionStatus.OPEN)
        .count()
    )
    if remaining_open == 0 and posting.status != PostingStatus.CLOSED:
        posting.status = PostingStatus.CLOSED
        write_audit(db, actor_id, "job_posting", posting.id, "CLOSE", detail="All openings filled")

    notify_user(db, request.created_by, f"{app_row.name} was hired for {request.role_title}.", link="/roster")

    db.commit()
    db.refresh(app_row)
    return _application_out(db, app_row)


def _next_worker_id(db: Session) -> str:
    from sqlalchemy import func

    max_id = db.query(func.max(Worker.id)).scalar() or 0
    candidate = 1000 + max_id + 1
    while db.query(Worker.id).filter(Worker.worker_id == f"W{candidate}").first() is not None:
        candidate += 1
    return f"W{candidate}"
