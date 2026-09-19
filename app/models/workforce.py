"""Worker roster and immutable monthly snapshots."""
from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import WorkerSource


class Worker(Base):
    __tablename__ = "worker"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_worker_id: Mapped[int | None] = mapped_column(
        ForeignKey("worker.id", use_alter=True, name="fk_worker_manager_worker"),
        nullable=True,
    )
    cost_center: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    annual_salary_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    position_id: Mapped[int | None] = mapped_column(
        ForeignKey("position.id", use_alter=True, name="fk_worker_position"),
        nullable=True,
    )
    source: Mapped[WorkerSource] = mapped_column(nullable=False, default=WorkerSource.MANUAL)

    team: Mapped["Team"] = relationship(back_populates="workers", foreign_keys=[team_id])  # noqa: F821


class SnapshotWorker(Base):
    """Immutable point-in-time copy of a worker row, taken at month rollover."""

    __tablename__ = "snapshot_worker"
    __table_args__ = (UniqueConstraint("team_id", "period_month", "worker_id", name="uq_snapshot_period_worker"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    period_month: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    worker_id: Mapped[str] = mapped_column(String(20), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_worker_id: Mapped[int | None] = mapped_column(nullable=True)
    cost_center: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    annual_salary_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    position_id: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[WorkerSource] = mapped_column(nullable=False)
