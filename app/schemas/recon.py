from datetime import date

from pydantic import BaseModel


class ReconChangeItem(BaseModel):
    worker_id: str
    name: str
    category: str  # NEW_HIRE | EXIT | CHANGE
    job_title: str | None = None
    before_grade: str | None = None
    after_grade: str | None = None
    before_salary_cents: int | None = None
    after_salary_cents: int | None = None
    before_title: str | None = None
    after_title: str | None = None
    before_manager: str | None = None
    after_manager: str | None = None
    flags: list[str] = []
    worker_pk: int | None = None
    resolved: bool = False


class ReconChangesTab(BaseModel):
    is_baseline: bool
    previous_period: date | None
    new_hires: list[ReconChangeItem]
    exits: list[ReconChangeItem]
    changes: list[ReconChangeItem]
    unchanged_count: int


class RequestedVsActualItem(BaseModel):
    position_id: int
    request_id: int
    role_title: str
    grade: str | None
    quantity: int
    target_start_date: date
    status: str  # FILLED | OPEN | OVERDUE
    filled_worker_id: str | None = None
    filled_on: date | None = None
    days_open: int | None = None
    resolved: bool = False


class UnplannedHireItem(BaseModel):
    worker_id: str
    worker_pk: int
    name: str
    job_title: str
    grade: str | None = None
    hire_date: date
    resolved: bool = False


class RequestedVsActualTab(BaseModel):
    positions: list[RequestedVsActualItem]
    unplanned_hires: list[UnplannedHireItem]


class PlanVsActualRow(BaseModel):
    month_start: date
    plan_fte_hc: int
    actual_fte_hc: int
    plan_vendor_hc: int
    actual_vendor_hc: int
    plan_budget_cents: int
    actual_cost_cents: int
    variance_cents: int
    is_closed: bool
    resolved: bool = False


class PlanVsActualTab(BaseModel):
    rows: list[PlanVsActualRow]


class ReconOut(BaseModel):
    team_id: int
    period_month: date
    changes: ReconChangesTab
    requested_vs_actual: RequestedVsActualTab
    plan_vs_actual: PlanVsActualTab
    unresolved_flag_count: int


class ReconResolveRequest(BaseModel):
    category: str
    worker_pk: int | None = None
    position_id: int | None = None
    period_month: date
    note: str | None = None


class ReconBulkResolveRequest(BaseModel):
    items: list[ReconResolveRequest]


class ReconLinkPositionRequest(BaseModel):
    worker_pk: int
    position_id: int
