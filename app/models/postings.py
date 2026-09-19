"""Public job postings and applicant tracking."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import ApplicationStatus, PostingStatus


class JobPosting(Base):
    __tablename__ = "job_posting"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("hiring_request.id"), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    openings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[PostingStatus] = mapped_column(nullable=False, default=PostingStatus.PUBLISHED, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Application(Base):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("posting_id", "email", name="uq_application_posting_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    posting_id: Mapped[int] = mapped_column(ForeignKey("job_posting.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(nullable=False, default=ApplicationStatus.NEW, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
