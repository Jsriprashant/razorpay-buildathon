"""Roster: the live worker table for a team, plus historical (snapshot)
views for closed months. Business logic only — routers stay thin."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.calc.dates import is_active_on, month_end
from app.models import (
    AppUser,
    AuditLog,
    Cycle,
    HiringRequest,
    Position,
    PositionStatus,
    RequestStatus,
    RequestType,
    SnapshotWorker,
    Team,
    Worker,
    WorkerSource,
)
from app.schemas.roster import PositionMatchOut, WorkerCreate, WorkerExitRequest, WorkerOut, WorkerUpdate


def _next_worker_id(db: Session) -> str:
    max_id = db.query(func.max(Worker.id)).scalar() or 0
    # worker_id is a display code, independent of the numeric PK sequence,
    # but W1000+id keeps it collision-free without a second counter table.
    candidate = 1000 + max_id + 1
    while db.query(Worker).filter(Worker.worker_id == f"W{candidate}").first() is not None:
        candidate += 1
    return f"W{candidate}"


def _worker_out(w: Worker, as_of: date, manager_name: str | None, is_snapshot: bool = False) -> WorkerOut:
    return WorkerOut(
        id=w.id,
        worker_id=w.worker_id,
        team_id=w.team_id,
        name=w.name,
        job_title=w.job_title,
        grade=w.grade,
        hire_date=w.hire_date,
        termination_date=w.termination_date,
        exit_reason=w.exit_reason,
        manager_worker_id=w.manager_worker_id,
        manager_name=manager_name,
        cost_center=w.cost_center,
        location=w.location,
        annual_salary_cents=w.annual_salary_cents,
        position_id=w.position_id,
        source=w.source,
        is_active=is_active_on(w.hire_date, w.termination_date, as_of),
        is_snapshot=is_snapshot,
    )


def get_roster(db: Session, team_id: int, month: date, today: date) -> list[WorkerOut]:
    """Live table for the current month; immutable snapshot for any closed
    (past) month so history never drifts as workers are later edited."""
    current_month = date(today.year, today.month, 1)
    requested_month = date(month.year, month.month, 1)

    if requested_month >= current_month:
        as_of = today if requested_month == current_month else month_end(requested_month)
        workers = db.query(Worker).filter(Worker.team_id == team_id).all()
        names_by_id = {w.id: w.name for w in workers}
        return [
            _worker_out(w, as_of, names_by_id.get(w.manager_worker_id))
            for w in workers
            if w.hire_date <= as_of
        ]

    rows = (
        db.query(SnapshotWorker)
        .filter(SnapshotWorker.team_id == team_id, SnapshotWorker.period_month == requested_month)
        .all()
    )
    names_by_worker_id = {r.worker_id: r.name for r in rows}
    result = []
    for r in rows:
        manager_name = None
        # manager_worker_id on a snapshot row is a Worker.id (FK-less int);
        # snapshot rows don't carry the manager's worker_id string, so we
        # can only resolve the manager's name via a second live lookup.
        if r.manager_worker_id is not None:
            mgr = db.get(Worker, r.manager_worker_id)
            manager_name = mgr.name if mgr else None
        result.append(
            WorkerOut(
                id=r.id,
                worker_id=r.worker_id,
                team_id=r.team_id,
                name=r.name,
                job_title=r.job_title,
                grade=r.grade,
                hire_date=r.hire_date,
                termination_date=r.termination_date,
                exit_reason=r.exit_reason,
                manager_worker_id=r.manager_worker_id,
                manager_name=manager_name,
                cost_center=r.cost_center,
                location=r.location,
                annual_salary_cents=r.annual_salary_cents,
                position_id=r.position_id,
                source=r.source,
                is_active=is_active_on(r.hire_date, r.termination_date, month_end(requested_month)),
                is_snapshot=True,
            )
        )
    del names_by_worker_id
    return result


def propose_position_matches(db: Session, team_id: int, job_title: str, grade: str | None) -> list[PositionMatchOut]:
    q = (
        db.query(Position, HiringRequest)
        .join(HiringRequest, Position.request_id == HiringRequest.id)
        .filter(
            HiringRequest.team_id == team_id,
            HiringRequest.type == RequestType.FTE,
            HiringRequest.status == RequestStatus.APPROVED,
            Position.status == PositionStatus.OPEN,
            func.lower(HiringRequest.role_title) == job_title.strip().lower(),
        )
    )
    if grade:
        q = q.filter(HiringRequest.grade == grade)
    q = q.order_by(HiringRequest.target_start_date.asc())
    matches = []
    for position, req in q.all():
        matches.append(
            PositionMatchOut(
                position_id=position.id,
                request_id=req.id,
                role_title=req.role_title,
                grade=req.grade,
                target_start_date=req.target_start_date,
                quantity=req.quantity,
            )
        )
    return matches


def _audit(db: Session, actor: AppUser, entity: str, entity_id: int, action: str, detail: str | None = None) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            detail_json=detail,
            at=datetime.utcnow(),
        )
    )


def add_worker(db: Session, team_id: int, payload: WorkerCreate, actor: AppUser) -> WorkerOut:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    position = None
    if payload.position_id is not None:
        position = db.get(Position, payload.position_id)
        if position is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        request = db.get(HiringRequest, position.request_id)
        if request is None or request.team_id != team_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        if position.status != PositionStatus.OPEN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position is not open")

    worker = Worker(
        worker_id=_next_worker_id(db),
        team_id=team_id,
        name=payload.name,
        job_title=payload.job_title,
        grade=payload.grade,
        hire_date=payload.hire_date,
        manager_worker_id=payload.manager_worker_id or team.manager_worker_id,
        cost_center=payload.cost_center or team.cost_center,
        location=payload.location,
        annual_salary_cents=payload.annual_salary_cents,
        position_id=position.id if position else None,
        source=WorkerSource.HIRED_FROM_POSTING if position else WorkerSource.MANUAL,
    )
    db.add(worker)
    db.flush()

    if position:
        position.status = PositionStatus.FILLED
        position.filled_worker_id = worker.id
        position.filled_on = payload.hire_date

    _audit(db, actor, "worker", worker.id, "CREATE", detail=f"Added {worker.name} ({worker.worker_id})")
    db.commit()
    db.refresh(worker)
    manager = db.get(Worker, worker.manager_worker_id) if worker.manager_worker_id else None
    return _worker_out(worker, payload.hire_date, manager.name if manager else None)


def update_worker(db: Session, worker_id: int, team_id: int, payload: WorkerUpdate, actor: AppUser, today: date) -> WorkerOut:
    worker = db.get(Worker, worker_id)
    if worker is None or worker.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    changes = payload.model_dump(exclude_unset=True)
    before = {k: getattr(worker, k) for k in changes}
    for key, value in changes.items():
        setattr(worker, key, value)

    if changes:
        _audit(
            db,
            actor,
            "worker",
            worker.id,
            "UPDATE",
            detail=f"{before} -> {changes} (effective {today.isoformat()})",
        )
    db.commit()
    db.refresh(worker)
    manager = db.get(Worker, worker.manager_worker_id) if worker.manager_worker_id else None
    return _worker_out(worker, today, manager.name if manager else None)


def record_exit(db: Session, worker_id: int, team_id: int, payload: WorkerExitRequest, actor: AppUser) -> WorkerOut:
    worker = db.get(Worker, worker_id)
    if worker is None or worker.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    if worker.termination_date is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Worker already has an exit recorded")
    if payload.last_working_day < worker.hire_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exit date is before hire date")

    worker.termination_date = payload.last_working_day
    worker.exit_reason = payload.reason
    _audit(
        db,
        actor,
        "worker",
        worker.id,
        "EXIT",
        detail=f"Last day {payload.last_working_day.isoformat()}: {payload.reason}",
    )
    db.commit()
    db.refresh(worker)
    manager = db.get(Worker, worker.manager_worker_id) if worker.manager_worker_id else None
    return _worker_out(worker, payload.last_working_day, manager.name if manager else None)
