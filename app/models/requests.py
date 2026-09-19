"""Hiring requests, positions and their approval trail."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import ApprovalAction, PositionStatus, RequestSource, RequestStatus, RequestType


class HiringRequest(Base):
    __tablename__ = "hiring_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), nullable=False, index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycle.id"), nullable=False, index=True)
    type: Mapped[RequestType] = mapped_column(nullable=False)
    role_title: Mapped[str] = mapped_column(String(150), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    annual_salary_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    hourly_rate_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    hours_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vendor_company_id: Mapped[int | None] = mapped_column(ForeignKey("vendor_company.id"), nullable=True)
    target_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    justification: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[RequestSource] = mapped_column(nullable=False, default=RequestSource.MANUAL)
    status: Mapped[RequestStatus] = mapped_column(nullable=False, default=RequestStatus.DRAFT, index=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Position(Base):
    __tablename__ = "position"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("hiring_request.id"), nullable=False, index=True)
    status: Mapped[PositionStatus] = mapped_column(nullable=False, default=PositionStatus.OPEN, index=True)
    filled_worker_id: Mapped[int | None] = mapped_column(ForeignKey("worker.id"), nullable=True)
    filled_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class ApprovalEvent(Base):
    __tablename__ = "approval_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("hiring_request.id"), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    action: Mapped[ApprovalAction] = mapped_column(nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
