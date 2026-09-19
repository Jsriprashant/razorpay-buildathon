"""Month rollover: closing a cycle snapshots the roster into snapshot_worker,
records its cycle_summary, marks it CLOSED, and opens the next cycle.

Deliberately re-entrant: calling rollover() when nothing is behind is a
no-op, and calling it once when N months are behind (the demo clock can be
advanced several months at once) catches up on all of them in one
transaction. Every write here reuses the same active_days/cost helpers as
kpi_service and recon_service so the closed-month numbers agree with what
those live views showed while the cycle was still open.
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.calc.dates import active_days_in_month, add_months, days_in_month, is_active_on, month_end, month_start
from app.calc.money import fte_month_cost_cents, vendor_month_cost_cents
from app.models import (
    AppUser,
    Cycle,
    CycleStatus,
    CycleSummary,
    EngagementStatus,
    HiringRequest,
    PlanLine,
    Role,
    SnapshotWorker,
    VendorEngagement,
    Worker,
)
from app.schemas.cycles import CycleOut, CycleSummaryOut
from app.services.audit_service import write_audit
from app.services.notification_service import notify_user


def _cycle_out(db: Session, cycle: Cycle) -> CycleOut:
    summary = db.query(CycleSummary).filter(CycleSummary.cycle_id == cycle.id).first()
    return CycleOut(
        id=cycle.id,
        team_id=cycle.team_id,
        month_start=cycle.month_start,
        status=cycle.status,
        opened_at=cycle.opened_at,
        closed_at=cycle.closed_at,
        summary=CycleSummaryOut.model_validate(summary) if summary else None,
    )


def _get_or_open_current_cycle(db: Session, team_id: int, today: date) -> Cycle:
    cycle = (
        db.query(Cycle)
        .filter(Cycle.team_id == team_id, Cycle.status == CycleStatus.OPEN)
        .order_by(Cycle.month_start.desc())
        .first()
    )
    if cycle is None:
        cycle = Cycle(team_id=team_id, month_start=month_start(today), status=CycleStatus.OPEN, opened_at=datetime.utcnow())
        db.add(cycle)
        db.commit()
        db.refresh(cycle)
    return cycle


def get_current_status(db: Session, team_id: int, today: date) -> dict:
    cycle = _get_or_open_current_cycle(db, team_id, today)
    return {
        "cycle": _cycle_out(db, cycle),
        "needs_rollover": cycle.month_start < month_start(today),
        "today": today,
    }


def list_history(db: Session, team_id: int) -> list[CycleOut]:
    cycles = (
        db.query(Cycle)
        .filter(Cycle.team_id == team_id, Cycle.status == CycleStatus.CLOSED)
        .order_by(Cycle.month_start.desc())
        .all()
    )
    return [_cycle_out(db, c) for c in cycles]


def get_cycle(db: Session, team_id: int, cycle_id: int) -> CycleOut:
    cycle = db.get(Cycle, cycle_id)
    if cycle is None or cycle.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
    return _cycle_out(db, cycle)


def _summarize_month(db: Session, team_id: int, period: date) -> tuple[int, int, int]:
    """(fte_hc, vendor_hc, actual_cost_cents) as of the last day of `period`'s
    month — same active/proration rules kpi_service and recon_service use for
    the live current-month figures, just pinned to a closing month-end
    instead of "today"."""
    last_day = month_end(period)
    dim = days_in_month(period.year, period.month)

    workers = db.query(Worker).filter(Worker.team_id == team_id).all()
    fte_hc = 0
    actual_cost = 0
    for w in workers:
        if is_active_on(w.hire_date, w.termination_date, last_day):
            fte_hc += 1
        active_days = active_days_in_month(w.hire_date, w.termination_date, period)
        if active_days > 0:
            actual_cost += fte_month_cost_cents(w.annual_salary_cents, active_days, dim)

    engagements = (
        db.query(VendorEngagement)
        .join(HiringRequest, VendorEngagement.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id, VendorEngagement.status == EngagementStatus.CONFIRMED)
        .all()
    )
    vendor_hc = 0
    for eng in engagements:
        if is_active_on(eng.start_date, eng.end_date, last_day):
            vendor_hc += eng.headcount
        active_days = active_days_in_month(eng.start_date, eng.end_date, period)
        if active_days > 0:
            actual_cost += vendor_month_cost_cents(
                eng.headcount, eng.hourly_rate_cents, eng.hours_per_month, active_days, dim
            )

    return fte_hc, vendor_hc, actual_cost


def _close_cycle(db: Session, cycle: Cycle, actor: AppUser) -> None:
    """Idempotent: writes the snapshot + cycle_summary rows for this cycle's
    month if they don't already exist, then marks it CLOSED."""
    period = cycle.month_start
    last_day = month_end(period)

    already_snapshotted = (
        db.query(SnapshotWorker.id)
        .filter(SnapshotWorker.team_id == cycle.team_id, SnapshotWorker.period_month == period)
        .first()
        is not None
    )
    if not already_snapshotted:
        workers = db.query(Worker).filter(Worker.team_id == cycle.team_id).all()
        for w in workers:
            if is_active_on(w.hire_date, w.termination_date, last_day):
                db.add(
                    SnapshotWorker(
                        period_month=period,
                        worker_id=w.worker_id,
                        team_id=cycle.team_id,
                        name=w.name,
                        job_title=w.job_title,
                        grade=w.grade,
                        hire_date=w.hire_date,
                        termination_date=w.termination_date,
                        exit_reason=w.exit_reason,
                        manager_worker_id=w.manager_worker_id,
                        cost_center=w.cost_center,
                        location=w.location,
                        annual_salary_cents=w.annual_salary_cents,
                        position_id=w.position_id,
                        source=w.source,
                    )
                )

    if db.query(CycleSummary.id).filter(CycleSummary.cycle_id == cycle.id).first() is None:
        fte_hc, vendor_hc, actual_cost = _summarize_month(db, cycle.team_id, period)
        plan_line = (
            db.query(PlanLine).filter(PlanLine.team_id == cycle.team_id, PlanLine.month_start == period).first()
        )
        db.add(
            CycleSummary(
                cycle_id=cycle.id,
                fte_hc=fte_hc,
                vendor_hc=vendor_hc,
                actual_cost_cents=actual_cost,
                plan_budget_cents=plan_line.planned_budget_cents if plan_line else 0,
                plan_fte_hc=plan_line.planned_fte_hc if plan_line else 0,
                plan_vendor_hc=plan_line.planned_vendor_hc if plan_line else 0,
            )
        )

    if cycle.status != CycleStatus.CLOSED:
        cycle.status = CycleStatus.CLOSED
        cycle.closed_at = datetime.utcnow()
        write_audit(db, actor.id, "cycle", cycle.id, "CLOSE", detail=f"Closed cycle {period.isoformat()}")


def rollover(db: Session, team_id: int, actor: AppUser, today: date) -> dict:
    """Close every OPEN cycle whose month is before the current month (in
    order), then open (or reuse) the OPEN cycle for the current month.

    Hiring requests in DRAFT/SUBMITTED/APPROVED keep whatever cycle_id they
    already had — rollover never repoints them, per spec ("carried over
    unchanged"). One transaction: either the whole catch-up commits, or none
    of it does, so a double-click or a mid-request failure can't leave a
    half-closed cycle.
    """
    closed_cycles: list[Cycle] = []
    current_month = month_start(today)

    cycle = _get_or_open_current_cycle(db, team_id, today)
    while cycle.month_start < current_month:
        _close_cycle(db, cycle, actor)
        next_month = add_months(cycle.month_start, 1)
        next_cycle = db.query(Cycle).filter(Cycle.team_id == team_id, Cycle.month_start == next_month).first()
        if next_cycle is None:
            next_cycle = Cycle(
                team_id=team_id, month_start=next_month, status=CycleStatus.OPEN, opened_at=datetime.utcnow()
            )
            db.add(next_cycle)
            db.flush()
        elif next_cycle.status != CycleStatus.OPEN:
            next_cycle.status = CycleStatus.OPEN
        closed_cycles.append(cycle)
        cycle = next_cycle

    if closed_cycles:
        label = cycle.month_start.strftime("%B %Y")
        managers = db.query(AppUser).filter(AppUser.team_id == team_id, AppUser.role == Role.MANAGER).all()
        for m in managers:
            notify_user(db, m.id, f"A new cycle started: {label}. Review your recon and forecast.", link="/home")

    db.commit()
    db.refresh(cycle)
    return {
        "closed_cycles": [_cycle_out(db, c) for c in closed_cycles],
        "current_cycle": _cycle_out(db, cycle),
    }
