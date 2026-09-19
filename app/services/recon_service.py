"""Month-over-month reconciliation: three tabs, all derived live from the
roster/snapshot/plan/position tables — nothing here is stored (Section rule:
"recon items, forecast, KPIs are derived on request... never stored")."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.calc.dates import active_days_in_month, add_months, days_in_month, is_active_on, month_end
from app.calc.money import fte_month_cost_cents, vendor_month_cost_cents
from app.models import (
    AppUser,
    Cycle,
    CycleSummary,
    EngagementStatus,
    HiringRequest,
    PlanLine,
    Position,
    PositionStatus,
    ReconResolution,
    RequestStatus,
    RequestType,
    SnapshotWorker,
    Team,
    VendorEngagement,
    Worker,
)
from app.schemas.recon import (
    PlanVsActualRow,
    PlanVsActualTab,
    ReconChangeItem,
    ReconChangesTab,
    ReconOut,
    ReconResolveRequest,
    RequestedVsActualItem,
    RequestedVsActualTab,
    UnplannedHireItem,
)

FLAG_UNPLANNED_HIRE = "UNPLANNED_HIRE"
FLAG_UNFILLED_OVERDUE = "UNFILLED_OVERDUE"
FLAG_PLAN_VARIANCE = "PLAN_VARIANCE"


def _resolved_keys(db: Session, team_id: int, period_month: date) -> set[tuple[str, int | None, int | None]]:
    rows = (
        db.query(ReconResolution)
        .filter(ReconResolution.team_id == team_id, ReconResolution.period_month == period_month)
        .all()
    )
    return {(r.category, r.worker_id, r.position_id) for r in rows}


def _changes_tab(db: Session, team_id: int, period_month: date, today: date, resolved: set) -> ReconChangesTab:
    previous_month = add_months(period_month, -1)
    previous_rows = (
        db.query(SnapshotWorker)
        .filter(SnapshotWorker.team_id == team_id, SnapshotWorker.period_month == previous_month)
        .all()
    )
    is_baseline = len(previous_rows) == 0
    previous_by_worker_id = {r.worker_id: r for r in previous_rows}

    as_of = today if period_month == date(today.year, today.month, 1) else month_end(period_month)
    current_workers = [
        w for w in db.query(Worker).filter(Worker.team_id == team_id).all() if is_active_on(w.hire_date, w.termination_date, as_of)
    ]
    current_by_worker_id = {w.worker_id: w for w in current_workers}

    new_hires: list[ReconChangeItem] = []
    exits: list[ReconChangeItem] = []
    changes: list[ReconChangeItem] = []
    unchanged = 0

    def _manager_name(worker_pk: int | None) -> str | None:
        if worker_pk is None:
            return None
        mgr = db.get(Worker, worker_pk)
        return mgr.name if mgr else None

    if not is_baseline:
        for wid, w in current_by_worker_id.items():
            prev = previous_by_worker_id.get(wid)
            if prev is None:
                is_unplanned = w.position_id is None
                new_hires.append(
                    ReconChangeItem(
                        worker_id=wid,
                        name=w.name,
                        category="NEW_HIRE",
                        job_title=w.job_title,
                        flags=[FLAG_UNPLANNED_HIRE] if is_unplanned else [],
                        worker_pk=w.id,
                        # Resolution identity matches the Requested-vs-Actual tab's
                        # unplanned-hire entry for the same worker, so a single
                        # acknowledgement clears the flag in both places.
                        resolved=(FLAG_UNPLANNED_HIRE, w.id, None) in resolved if is_unplanned else False,
                    )
                )
            else:
                grade_changed = prev.grade != w.grade
                salary_changed = prev.annual_salary_cents != w.annual_salary_cents
                title_changed = prev.job_title != w.job_title
                manager_changed = prev.manager_worker_id != w.manager_worker_id
                if grade_changed or salary_changed or title_changed or manager_changed:
                    changes.append(
                        ReconChangeItem(
                            worker_id=wid,
                            name=w.name,
                            category="CHANGE",
                            job_title=w.job_title,
                            before_grade=prev.grade if grade_changed else None,
                            after_grade=w.grade if grade_changed else None,
                            before_salary_cents=prev.annual_salary_cents if salary_changed else None,
                            after_salary_cents=w.annual_salary_cents if salary_changed else None,
                            before_title=prev.job_title if title_changed else None,
                            after_title=w.job_title if title_changed else None,
                            before_manager=_manager_name(prev.manager_worker_id) if manager_changed else None,
                            after_manager=_manager_name(w.manager_worker_id) if manager_changed else None,
                            worker_pk=w.id,
                            resolved=("CHANGE", w.id, None) in resolved,
                        )
                    )
                else:
                    unchanged += 1

        for wid, prev in previous_by_worker_id.items():
            if wid not in current_by_worker_id:
                live_worker = db.query(Worker).filter(Worker.worker_id == wid).first()
                exits.append(
                    ReconChangeItem(
                        worker_id=wid,
                        name=prev.name,
                        category="EXIT",
                        job_title=prev.job_title,
                        worker_pk=live_worker.id if live_worker else None,
                        resolved=("EXIT", live_worker.id if live_worker else None, None) in resolved,
                    )
                )

    return ReconChangesTab(
        is_baseline=is_baseline,
        previous_period=None if is_baseline else previous_month,
        new_hires=new_hires,
        exits=exits,
        changes=changes,
        unchanged_count=unchanged,
    )


def _requested_vs_actual_tab(db: Session, team_id: int, period_month: date, today: date, resolved: set) -> RequestedVsActualTab:
    rows = (
        db.query(Position, HiringRequest)
        .join(HiringRequest, Position.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id, HiringRequest.type == RequestType.FTE)
        .all()
    )
    items: list[RequestedVsActualItem] = []
    for position, req in rows:
        if position.status == PositionStatus.FILLED:
            worker = db.get(Worker, position.filled_worker_id) if position.filled_worker_id else None
            items.append(
                RequestedVsActualItem(
                    position_id=position.id,
                    request_id=req.id,
                    role_title=req.role_title,
                    grade=req.grade,
                    quantity=req.quantity,
                    target_start_date=req.target_start_date,
                    status="FILLED",
                    filled_worker_id=worker.worker_id if worker else None,
                    filled_on=position.filled_on,
                    resolved=("REQUESTED_VS_ACTUAL", None, position.id) in resolved,
                )
            )
        elif position.status == PositionStatus.OPEN:
            overdue = req.target_start_date < today
            items.append(
                RequestedVsActualItem(
                    position_id=position.id,
                    request_id=req.id,
                    role_title=req.role_title,
                    grade=req.grade,
                    quantity=req.quantity,
                    target_start_date=req.target_start_date,
                    status="OVERDUE" if overdue else "OPEN",
                    days_open=(today - req.target_start_date).days if overdue else None,
                    resolved=("REQUESTED_VS_ACTUAL", None, position.id) in resolved,
                )
            )

    as_of = today if period_month == date(today.year, today.month, 1) else month_end(period_month)
    period_start = period_month
    period_end = month_end(period_month)
    unplanned: list[UnplannedHireItem] = []
    for w in db.query(Worker).filter(Worker.team_id == team_id, Worker.position_id.is_(None)).all():
        if period_start <= w.hire_date <= min(period_end, as_of):
            unplanned.append(
                UnplannedHireItem(
                    worker_id=w.worker_id,
                    worker_pk=w.id,
                    name=w.name,
                    job_title=w.job_title,
                    grade=w.grade,
                    hire_date=w.hire_date,
                    resolved=(FLAG_UNPLANNED_HIRE, w.id, None) in resolved,
                )
            )

    return RequestedVsActualTab(positions=items, unplanned_hires=unplanned)


def _plan_vs_actual_tab(db: Session, team_id: int, today: date, resolved: set) -> PlanVsActualTab:
    rows: list[PlanVsActualRow] = []

    closed = (
        db.query(Cycle, CycleSummary)
        .join(CycleSummary, CycleSummary.cycle_id == Cycle.id)
        .filter(Cycle.team_id == team_id)
        .order_by(Cycle.month_start.asc())
        .all()
    )
    for cycle, summary in closed:
        rows.append(
            PlanVsActualRow(
                month_start=cycle.month_start,
                plan_fte_hc=summary.plan_fte_hc,
                actual_fte_hc=summary.fte_hc,
                plan_vendor_hc=summary.plan_vendor_hc,
                actual_vendor_hc=summary.vendor_hc,
                plan_budget_cents=summary.plan_budget_cents,
                actual_cost_cents=summary.actual_cost_cents,
                # actual - plan: positive = over budget, negative = under budget.
                variance_cents=summary.actual_cost_cents - summary.plan_budget_cents,
                is_closed=True,
                resolved=("PLAN_VARIANCE", None, None) in resolved,
            )
        )

    current_month = date(today.year, today.month, 1)
    plan_line = (
        db.query(PlanLine).filter(PlanLine.team_id == team_id, PlanLine.month_start == current_month).first()
    )
    workers = db.query(Worker).filter(Worker.team_id == team_id).all()
    dim = days_in_month(current_month.year, current_month.month)
    actual_fte_hc = 0
    actual_cost = 0
    for w in workers:
        if is_active_on(w.hire_date, w.termination_date, today):
            actual_fte_hc += 1
        active_days = active_days_in_month(w.hire_date, w.termination_date, current_month)
        if active_days > 0:
            actual_cost += fte_month_cost_cents(w.annual_salary_cents, active_days, dim)

    engagements = (
        db.query(VendorEngagement)
        .join(HiringRequest, VendorEngagement.request_id == HiringRequest.id)
        .filter(HiringRequest.team_id == team_id, VendorEngagement.status == EngagementStatus.CONFIRMED)
        .all()
    )
    actual_vendor_hc = 0
    for eng in engagements:
        if is_active_on(eng.start_date, eng.end_date, today):
            actual_vendor_hc += eng.headcount
        active_days = active_days_in_month(eng.start_date, eng.end_date, current_month)
        if active_days > 0:
            actual_cost += vendor_month_cost_cents(eng.headcount, eng.hourly_rate_cents, eng.hours_per_month, active_days, dim)

    if plan_line is not None:
        rows.append(
            PlanVsActualRow(
                month_start=current_month,
                plan_fte_hc=plan_line.planned_fte_hc,
                actual_fte_hc=actual_fte_hc,
                plan_vendor_hc=plan_line.planned_vendor_hc,
                actual_vendor_hc=actual_vendor_hc,
                plan_budget_cents=plan_line.planned_budget_cents,
                actual_cost_cents=actual_cost,
                variance_cents=actual_cost - plan_line.planned_budget_cents,
                is_closed=False,
                resolved=("PLAN_VARIANCE", None, None) in resolved,
            )
        )

    return PlanVsActualTab(rows=rows)


def get_recon(db: Session, team_id: int, period_month: date, today: date) -> ReconOut:
    resolved = _resolved_keys(db, team_id, period_month)
    changes = _changes_tab(db, team_id, period_month, today, resolved)
    requested = _requested_vs_actual_tab(db, team_id, period_month, today, resolved)
    plan_vs_actual = _plan_vs_actual_tab(db, team_id, today, resolved)

    unresolved = 0
    for item in changes.new_hires:
        if FLAG_UNPLANNED_HIRE in item.flags and not item.resolved:
            unresolved += 1
    for item in requested.positions:
        if item.status == "OVERDUE" and not item.resolved:
            unresolved += 1
    for item in requested.unplanned_hires:
        if not item.resolved:
            unresolved += 1
    for row in plan_vs_actual.rows:
        if not row.is_closed and row.variance_cents != 0 and not row.resolved:
            unresolved += 1

    return ReconOut(
        team_id=team_id,
        period_month=period_month,
        changes=changes,
        requested_vs_actual=requested,
        plan_vs_actual=plan_vs_actual,
        unresolved_flag_count=unresolved,
    )


def resolve_flag(db: Session, team_id: int, payload: ReconResolveRequest, actor: AppUser) -> None:
    if payload.worker_pk is not None:
        worker = db.get(Worker, payload.worker_pk)
        if worker is None or worker.team_id != team_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    if payload.position_id is not None:
        position = db.get(Position, payload.position_id)
        if position is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        req = db.get(HiringRequest, position.request_id)
        if req is None or req.team_id != team_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    db.add(
        ReconResolution(
            team_id=team_id,
            period_month=payload.period_month,
            worker_id=payload.worker_pk,
            position_id=payload.position_id,
            category=payload.category,
            note=payload.note,
            by=actor.id,
            at=datetime.utcnow(),
        )
    )
    db.commit()


def link_position(db: Session, team_id: int, worker_pk: int, position_id: int, actor: AppUser) -> None:
    worker = db.get(Worker, worker_pk)
    position = db.get(Position, position_id)
    if worker is None or worker.team_id != team_id:
        raise ValueError("Worker not found")
    if position is None:
        raise ValueError("Position not found")
    req = db.get(HiringRequest, position.request_id)
    if req is None or req.team_id != team_id:
        raise ValueError("Position not found")
    if position.status != PositionStatus.OPEN:
        raise ValueError("Position is not open")
    worker.position_id = position.id
    position.status = PositionStatus.FILLED
    position.filled_worker_id = worker.id
    position.filled_on = worker.hire_date
    db.commit()
