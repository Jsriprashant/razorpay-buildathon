"""python -m app.scripts.seed — deterministic demo data (Section 15).

Every date is derived from get_today() (never the real wall clock directly,
except as get_today()'s own fallback). Every record is labelled DEMO in a
free-text field where one exists, and everything else is recognizable as
demo data by construction (worker_id prefix, seeded emails, etc).

Idempotent-ish for a fresh database: run `seed_reset` to wipe and reseed.
"""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.calc.dates import active_days_in_month, add_months, days_in_month, fiscal_year_months, month_end
from app.calc.money import fte_month_cost_cents, vendor_month_cost_cents
from app.database import Base, SessionLocal, engine
from app.models import (
    AppUser,
    Application,
    ApplicationStatus,
    ApprovalAction,
    ApprovalEvent,
    Cycle,
    CycleStatus,
    CycleSummary,
    HiringRequest,
    JobPosting,
    PlanLine,
    Position,
    PositionStatus,
    PostingStatus,
    RequestSource,
    RequestStatus,
    RequestType,
    Role,
    Setting,
    Team,
    VendorCompany,
    VendorEngagement,
    VendorMessage,
    VendorMessageStatus,
    Worker,
    WorkerSource,
)
from app.models.enums import EngagementStatus
from app.models.workforce import SnapshotWorker
from app.services.settings_service import DEFAULT_SETTINGS, ensure_defaults

VENDOR_HOURLY_RATE_CENTS = 5000  # $50/hr, matches the spec's golden example
VENDOR_HOURS_PER_MONTH = 160
DEMO_TAG = "DEMO seed data"


def _get_today(db: Session) -> date:
    row = db.get(Setting, "demo_today")
    if row is not None and row.value:
        return date.fromisoformat(row.value)
    return date.today()


def seed(db: Session) -> None:
    ensure_defaults(db)
    today = _get_today(db)
    fy_start_month = int(DEFAULT_SETTINGS["fy_start_month"] or 1)

    # --- Team & users -----------------------------------------------------
    team = Team(name="Platform Engineering", cost_center="CC-100")
    db.add(team)
    db.flush()

    manager_user = AppUser(name="Priya Sharma", email="manager@demo.headcounthq.dev", role=Role.MANAGER, team_id=team.id)
    hr_user = AppUser(name="Jordan Blake", email="hr@demo.headcounthq.dev", role=Role.HR, team_id=None)
    finance_user = AppUser(
        name="Sam Okafor", email="finance@demo.headcounthq.dev", role=Role.FINANCE_VIEWER, team_id=None
    )
    db.add_all([manager_user, hr_user, finance_user])
    db.flush()

    # --- Workers ------------------------------------------------------------
    # Manager's own worker record (W1001), hired 18 months ago, is everyone's
    # manager_worker_id below.
    manager_hire_date = add_months(today, -18)
    manager_worker = Worker(
        worker_id="W1001",
        team_id=team.id,
        name=manager_user.name,
        job_title="Engineering Manager",
        grade="M1",
        hire_date=manager_hire_date,
        cost_center=team.cost_center,
        location="Remote - US",
        annual_salary_cents=15_000_000,  # $150,000
        source=WorkerSource.SEED,
    )
    db.add(manager_worker)
    db.flush()
    team.manager_worker_id = manager_worker.id

    job_titles = [
        "Software Engineer", "Senior Software Engineer", "Staff Software Engineer",
        "QA Engineer", "Site Reliability Engineer", "Data Engineer", "Product Analyst",
        "Engineering Manager", "Technical Program Manager",
    ]
    grades = ["G1", "G2", "G3", "G4"]
    locations = ["Remote - US", "Remote - India", "New York, NY", "Austin, TX", "Bengaluru, IN"]
    base_salaries_cents = {
        "G1": 8_000_000, "G2": 10_500_000, "G3": 13_000_000, "G4": 16_000_000,
    }

    workers: list[Worker] = [manager_worker]
    pre_existing_count = 22
    for i in range(pre_existing_count):
        idx = i + 2  # W1002..W1023
        # Spread hire dates across the last 18 months, excluding the current month
        months_back = 1 + (i % 17)
        hire_date = add_months(today, -months_back) + timedelta(days=(i * 3) % 26)
        grade = grades[i % len(grades)]
        w = Worker(
            worker_id=f"W{1000 + idx}",
            team_id=team.id,
            name=f"Demo Worker {idx}",
            job_title=job_titles[i % len(job_titles)],
            grade=grade,
            hire_date=hire_date,
            manager_worker_id=manager_worker.id,
            cost_center=team.cost_center,
            location=locations[i % len(locations)],
            annual_salary_cents=base_salaries_cents[grade],
            source=WorkerSource.SEED,
        )
        workers.append(w)
    db.add_all(workers[1:])
    db.flush()

    # Pick specific pre-existing workers (excluding the manager) for the
    # required current-month diffs vs. last month's snapshot.
    exiting_worker = workers[1]
    grade_change_worker = workers[2]
    salary_change_worker = workers[3]

    exit_day = min(10, days_in_month(today.year, today.month))
    exiting_worker.termination_date = date(today.year, today.month, exit_day)
    exiting_worker.exit_reason = "Resigned"

    grade_change_effective = date(today.year, today.month, min(5, days_in_month(today.year, today.month)))
    grade_change_worker_old_grade = grade_change_worker.grade
    grade_change_worker_new_grade = "G4" if grade_change_worker.grade != "G4" else "G3"
    # The live worker row reflects the CURRENT (post-change) state; snapshots
    # for months before grade_change_effective substitute the old grade back
    # in via worker_state_on() below.
    grade_change_worker.grade = grade_change_worker_new_grade

    salary_change_effective = date(today.year, today.month, min(7, days_in_month(today.year, today.month)))
    salary_change_worker_old_salary = salary_change_worker.annual_salary_cents
    salary_change_worker_new_salary = salary_change_worker_old_salary + 600_000  # +$6,000/yr
    salary_change_worker.annual_salary_cents = salary_change_worker_new_salary

    # --- Cycles for the fiscal year, up to and including the current month --
    fy_months = fiscal_year_months(today, fy_start_month)
    current_month_start = date(today.year, today.month, 1)
    cycles: dict[date, Cycle] = {}
    for m in fy_months:
        if m > current_month_start:
            break
        is_current = m == current_month_start
        cycle = Cycle(
            team_id=team.id,
            month_start=m,
            status=CycleStatus.OPEN if is_current else CycleStatus.CLOSED,
            opened_at=datetime.combine(m, datetime.min.time()),
            closed_at=None if is_current else datetime.combine(month_end(m), datetime.min.time()),
        )
        db.add(cycle)
        cycles[m] = cycle
    db.flush()
    current_cycle = cycles[current_month_start]
    closed_months = [m for m in cycles if m != current_month_start]

    # --- Vendor companies & engagements -------------------------------------
    vendor_companies = [
        VendorCompany(name="Alpha Staffing Group", contact_name="Nina Torres", contact_email="nina@alphastaffing.demo"),
        VendorCompany(name="BlueWave Contractors", contact_name="Marcus Lee", contact_email="marcus@bluewave.demo"),
        VendorCompany(name="Crest Talent Partners", contact_name="Devi Nair", contact_email="devi@cresttalent.demo"),
    ]
    db.add_all(vendor_companies)
    db.flush()

    earliest_cycle_month = min(cycles.keys())
    vendor_request_a = HiringRequest(
        team_id=team.id,
        cycle_id=cycles[earliest_cycle_month].id,
        type=RequestType.VENDOR,
        role_title="Contract QA Tester",
        quantity=2,
        hourly_rate_cents=VENDOR_HOURLY_RATE_CENTS,
        hours_per_month=VENDOR_HOURS_PER_MONTH,
        vendor_company_id=vendor_companies[0].id,
        target_start_date=add_months(today, -6),
        end_date=add_months(today, 6),
        justification="Ongoing QA contract coverage.",
        source=RequestSource.MANUAL,
        status=RequestStatus.APPROVED,
        decided_by=hr_user.id,
        created_by=manager_user.id,
        created_at=datetime.combine(add_months(today, -6), datetime.min.time()),
        submitted_at=datetime.combine(add_months(today, -6), datetime.min.time()),
        approved_at=datetime.combine(add_months(today, -6), datetime.min.time()),
    )
    # Expiring within 30 days of today, to light up the "expiring" KPI/notification.
    vendor_b_end = today + timedelta(days=20)
    vendor_request_b = HiringRequest(
        team_id=team.id,
        cycle_id=cycles[earliest_cycle_month].id,
        type=RequestType.VENDOR,
        role_title="Contract Data Analyst",
        quantity=2,
        hourly_rate_cents=VENDOR_HOURLY_RATE_CENTS,
        hours_per_month=VENDOR_HOURS_PER_MONTH,
        vendor_company_id=vendor_companies[1].id,
        target_start_date=add_months(today, -4),
        end_date=vendor_b_end,
        justification="Short-term analytics contract.",
        source=RequestSource.MANUAL,
        status=RequestStatus.APPROVED,
        decided_by=hr_user.id,
        created_by=manager_user.id,
        created_at=datetime.combine(add_months(today, -4), datetime.min.time()),
        submitted_at=datetime.combine(add_months(today, -4), datetime.min.time()),
        approved_at=datetime.combine(add_months(today, -4), datetime.min.time()),
    )
    db.add_all([vendor_request_a, vendor_request_b])
    db.flush()

    engagement_a = VendorEngagement(
        request_id=vendor_request_a.id,
        vendor_company_id=vendor_companies[0].id,
        headcount=2,
        hourly_rate_cents=VENDOR_HOURLY_RATE_CENTS,
        hours_per_month=VENDOR_HOURS_PER_MONTH,
        start_date=vendor_request_a.target_start_date,
        end_date=vendor_request_a.end_date,
        status=EngagementStatus.CONFIRMED,
    )
    engagement_b = VendorEngagement(
        request_id=vendor_request_b.id,
        vendor_company_id=vendor_companies[1].id,
        headcount=2,
        hourly_rate_cents=VENDOR_HOURLY_RATE_CENTS,
        hours_per_month=VENDOR_HOURS_PER_MONTH,
        start_date=vendor_request_b.target_start_date,
        end_date=vendor_request_b.end_date,
        status=EngagementStatus.CONFIRMED,
    )
    db.add_all([engagement_a, engagement_b])
    db.flush()

    for engagement in (engagement_a, engagement_b):
        db.add(
            VendorMessage(
                engagement_id=engagement.id,
                to_email=next(c.contact_email for c in vendor_companies if c.id == engagement.vendor_company_id),
                subject=f"Vendor engagement confirmation - {team.name}",
                body="Confirming headcount, rate and dates for this engagement. (Simulated email)",
                status=VendorMessageStatus.SENT,
                sent_by=hr_user.id,
                sent_at=datetime.combine(engagement.start_date, datetime.min.time()),
            )
        )

    # --- Approved FTE request -> posting -> 2 applications -> 1 filled + 1 overdue OPEN position
    approved_fte_target_start = today - timedelta(days=20)  # already overdue
    approved_fte_request = HiringRequest(
        team_id=team.id,
        cycle_id=current_cycle.id,
        type=RequestType.FTE,
        role_title="Software Engineer",
        grade="G2",
        quantity=2,
        annual_salary_cents=base_salaries_cents["G2"],
        target_start_date=approved_fte_target_start,
        justification="Team growth to support the new platform initiative.",
        source=RequestSource.MANUAL,
        status=RequestStatus.APPROVED,
        decided_by=hr_user.id,
        created_by=manager_user.id,
        created_at=datetime.combine(approved_fte_target_start - timedelta(days=30), datetime.min.time()),
        submitted_at=datetime.combine(approved_fte_target_start - timedelta(days=30), datetime.min.time()),
        approved_at=datetime.combine(approved_fte_target_start - timedelta(days=25), datetime.min.time()),
    )
    db.add(approved_fte_request)
    db.flush()

    db.add(
        ApprovalEvent(
            request_id=approved_fte_request.id,
            actor_id=manager_user.id,
            action=ApprovalAction.SUBMIT,
            note=None,
            at=approved_fte_request.submitted_at,
        )
    )
    db.add(
        ApprovalEvent(
            request_id=approved_fte_request.id,
            actor_id=hr_user.id,
            action=ApprovalAction.APPROVE,
            note="Approved - budget available.",
            at=approved_fte_request.approved_at,
        )
    )

    posting = JobPosting(
        request_id=approved_fte_request.id,
        slug="software-engineer-platform-engineering",
        title="Software Engineer - Platform Engineering",
        description=(
            "Platform Engineering is hiring a Software Engineer (Grade G2). "
            "Join a team building the internal platform powering the rest of the org."
        ),
        location="Remote - US",
        openings=approved_fte_request.quantity,
        status=PostingStatus.PUBLISHED,
        published_at=datetime.combine(approved_fte_request.approved_at.date(), datetime.min.time()),
    )
    db.add(posting)
    db.flush()

    db.add(
        Application(
            posting_id=posting.id,
            name="Alex Rivera",
            email="alex.rivera@example.demo",
            phone="555-0101",
            profile_url="https://example.demo/alex-rivera",
            note="5 years backend experience.",
            status=ApplicationStatus.NEW,
            created_at=datetime.combine(today - timedelta(days=3), datetime.min.time()),
        )
    )

    filled_position = Position(request_id=approved_fte_request.id, status=PositionStatus.OPEN)
    overdue_open_position = Position(request_id=approved_fte_request.id, status=PositionStatus.OPEN)
    db.add_all([filled_position, overdue_open_position])
    db.flush()

    # New hire #1: linked to the approved position (fills it).
    linked_hire_date = date(today.year, today.month, min(3, days_in_month(today.year, today.month)))
    linked_new_hire = Worker(
        worker_id="W1024",
        team_id=team.id,
        name="Morgan Ellis",
        job_title="Software Engineer",
        grade="G2",
        hire_date=linked_hire_date,
        manager_worker_id=manager_worker.id,
        cost_center=team.cost_center,
        location="Remote - US",
        annual_salary_cents=base_salaries_cents["G2"],
        position_id=filled_position.id,
        source=WorkerSource.HIRED_FROM_POSTING,
    )
    db.add(linked_new_hire)
    db.flush()
    filled_position.status = PositionStatus.FILLED
    filled_position.filled_worker_id = linked_new_hire.id
    filled_position.filled_on = linked_hire_date

    hired_application = Application(
        posting_id=posting.id,
        name="Morgan Ellis",
        email="morgan.ellis@example.demo",
        phone="555-0103",
        profile_url="https://example.demo/morgan-ellis",
        note="Hired.",
        status=ApplicationStatus.HIRED,
        created_at=datetime.combine(linked_hire_date - timedelta(days=10), datetime.min.time()),
    )
    db.add(hired_application)

    # New hire #2: UNPLANNED (no linked position).
    unplanned_hire_date = date(today.year, today.month, min(12, days_in_month(today.year, today.month)))
    unplanned_new_hire = Worker(
        worker_id="W1025",
        team_id=team.id,
        name="Taylor Brooks",
        job_title="Data Engineer",
        grade="G1",
        hire_date=unplanned_hire_date,
        manager_worker_id=manager_worker.id,
        cost_center=team.cost_center,
        location="Remote - India",
        annual_salary_cents=base_salaries_cents["G1"],
        source=WorkerSource.MANUAL,
    )
    db.add(unplanned_new_hire)

    # --- One SUBMITTED FTE request waiting in the HR inbox ------------------
    submitted_request = HiringRequest(
        team_id=team.id,
        cycle_id=current_cycle.id,
        type=RequestType.FTE,
        role_title="Senior Software Engineer",
        grade="G3",
        quantity=1,
        annual_salary_cents=base_salaries_cents["G3"],
        target_start_date=today + timedelta(days=30),
        justification="Backfill for anticipated attrition on the core services team.",
        source=RequestSource.MANUAL,
        status=RequestStatus.SUBMITTED,
        created_by=manager_user.id,
        created_at=datetime.combine(today - timedelta(days=2), datetime.min.time()),
        submitted_at=datetime.combine(today - timedelta(days=2), datetime.min.time()),
    )
    db.add(submitted_request)
    db.flush()
    db.add(
        ApprovalEvent(
            request_id=submitted_request.id,
            actor_id=manager_user.id,
            action=ApprovalAction.SUBMIT,
            note=None,
            at=submitted_request.submitted_at,
        )
    )

    db.flush()

    # --- Snapshots + cycle_summary for every CLOSED month -------------------
    all_workers = db.query(Worker).filter(Worker.team_id == team.id).all()

    def worker_state_on(w: Worker, as_of: date) -> tuple[str, int] | None:
        """Returns (grade, annual_salary_cents) as they were on `as_of`, or
        None if the worker wasn't active on that date. Only the two
        specifically-seeded change events differ by date; everyone else is
        constant over time."""
        if w.hire_date > as_of:
            return None
        if w.termination_date is not None and w.termination_date < as_of:
            return None
        grade = w.grade
        salary = w.annual_salary_cents
        if w.id == grade_change_worker.id and as_of < grade_change_effective:
            grade = grade_change_worker_old_grade
        if w.id == salary_change_worker.id and as_of < salary_change_effective:
            salary = salary_change_worker_old_salary
        return grade, salary

    vendor_engagements_for_cost = [engagement_a, engagement_b]

    for m in sorted(closed_months):
        last_day = month_end(m)
        dim = days_in_month(m.year, m.month)
        fte_hc = 0
        actual_cost = 0
        for w in all_workers:
            state = worker_state_on(w, last_day)
            if state is None:
                continue
            # Skip workers who are only "active" at snapshot time because
            # they're seeded as hired after this closed month (their
            # hire_date check inside worker_state_on already handles this).
            fte_hc += 1
            grade, salary = state
            # A closed month's snapshot reflects what was true as of that
            # month — a termination that happens later (this month) must not
            # leak backwards into earlier snapshots, or every past month
            # would falsely show the exit too.
            termination_as_of = w.termination_date if w.termination_date is not None and w.termination_date <= last_day else None
            exit_reason_as_of = w.exit_reason if termination_as_of is not None else None
            db.add(
                SnapshotWorker(
                    period_month=m,
                    worker_id=w.worker_id,
                    team_id=team.id,
                    name=w.name,
                    job_title=w.job_title,
                    grade=grade,
                    hire_date=w.hire_date,
                    termination_date=termination_as_of,
                    exit_reason=exit_reason_as_of,
                    manager_worker_id=w.manager_worker_id,
                    cost_center=w.cost_center,
                    location=w.location,
                    annual_salary_cents=salary,
                    position_id=w.position_id,
                    source=w.source,
                )
            )
            active_days = active_days_in_month(w.hire_date, w.termination_date, m)
            actual_cost += fte_month_cost_cents(salary, active_days, dim)

        vendor_hc = 0
        for eng in vendor_engagements_for_cost:
            if eng.start_date <= last_day and (eng.end_date is None or eng.end_date >= last_day):
                vendor_hc += eng.headcount
                actual_cost += vendor_month_cost_cents(eng.headcount, eng.hourly_rate_cents, eng.hours_per_month, dim, dim)

        plan_fte_hc = fte_hc
        plan_vendor_hc = 4
        avg_salary = base_salaries_cents["G2"]
        plan_budget = plan_fte_hc * (avg_salary // 12) + plan_vendor_hc * (
            VENDOR_HOURLY_RATE_CENTS * VENDOR_HOURS_PER_MONTH
        )

        db.add(
            PlanLine(
                team_id=team.id,
                month_start=m,
                planned_fte_hc=plan_fte_hc,
                planned_vendor_hc=plan_vendor_hc,
                planned_budget_cents=plan_budget,
            )
        )
        db.add(
            CycleSummary(
                cycle_id=cycles[m].id,
                fte_hc=fte_hc,
                vendor_hc=vendor_hc,
                actual_cost_cents=actual_cost,
                plan_budget_cents=plan_budget,
                plan_fte_hc=plan_fte_hc,
                plan_vendor_hc=plan_vendor_hc,
            )
        )

    # --- Full fiscal-year plan (including current + future months) ----------
    current_active_fte = sum(
        1 for w in all_workers if w.hire_date <= today and (w.termination_date is None or w.termination_date >= today)
    )
    avg_salary = base_salaries_cents["G2"]
    for offset, m in enumerate(fy_months):
        if m in cycles:  # already written above for closed months
            continue
        months_after_current = (m.year - current_month_start.year) * 12 + (m.month - current_month_start.month)
        if m == current_month_start:
            planned_fte = current_active_fte + 1
        else:
            planned_fte = current_active_fte + 1 + months_after_current
        planned_vendor = 4
        planned_budget = planned_fte * (avg_salary // 12) + planned_vendor * (
            VENDOR_HOURLY_RATE_CENTS * VENDOR_HOURS_PER_MONTH
        )
        db.add(
            PlanLine(
                team_id=team.id,
                month_start=m,
                planned_fte_hc=planned_fte,
                planned_vendor_hc=planned_vendor,
                planned_budget_cents=planned_budget,
            )
        )

    # Current month plan line (month_start == current_month_start) explicitly:
    db.add(
        PlanLine(
            team_id=team.id,
            month_start=current_month_start,
            planned_fte_hc=current_active_fte + 1,
            planned_vendor_hc=4,
            planned_budget_cents=(current_active_fte + 1) * (avg_salary // 12)
            + 4 * (VENDOR_HOURLY_RATE_CENTS * VENDOR_HOURS_PER_MONTH),
        )
    )

    db.commit()
    print(f"Seed complete. {DEMO_TAG}: team={team.name}, workers={len(all_workers)}, today={today.isoformat()}")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Team).count() > 0:
            print("Seed skipped: data already present. Use `python -m app.scripts.seed_reset` to reseed.")
            return
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
