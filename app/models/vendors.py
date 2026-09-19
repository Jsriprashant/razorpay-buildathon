"""Vendor companies, engagements and the simulated outbox."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import EngagementStatus, VendorMessageStatus


class VendorCompany(Base):
    __tablename__ = "vendor_company"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)


class VendorEngagement(Base):
    __tablename__ = "vendor_engagement"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("hiring_request.id"), nullable=False, unique=True)
    vendor_company_id: Mapped[int] = mapped_column(ForeignKey("vendor_company.id"), nullable=False, index=True)
    headcount: Mapped[int] = mapped_column(Integer, nullable=False)
    hourly_rate_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hours_per_month: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[EngagementStatus] = mapped_column(
        nullable=False, default=EngagementStatus.AWAITING_DISPATCH, index=True
    )


class VendorMessage(Base):
    __tablename__ = "vendor_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("vendor_engagement.id"), nullable=False, index=True)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[VendorMessageStatus] = mapped_column(nullable=False, default=VendorMessageStatus.SENT)
    sent_by: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
