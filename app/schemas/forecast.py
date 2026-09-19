from datetime import date

from pydantic import BaseModel, Field


class MonthPoint(BaseModel):
    month_start: date
    plan_fte_hc: int
    plan_vendor_hc: int
    projected_fte_hc: int
    projected_vendor_hc: int
    with_suggestions_fte_hc: int
    with_suggestions_vendor_hc: int
    plan_cost_cents: int
    no_action_cost_cents: int
    with_suggestions_cost_cents: int


class SuggestionOut(BaseModel):
    type: str
    quantity: int
    start: date
    request_by: date
    urgent: bool
    unit_cost_cents: int | None
    request_prefill: dict


class ForecastOut(BaseModel):
    team_id: int
    generated_on: date
    months: list[MonthPoint]
    suggestions: list[SuggestionOut]
    disclosure: str


class WhatIfRequest(BaseModel):
    hiring_delay_months: int = Field(default=0, ge=0, le=12)
    attrition_pct_override: float | None = Field(default=None, ge=0, le=1)
    hiring_freeze_from_month: date | None = None
    extra_hires: int = Field(default=0, ge=0)
    extra_hires_type: str = Field(default="FTE")  # "FTE" or "VENDOR"
    extra_hires_start_month: date | None = None
    extra_hires_unit_cost_cents: int | None = Field(default=None, ge=0)


class WhatIfMonthPoint(BaseModel):
    month_start: date
    baseline_fte_hc: int
    whatif_fte_hc: int
    baseline_vendor_hc: int
    whatif_vendor_hc: int
    baseline_cost_cents: int
    whatif_cost_cents: int
    delta_hc: int
    delta_cost_cents: int


class WhatIfOut(BaseModel):
    team_id: int
    months: list[WhatIfMonthPoint]
    suggestions: list[SuggestionOut]
