from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ApplicationStatus, PostingStatus


class JobPostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    slug: str
    title: str
    description: str
    location: str
    openings: int
    status: PostingStatus
    published_at: datetime
    applicant_count: int = 0
    open_position_count: int = 0


class JobPostingUpdate(BaseModel):
    status: PostingStatus


class PublicPostingListItem(BaseModel):
    slug: str
    title: str
    location: str
    openings: int
    published_at: datetime


class PublicPostingDetail(BaseModel):
    slug: str
    title: str
    description: str
    location: str
    openings: int
    published_at: datetime


class ApplyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    profile_url: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=2000)
    # Honeypot: a real applicant never fills this hidden field in. Any value
    # here means a bot filled the form; we pretend to succeed without saving.
    website: str = Field(default="", max_length=200)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    posting_id: int
    posting_title: str | None = None
    name: str
    email: str
    phone: str | None
    profile_url: str | None
    note: str | None
    status: ApplicationStatus
    created_at: datetime
    suggested_annual_salary_cents: int | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class HireRequest(BaseModel):
    hire_date: date
    annual_salary_cents: int = Field(gt=0)
