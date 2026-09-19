"""Cycle rollover + history — see app/services/cycle_service.py for the
idempotent close/open logic these schemas wrap."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CycleStatus


class CycleSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fte_hc: int
    vendor_hc: int
    actual_cost_cents: int
    plan_budget_cents: int
    plan_fte_hc: int
    plan_vendor_hc: int


class CycleOut(BaseModel):
    id: int
    team_id: int
    month_start: date
    status: CycleStatus
    opened_at: datetime
    closed_at: datetime | None
    summary: CycleSummaryOut | None = None


class CycleCurrentOut(BaseModel):
    cycle: CycleOut
    needs_rollover: bool
    today: date


class RolloverOut(BaseModel):
    closed_cycles: list[CycleOut]
    current_cycle: CycleOut
