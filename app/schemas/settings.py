from pydantic import BaseModel


class SettingsOut(BaseModel):
    currency: str
    fy_start_month: int
    vendor_hours_per_month: int
    attrition_pct_monthly: float
    fte_lead_days: int
    vendor_lead_days: int
    demo_today: str | None = None


class SettingsUpdate(BaseModel):
    currency: str | None = None
    fy_start_month: int | None = None
    vendor_hours_per_month: int | None = None
    attrition_pct_monthly: float | None = None
    fte_lead_days: int | None = None
    vendor_lead_days: int | None = None
    demo_today: str | None = None
