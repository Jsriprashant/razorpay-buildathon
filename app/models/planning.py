"""Plan lines, monthly cycles, and closed-cycle summaries."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import CycleStatus


class PlanLine(Base):
    __tablename__ = "plan_line"
    __table_args__ = (UniqueConstraint("team_id", "month_start", name="uq_plan_team_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), nullable=False, index=True)
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    planned_fte_hc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_vendor_hc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_budget_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class Cycle(Base):
    __tablename__ = "cycle"
    __table_args__ = (UniqueConstraint("team_id", "month_start", name="uq_cycle_team_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), nullable=False, index=True)
    month_start: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[CycleStatus] = mapped_column(nullable=False, default=CycleStatus.OPEN)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CycleSummary(Base):
    __tablename__ = "cycle_summary"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("cycle.id"), nullable=False, unique=True, index=True)
    fte_hc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vendor_hc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_cost_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    plan_budget_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    plan_fte_hc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    plan_vendor_hc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
