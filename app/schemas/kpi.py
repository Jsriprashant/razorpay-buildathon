from datetime import date

from pydantic import BaseModel


class KpiCard(BaseModel):
    key: str
    label: str
    formula: str
    value: float | int | None = None
    display: str
    secondary: str | None = None
    click_through: str | None = None


class KpiOut(BaseModel):
    team_id: int
    period_month: date
    cards: list[KpiCard]
    variance_summary: str
