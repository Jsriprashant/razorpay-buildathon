# Flow matrix

Every UI action mapped to route → endpoint → tables written → state change →
notification → UI update. Grouped by feature area. This pass also confirms
there is no orphan button (every action below is reachable from the UI and
wired to a real endpoint) and no orphan endpoint (every endpoint below is
called from at least one UI action, except the public careers API which is
called by the public site, and `GET` endpoints, which are read paths, not
actions).

## Auth

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| Pick a demo user | `/login` | `POST /auth/login` | none (session cookie only) | — | redirect to `/home` |
| Log out | any page, Topbar | `POST /auth/logout` | none | — | redirect to `/login` |

## Roster

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View roster | `/roster` | `GET /roster` | — | — | worker table |
| Add a person to fill an open position | `/roster` | `POST /roster/workers` | `worker`, `position` (status→FILLED) | — | worker appears, position count drops |
| Edit a worker | `/roster` | `PATCH /roster/workers/{id}` | `worker` | — | row updates |
| Mark a worker exited | `/roster` | `POST /roster/workers/{id}/exit` | `worker` (termination_date, is_active) | — | worker moves to inactive |

## Reconciliation

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View recon | `/recon` | `GET /recon` | — | — | 3 tabs render |
| Resolve one flagged item | `/recon` | `POST /recon/resolve` | `recon_resolution` | — | item marked resolved, count drops |
| Bulk resolve | `/recon` | `POST /recon/resolve/bulk` | `recon_resolution` (many) | — | items marked resolved |
| Link an unplanned hire to a position | `/recon` | `POST /recon/link-position` | `worker.position_id` | — | unplanned hire moves into requested-vs-actual |

## Plan & forecast

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View/edit plan | `/plan` | `GET /plan`, `PUT /plan` | `plan_line` | — | grid updates; `has_plan` flips true |
| View forecast | `/forecast` | `GET /forecast` | — | — | chart + suggestions render |
| Run a what-if | `/forecast` | `POST /forecast/what-if` | — (read-only simulation) | — | comparison chart renders |
| "Request this" on a suggestion | `/forecast` → `/requests/new` | (prefill only, then `POST /requests`) | see Requests below | see Requests below | new request opens prefilled |

## Requests (manager side)

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View requests | `/requests` | `GET /requests` | — | — | list renders |
| Create draft | `/requests/new` | `POST /requests` | `hiring_request` | — | redirect to detail, status DRAFT |
| Edit draft | `/requests/:id` | `PATCH /requests/{id}` | `hiring_request` | — | fields update |
| Submit | `/requests/:id` | `POST /requests/{id}/submit` | `hiring_request` (status→SUBMITTED), `approval_event` | → HR: "New hiring request awaiting review" → `/hr/inbox` | status badge updates |
| Resubmit after changes requested | `/requests/:id` | `POST /requests/{id}/resubmit` | `hiring_request` (status→SUBMITTED), `approval_event` | → HR: "New hiring request awaiting review" → `/hr/inbox` | status badge updates |
| Cancel (draft/submitted) | `/requests/:id` | `POST /requests/{id}/cancel` | `hiring_request` (status→CANCELLED), `approval_event` | → HR: "Hiring request cancelled" → `/hr/inbox` | status badge updates |

## HR approvals

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View inbox | `/hr/inbox` | `GET /hr/inbox` | — | — | list renders |
| Approve (FTE) | `/hr/inbox` | `POST /hr/requests/{id}/approve` | `hiring_request`, `approval_event`, `position` (N rows), `job_posting` | → requester: "Your request … was approved" → `/requests/{id}`; → requester: "Job posting published" → `/careers/{slug}` | request approved, posting live |
| Approve (vendor) | `/hr/inbox` | `POST /hr/requests/{id}/approve` | `hiring_request`, `approval_event`, `vendor_engagement` | → requester: "Your request … was approved"; → HR: "New vendor engagement awaiting dispatch" → `/hr/vendor-dispatch` | request approved, engagement queued |
| Reject | `/hr/inbox` | `POST /hr/requests/{id}/reject` | `hiring_request` (status→REJECTED), `approval_event` | → requester: "Your request … was rejected" → `/requests/{id}` | status badge updates |
| Request changes | `/hr/inbox` | `POST /hr/requests/{id}/request-changes` | `hiring_request` (status→CHANGES_REQUESTED), `approval_event` | → requester: "Changes were requested…" → `/requests/{id}` | status badge updates |
| Cancel an approved request | `/hr/inbox` | `POST /hr/requests/{id}/cancel` | `hiring_request` (status→CANCELLED) | → requester: "Your approved request … was cancelled by HR" → `/requests/{id}` | status badge updates |
| Bulk approve | `/hr/inbox` | `POST /hr/requests/bulk-approve` | same as single approve, per request | same as single approve, per request | multiple rows update |

## Postings & public careers

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View postings | `/hr/postings` | `GET /hr/postings` | — | — | list renders |
| Pause/close/republish a posting | `/hr/postings` | `PATCH /hr/postings/{id}` | `job_posting` | — | status badge updates |
| Browse public jobs | `/careers` | `GET /public/postings` | — | — | public list (no salary/cost/IDs) |
| View a public job | `/careers/:slug` | `GET /public/postings/{slug}` | — | — | public detail |
| Apply | `/careers/:slug` | `POST /public/postings/{slug}/apply` | `application` | → HR: "New application for …" → `/hr/applications` | success state |

## Applications

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View applications | `/hr/applications` | `GET /applications` | — | — | kanban renders |
| Shortlist/reject | `/hr/applications` | `POST /applications/{id}/status` | `application` | — | card moves column |
| Hire | `/hr/applications` | `POST /applications/{id}/hire` | `worker`, `position` (status→FILLED), `application` (status→HIRED), `job_posting` (status→CLOSED if last opening) | → requester: "{name} was hired for {role}" → `/roster` | worker appears in roster, application marked hired |

## Vendors

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View vendor companies | `/hr/vendors` | `GET /hr/vendor-companies` | — | — | list renders |
| Add a vendor company | `/hr/vendors` | `POST /hr/vendor-companies` | `vendor_company` | — | list updates |
| View dispatch queue | `/hr/vendor-dispatch` | `GET /hr/vendor-dispatch` | — | — | list renders |
| Preview default message | `/hr/vendor-dispatch` | `GET /hr/engagements/{id}/default-message` | — | — | message preview |
| Send (simulated) dispatch | `/hr/vendor-dispatch` | `POST /hr/engagements/{id}/send` | `vendor_message`, `vendor_engagement` (status→MESSAGE_SENT) | → requester: "Vendor message sent to …" → `/vendors` | status badge updates |
| Confirm engagement | `/hr/vendor-dispatch` | `POST /hr/engagements/{id}/confirm` | `vendor_engagement` (status→CONFIRMED) | → requester: "Vendor engagement confirmed…" → `/vendors` | status badge updates |
| Decline engagement | `/hr/vendor-dispatch` | `POST /hr/engagements/{id}/decline` | `vendor_engagement` (status→DECLINED) | → requester: "Vendor declined the engagement…" → `/vendors` | status badge updates |
| View my team's engagements | `/vendors` | `GET /vendors` | — | — | list renders |
| (background) engagement expiring within 30 days | any page load | `ensure_expiry_notifications` (internal, not a route) | — | → requester and → HR: "Vendor engagement … expires on …" → `/vendors` / `/hr/vendor-dispatch` (deduplicated) | bell badge increments |

## Cycles, rollover, history & demo

| UI action | Route | Endpoint | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| (auto) rollover check | any manager page load | `GET /cycles/current` | — | — | shows modal/banner if `needs_rollover` |
| Start fresh cycle | rollover modal/banner | `POST /cycles/rollover` | `snapshot_worker` (N rows per closed month), `cycle_summary` (1 row per closed month), `cycle` (closes old, opens new; repeats per month behind) | → every manager on the team: "A new cycle started: {Month Year}…" → `/home` | modal closes, all data refetches |
| Remind me later | rollover modal | (none — `localStorage` only) | — | — | modal replaced by persistent banner |
| View history | `/history` | `GET /cycles` | — | — | closed-cycle table renders |
| View one cycle | (not yet linked from UI; available for future drill-down) | `GET /cycles/{id}` | — | — | — |
| Advance to next month | Demo panel | `POST /demo/advance-month` | `setting.demo_today` | — | demo panel shows new simulated date; broad refetch |
| Reset demo data | Demo panel | `POST /demo/reset` | drops & recreates all tables, reseeds | — | full page reload to `/home` |

## Home

| UI action | Route | Endpoint(s) | Tables written | Notification | UI update |
|---|---|---|---|---|---|
| View dashboard | `/home` | `GET /kpis` | — | — | KPI cards + variance summary |
| Checklist step: Set your plan | `/home` → `/plan` | see Plan above | — | — | step ticks once `has_plan` is true |
| Checklist step: Review recon | `/home` → `/recon` | see Recon above | — | — | step ticks once `unresolved_flag_count` is 0 |
| Checklist step: Review forecast | `/home` → `/forecast` | see Forecast above | — | — | step ticks once no suggestion is flagged urgent |
| Checklist step: Raise requests | `/home` → `/requests/new` | see Requests above | — | — | step ticks once a request exists in the current cycle |

## Notifications (cross-cutting)

| UI action | Route | Endpoint | Tables written | UI update |
|---|---|---|---|---|
| View notifications | bell, any page | `GET /notifications` | — | dropdown renders, unread badge |
| Mark one read (click item) | bell dropdown | `POST /notifications/read` (`notification_id`) | `notification.read_at` | item un-bolds, badge decrements, navigates to `link` |
| Mark all read | bell dropdown | `POST /notifications/read` (no id) | `notification.read_at` (all unread) | badge clears |

## Settings

| UI action | Route | Endpoint | Tables written | UI update |
|---|---|---|---|---|
| View settings | `/hr/settings` | `GET /settings` | — | form renders |
| Update settings | `/hr/settings` | `PUT /settings` (HR only) | `setting` | form updates |

## Orphan check

- Every endpoint above is reached from at least one UI element, except
  `GET /cycles/{id}` (kept for API completeness / a future drill-down from
  `/history`, but no current button links to it — flagged here rather than
  hidden) and the public careers endpoints (called by the public site, not
  the authenticated app).
- No button in the app calls an endpoint that doesn't exist — every `onClick`
  → mutation pair in `frontend/src/pages` and `frontend/src/components`
  targets one of the routes above.
