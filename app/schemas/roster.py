from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WorkerSource


class WorkerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_id: str
    team_id: int
    name: str
    job_title: str
    grade: str
    hire_date: date
    termination_date: date | None
    exit_reason: str | None
    manager_worker_id: int | None
    manager_name: str | None = None
    cost_center: str
    location: str
    annual_salary_cents: int
    position_id: int | None
    source: WorkerSource
    is_active: bool = True
    is_snapshot: bool = False


class PositionMatchOut(BaseModel):
    position_id: int
    request_id: int
    role_title: str
    grade: str | None
    target_start_date: date
    quantity: int


class WorkerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    job_title: str = Field(min_length=1, max_length=150)
    grade: str = Field(min_length=1, max_length=20)
    hire_date: date
    annual_salary_cents: int = Field(gt=0)
    location: str = Field(min_length=1, max_length=150)
    cost_center: str | None = Field(default=None, max_length=50)
    manager_worker_id: int | None = None
    position_id: int | None = None


class WorkerUpdate(BaseModel):
    job_title: str | None = Field(default=None, min_length=1, max_length=150)
    grade: str | None = Field(default=None, min_length=1, max_length=20)
    annual_salary_cents: int | None = Field(default=None, gt=0)


class WorkerExitRequest(BaseModel):
    last_working_day: date
    reason: str = Field(min_length=1, max_length=500)
