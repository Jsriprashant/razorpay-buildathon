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

export interface Worker {
  id: number;
  worker_id: string;
  team_id: number;
  name: string;
  job_title: string;
  grade: string;
  hire_date: string;
  termination_date: string | null;
  exit_reason: string | null;
  manager_worker_id: number | null;
  manager_name: string | null;
  cost_center: string;
  location: string;
  annual_salary_cents: number;
  position_id: number | null;
  source: "SEED" | "MANUAL" | "HIRED_FROM_POSTING";
  is_active: boolean;
  is_snapshot: boolean;
}

export interface PositionMatch {
  position_id: number;
  request_id: number;
  role_title: string;
  grade: string | null;
  target_start_date: string;
  quantity: number;
}

export interface ReconChangeItem {
  worker_id: string;
  name: string;
  category: "NEW_HIRE" | "EXIT" | "CHANGE";
  job_title: string | null;
  before_grade: string | null;
  after_grade: string | null;
  before_salary_cents: number | null;
  after_salary_cents: number | null;
  before_title: string | null;
  after_title: string | null;
  before_manager: string | null;
  after_manager: string | null;
  flags: string[];
  worker_pk: number | null;
  resolved: boolean;
}

export interface ReconChangesTab {
  is_baseline: boolean;
  previous_period: string | null;
  new_hires: ReconChangeItem[];
  exits: ReconChangeItem[];
  changes: ReconChangeItem[];
  unchanged_count: number;
}

export interface RequestedVsActualItem {
  position_id: number;
  request_id: number;
  role_title: string;
  grade: string | null;
  quantity: number;
  target_start_date: string;
  status: "FILLED" | "OPEN" | "OVERDUE";
  filled_worker_id: string | null;
  filled_on: string | null;
  days_open: number | null;
  resolved: boolean;
}

export interface UnplannedHireItem {
  worker_id: string;
  worker_pk: number;
  name: string;
  job_title: string;
  grade: string | null;
  hire_date: string;
  resolved: boolean;
}

export interface RequestedVsActualTab {
  positions: RequestedVsActualItem[];
  unplanned_hires: UnplannedHireItem[];
}

export interface PlanVsActualRow {
  month_start: string;
  plan_fte_hc: number;
  actual_fte_hc: number;
  plan_vendor_hc: number;
  actual_vendor_hc: number;
  plan_budget_cents: number;
  actual_cost_cents: number;
  variance_cents: number;
  is_closed: boolean;
  resolved: boolean;
}

export interface ReconOut {
  team_id: number;
  period_month: string;
  changes: ReconChangesTab;
  requested_vs_actual: RequestedVsActualTab;
  plan_vs_actual: { rows: PlanVsActualRow[] };
  unresolved_flag_count: number;
}

export interface KpiCard {
  key: string;
  label: string;
  formula: string;
  value: number | null;
  display: string;
  secondary: string | null;
  click_through: string | null;
}

export interface KpiOut {
  team_id: number;
  period_month: string;
  cards: KpiCard[];
  variance_summary: string;
}

export interface PlanLine {
  month_start: string;
  planned_fte_hc: number;
  planned_vendor_hc: number;
  planned_budget_cents: number;
}

export interface PlanOut {
  team_id: number;
  lines: PlanLine[];
}

export interface ForecastMonthPoint {
  month_start: string;
  plan_fte_hc: number;
  plan_vendor_hc: number;
  projected_fte_hc: number;
  projected_vendor_hc: number;
  with_suggestions_fte_hc: number;
  with_suggestions_vendor_hc: number;
  plan_cost_cents: number;
  no_action_cost_cents: number;
  with_suggestions_cost_cents: number;
}

export interface ForecastSuggestion {
  type: "FTE" | "VENDOR";
  quantity: number;
  start: string;
  request_by: string;
  urgent: boolean;
  unit_cost_cents: number | null;
  request_prefill: Record<string, unknown>;
}

export interface ForecastOut {
  team_id: number;
  generated_on: string;
  months: ForecastMonthPoint[];
  suggestions: ForecastSuggestion[];
  disclosure: string;
}

export interface WhatIfMonthPoint {
  month_start: string;
  baseline_fte_hc: number;
  whatif_fte_hc: number;
  baseline_vendor_hc: number;
  whatif_vendor_hc: number;
  baseline_cost_cents: number;
  whatif_cost_cents: number;
  delta_hc: number;
  delta_cost_cents: number;
}

export interface WhatIfRequest {
  hiring_delay_months: number;
  attrition_pct_override: number | null;
  hiring_freeze_from_month: string | null;
  extra_hires: number;
  extra_hires_type: "FTE" | "VENDOR";
  extra_hires_start_month: string | null;
  extra_hires_unit_cost_cents: number | null;
}

export interface WhatIfOut {
  team_id: number;
  months: WhatIfMonthPoint[];
  suggestions: ForecastSuggestion[];
}

export type RequestType = "FTE" | "VENDOR";
export type RequestStatus = "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED" | "CHANGES_REQUESTED" | "CANCELLED";
export type ApprovalAction = "SUBMIT" | "APPROVE" | "REJECT" | "REQUEST_CHANGES" | "CANCEL" | "RESUBMIT";
export type PositionStatus = "OPEN" | "FILLED" | "CANCELLED";
export type PostingStatus = "PUBLISHED" | "PAUSED" | "CLOSED";
export type ApplicationStatus = "NEW" | "SHORTLISTED" | "REJECTED" | "HIRED";
export type EngagementStatus = "AWAITING_DISPATCH" | "MESSAGE_SENT" | "CONFIRMED" | "DECLINED" | "CANCELLED";
export type EngagementLifecycle = "UPCOMING" | "ACTIVE" | "ENDED" | "CANCELLED";
export type FitBadge = "NO_DATA" | "WITHIN_PLAN" | "EXCEEDS_PLAN" | "WITHIN_BUDGET" | "OVER_BUDGET";

export interface ApprovalEvent {
  id: number;
  actor_id: number;
  actor_name: string | null;
  action: ApprovalAction;
  note: string | null;
  at: string;
}

export interface PositionSummary {
  id: number;
  status: PositionStatus;
  filled_worker_id: number | null;
  filled_worker_name: string | null;
  filled_on: string | null;
}

export interface HiringRequest {
  id: number;
  team_id: number;
  team_name: string | null;
  cycle_id: number;
  type: RequestType;
  role_title: string;
  grade: string | null;
  quantity: number;
  annual_salary_cents: number | null;
  hourly_rate_cents: number | null;
  hours_per_month: number | null;
  vendor_company_id: number | null;
  vendor_company_name: string | null;
  target_start_date: string;
  end_date: string | null;
  justification: string;
  source: "MANUAL" | "FORECAST_SUGGESTION";
  status: RequestStatus;
  decided_by: number | null;
  decision_note: string | null;
  created_by: number;
  created_by_name: string | null;
  created_at: string;
  submitted_at: string | null;
  approved_at: string | null;
  posting_slug: string | null;
  posting_status: string | null;
  vendor_engagement_id: number | null;
  vendor_engagement_status: string | null;
  contract_value_cents: number | null;
  plan_fit: FitBadge | null;
  budget_fit: FitBadge | null;
}

export interface RequestDetail extends HiringRequest {
  approval_events: ApprovalEvent[];
  positions: PositionSummary[];
  vendor_messages: VendorMessage[];
}

export interface JobPosting {
  id: number;
  request_id: number;
  slug: string;
  title: string;
  description: string;
  location: string;
  openings: number;
  status: PostingStatus;
  published_at: string;
  applicant_count: number;
  open_position_count: number;
}

export interface PublicPostingListItem {
  slug: string;
  title: string;
  location: string;
  openings: number;
  published_at: string;
}

export interface PublicPostingDetail extends PublicPostingListItem {
  description: string;
}

export interface Application {
  id: number;
  posting_id: number;
  posting_title: string | null;
  name: string;
  email: string;
  phone: string | null;
  profile_url: string | null;
  note: string | null;
  status: ApplicationStatus;
  created_at: string;
  suggested_annual_salary_cents: number | null;
}

export interface VendorCompany {
  id: number;
  name: string;
  contact_name: string;
  contact_email: string;
}

export interface VendorMessage {
  id: number;
  engagement_id: number;
  to_email: string;
  subject: string;
  body: string;
  status: "SENT" | "REPLIED";
  sent_by: number;
  sent_at: string;
}

export interface VendorEngagement {
  id: number;
  request_id: number;
  team_id: number;
  team_name: string | null;
  role_title: string | null;
  vendor_company_id: number;
  vendor_company_name: string | null;
  vendor_contact_email: string | null;
  headcount: number;
  hourly_rate_cents: number;
  hours_per_month: number;
  start_date: string;
  end_date: string | null;
  status: EngagementStatus;
  lifecycle: EngagementLifecycle | null;
  contract_value_cents: number | null;
  messages: VendorMessage[];
}
