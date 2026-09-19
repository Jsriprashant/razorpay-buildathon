export type Role = "MANAGER" | "HR" | "FINANCE_VIEWER";

export interface DemoUser {
  id: number;
  name: string;
  email: string;
  role: Role;
  team_id: number | null;
}

export interface CurrentUser {
  id: number;
  name: string;
  email: string;
  role: Role;
  team_id: number | null;
  team_name: string | null;
}

export interface Settings {
  currency: string;
  fy_start_month: number;
  vendor_hours_per_month: number;
  attrition_pct_monthly: number;
  fte_lead_days: number;
  vendor_lead_days: number;
  demo_today: string | null;
}
