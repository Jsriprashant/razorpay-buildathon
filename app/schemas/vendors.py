from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import EngagementStatus, VendorMessageStatus


class VendorCompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact_name: str
    contact_email: str


class VendorCompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact_name: str = Field(min_length=1, max_length=200)
    contact_email: EmailStr


class VendorMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    engagement_id: int
    to_email: str
    subject: str
    body: str
    status: VendorMessageStatus
    sent_by: int
    sent_at: datetime


class SendMessageRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=5000)


class VendorEngagementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    team_id: int
    team_name: str | None = None
    role_title: str | None = None
    vendor_company_id: int
    vendor_company_name: str | None = None
    vendor_contact_email: str | None = None
    headcount: int
    hourly_rate_cents: int
    hours_per_month: int
    start_date: date
    end_date: date | None
    status: EngagementStatus
    lifecycle: str | None = None  # ACTIVE | ENDED | UPCOMING, derived (never stored)
    contract_value_cents: int | None = None
    messages: list[VendorMessageOut] = Field(default_factory=list)


class DeclineRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
