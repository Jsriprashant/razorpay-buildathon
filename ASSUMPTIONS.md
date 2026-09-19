# Assumptions

Every place the spec left a detail unspecified, and the decision made,
across all three build tasks (foundation, requests/HR/vendor, and this
rollover/notifications/polish pass).

## Auth & sessions

- Login is a demo user picker (`GET /auth/demo-users`, `POST /auth/login`
  with just a `user_id`) — no passwords. This is explicitly a demo/prototype
  identity system standing in for real SSO.
- Sessions are a signed cookie via Starlette `SessionMiddleware`, keyed off
  `SESSION_SECRET` from Replit's secrets. No server-side session store.

## Money & dates

- All money is integer cents; rounding is always `ROUND_HALF_UP` via
  `app/calc/money.py`, never Python's `round()` (which uses banker's
  rounding and would silently drift from the spec's golden values).
- "Today" is never `date.today()`. Everything reads
  `app.services.clock.get_today(db)`, which returns the `demo_today` setting
  when set, else the real date. This is what lets the demo clock and
  rollover mechanics work without a real scheduler.

## Cycles & rollover

- A cycle's `month_start` is the first of the month; "the current cycle" for
  a team is its most recent OPEN cycle.
- Rollover is triggered client-side, not by a background job: any manager
  page load (via `RolloverGate`, mounted once in the app shell) checks
  `GET /cycles/current`; if `needs_rollover` is true it prompts. This keeps
  the whole system driven by `get_today()` and avoids needing a cron.
- Rollover is a single idempotent transaction that can close more than one
  month at once if the demo clock was advanced multiple times before anyone
  rolled over — each month in the gap gets its own snapshot, cycle_summary,
  and close/reopen step, in order, inside one request.
- Rollover **never repoints `cycle_id`** on existing DRAFT/SUBMITTED/APPROVED
  hiring requests — "carried over unchanged" is taken literally, so a
  request keeps referencing the cycle it was created in even after that
  cycle closes. Its data and workflow state are untouched either way.
- `POST /cycles/rollover` requires manager or HR; the GET endpoints
  (`/cycles/current`, `/cycles`, `/cycles/{id}`) are open to any
  authenticated user so HR/Finance can read history too.
- "Remind me later" is a UI-only dismissal, stored in `localStorage` keyed
  by the cycle id being rolled over — there's no server field for this
  because it's a personal UI preference, not shared business data, and it
  naturally resets (a new cycle needs a fresh reminder) without any cleanup.

## Demo panel

- "Advance to next month" and "Reset demo data" are available to **all**
  roles (Manager/HR/Finance viewer), not gated to HR — there's no real
  production data at stake in a demo app, and letting any role explore the
  clock keeps the demo self-serve regardless of which user picked it.
- "Reset demo data" drops and recreates every table, then reseeds
  deterministically and clears `demo_today`. It closes its own request's DB
  session before calling the reset script and opens a fresh session
  afterward — a `drop_all`/`create_all` under an open transaction on the
  same connection will otherwise block on lock contention.
- Advancing the clock does **not** close the current cycle by itself; it
  only changes what "today" is. The next manager page load is what surfaces
  the rollover prompt. This mirrors what would happen for a real user simply
  living through a month turning over.

## Notifications

- Notifications are a flat per-user inbox (`GET /notifications`,
  `POST /notifications/read` with an optional `notification_id`, omitted =
  mark all read). No categories, filtering, or push delivery — this is a
  demo, so "email" and "SSO" are explicitly simulated (see the banner on
  `/login`).
- `notify_role(db, Role.HR, ...)` fans out to every HR user individually
  rather than modeling a shared "HR inbox" notification row, so per-user
  read state stays correct even though multiple HR users would all see it.
- Vendor engagement expiry notifications (`ensure_expiry_notifications`, 30
  days out) are deduplicated by checking `notification_exists` for the same
  user+message before writing, and are computed on relevant page loads
  rather than a scheduled job, consistent with rollover's client-triggered
  approach — there is no background worker in this deployment.
- The full set of notification triggers (see `docs/flow-matrix.md` for the
  authoritative table): request submitted/resubmitted → HR; request
  cancelled by manager → HR; request approved/rejected/changes-requested →
  requester; FTE approval → requester (posting published); vendor approval →
  HR (engagement awaiting dispatch); vendor message sent/confirmed/declined
  → requester; vendor engagement expiring soon → requester and HR;
  application hired → requester; new public application → HR; cycle
  rollover → every manager on the team.

## Plan & the "no plan yet" nudge

- `PlanOut.has_plan` is true iff at least one `PlanLine` row exists for the
  team — a plan with all-zero values still counts as "has a plan" (the team
  made a deliberate call), only the complete absence of rows triggers the
  nudge.
- The "Set your plan" step is folded into the same Home checklist as the
  cycle's 3 steps (recon/forecast/requests), appearing first when there's no
  plan yet, rather than being a separate banner — the spec calls it "the
  extra first step," implying one checklist, not two competing prompts.
- Checklist steps auto-tick from data, never from a "did the user visit this
  page" flag: recon is done when `unresolved_flag_count` is 0; forecast is
  done when no remaining suggestion is flagged urgent; "raise requests" is
  done when at least one hiring request exists whose `cycle_id` matches the
  team's current open cycle. This keeps the checklist honest even if pages
  are visited out of order or the tab is reloaded.

## Scoping & security

- Every route depends on `current_user`; team-scoped resources additionally
  call `assert_team_scope` so a manager can only see/act on their own team's
  data (404, not 403, when the id exists but belongs to another team — this
  avoids confirming the id's existence to an unauthorized caller).
- Public careers endpoints (`/public/postings*`) never return salary, cost,
  internal IDs, or anything beyond slug/title/description/location/openings/
  published_at.
- Illegal state transitions (e.g. approving a DRAFT request, confirming an
  engagement that was never dispatched) return 409, not 400 — the request is
  well-formed, the current state just doesn't allow it.
