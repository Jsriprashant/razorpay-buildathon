from datetime import date

from pydantic import BaseModel, Field


class PlanLineOut(BaseModel):
    month_start: date
    planned_fte_hc: int
    planned_vendor_hc: int
    planned_budget_cents: int


class PlanLineIn(BaseModel):
    month_start: date
    planned_fte_hc: int = Field(ge=0)
    planned_vendor_hc: int = Field(ge=0)
    planned_budget_cents: int = Field(ge=0)


class PlanOut(BaseModel):
    team_id: int
    lines: list[PlanLineOut]


class PlanUpdateRequest(BaseModel):
    lines: list[PlanLineIn]
