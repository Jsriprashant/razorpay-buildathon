from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ApprovalAction, PositionStatus, RequestSource, RequestStatus, RequestType
from app.schemas.vendors import VendorMessageOut


class HiringRequestCreate(BaseModel):
    type: RequestType
    role_title: str = Field(min_length=1, max_length=150)
    grade: str | None = Field(default=None, max_length=20)
    quantity: int = Field(default=1, gt=0, le=100)
    annual_salary_cents: int | None = Field(default=None, gt=0)
    vendor_company_id: int | None = None
    hourly_rate_cents: int | None = Field(default=None, gt=0)
    hours_per_month: int | None = Field(default=None, gt=0, le=744)
    target_start_date: date
    end_date: date | None = None
    justification: str = Field(default="", max_length=2000)
    source: RequestSource = RequestSource.MANUAL

    @model_validator(mode="after")
    def _validate_type_fields(self) -> "HiringRequestCreate":
        if self.type == RequestType.FTE:
            if self.annual_salary_cents is None:
                raise ValueError("annual_salary_cents is required for FTE requests")
            if not self.grade:
                raise ValueError("grade is required for FTE requests")
        else:
            if self.vendor_company_id is None:
                raise ValueError("vendor_company_id is required for vendor requests")
            if self.hourly_rate_cents is None or self.hours_per_month is None:
                raise ValueError("hourly_rate_cents and hours_per_month are required for vendor requests")
            if self.end_date is None:
                raise ValueError("end_date is required for vendor requests")
            if self.end_date < self.target_start_date:
                raise ValueError("end_date must be on/after target_start_date")
        return self


class HiringRequestUpdate(BaseModel):
    role_title: str | None = Field(default=None, min_length=1, max_length=150)
    grade: str | None = Field(default=None, max_length=20)
    quantity: int | None = Field(default=None, gt=0, le=100)
    annual_salary_cents: int | None = Field(default=None, gt=0)
    vendor_company_id: int | None = None
    hourly_rate_cents: int | None = Field(default=None, gt=0)
    hours_per_month: int | None = Field(default=None, gt=0, le=744)
    target_start_date: date | None = None
    end_date: date | None = None
    justification: str | None = Field(default=None, max_length=2000)


class DecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class BulkApproveRequest(BaseModel):
    request_ids: list[int] = Field(min_length=1, max_length=100)


class ApprovalEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int
    actor_name: str | None = None
    action: ApprovalAction
    note: str | None
    at: datetime


class PositionSummaryOut(BaseModel):
    id: int
    status: PositionStatus
    filled_worker_id: int | None
    filled_worker_name: str | None = None
    filled_on: date | None


class HiringRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    team_name: str | None = None
    cycle_id: int
    type: RequestType
    role_title: str
    grade: str | None
    quantity: int
    annual_salary_cents: int | None
    hourly_rate_cents: int | None
    hours_per_month: int | None
    vendor_company_id: int | None
    vendor_company_name: str | None = None
    target_start_date: date
    end_date: date | None
    justification: str
    source: RequestSource
    status: RequestStatus
    decided_by: int | None
    decision_note: str | None
    created_by: int
    created_by_name: str | None = None
    created_at: datetime
    submitted_at: datetime | None
    approved_at: datetime | None
    posting_slug: str | None = None
    posting_status: str | None = None
    vendor_engagement_id: int | None = None
    vendor_engagement_status: str | None = None
    contract_value_cents: int | None = None
    plan_fit: str | None = None
    budget_fit: str | None = None


class RequestDetailOut(HiringRequestOut):
    approval_events: list[ApprovalEventOut] = Field(default_factory=list)
    positions: list[PositionSummaryOut] = Field(default_factory=list)
    vendor_messages: list["VendorMessageOut"] = Field(default_factory=list)
