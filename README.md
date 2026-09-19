# HeadcountHQ

A Workday-replacement app for headcount, hiring requests, vendor contracts and
workforce forecasting — explicitly **not** payroll or benefits. Managers plan
and request headcount, HR approves and dispatches it, and everyone sees the
same numbers reconciled against actuals every month.

## Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0, PostgreSQL
  (Replit's built-in database). Managed with `uv`.
- **Frontend**: React + Vite + TypeScript + Tailwind + a hand-rolled
  shadcn-style UI kit + TanStack Query. Lives in `frontend/`, builds to
  `frontend/dist`.
- **Serving**: one process, one port. FastAPI serves `/api/v1/*` and the built
  frontend (SPA fallback for client-side routes). There is no separate
  frontend dev server.
- **Sessions**: signed cookie (`SESSION_SECRET`), demo user picker instead of
  real passwords — this is a demo/prototype, not a production identity
  system.

## Running it

The configured "Start application" workflow does everything in one command:
installs frontend deps, builds the frontend, initializes the database,
seeds it if empty, and starts the API/SPA server on port 5000. Just hit Run.

To reseed by hand from a shell:

```
uv run python -m app.scripts.init_db      # create tables if missing
uv run python -m app.scripts.seed         # seed if empty (no-op otherwise)
uv run python -m app.scripts.seed_reset   # drop everything and reseed fresh
```

To run the test suite:

```
uv run pytest
```

## Demo script (under 15 minutes)

The seed data starts you mid-fiscal-year with history already in place, so
you can see every feature without setting anything up first.

1. **Sign in** at `/login` as **Priya Sharma (Manager)** — no password, this
   is a demo picker.
2. **Home**: KPI cards (headcount, budget variance, open positions, vendor
   spend) plus the "Get this cycle started" checklist. Its steps auto-tick
   from real data (unresolved recon flags, outstanding urgent forecast
   suggestions, whether a request exists in the current cycle) — try
   resolving a recon flag and come back to see a step tick off.
3. **Roster** → see the team's active/former workers; try "Add a person to
   fill" against an open position.
4. **Recon**: three tabs — changes since last period (new hires / exits /
   grade or manager changes), requested-vs-actual (which approved positions
   are filled, open, or overdue), and plan-vs-actual (budget/headcount
   variance by month). Resolve a flagged item and see the unresolved count
   drop.
5. **Forecast**: projected headcount/cost with and without the suggested
   actions; click "Request this" on a suggestion to prefill a new hiring
   request.
6. **Requests**: submit a new FTE or vendor request, or open an existing
   DRAFT and submit it.
7. **Sign out, sign in as Jordan Blake (HR)**. Open **HR → Inbox**, approve
   the request you just submitted — for FTE it publishes a careers posting
   automatically; for vendor it creates an engagement.
8. If FTE: **HR → Postings** shows the new posting; visit `/careers` in a
   new tab (works signed out) and submit a public application, then
   **HR → Applications** → Hire the applicant, which creates the worker and
   closes the posting once every opening is filled.
9. If vendor: **HR → Vendor dispatch** → send the (simulated) dispatch
   message, then confirm the engagement.
10. **Notification bell** (top right, any role): every event above — request
    submitted, approved/rejected, posting published, hired, engagement
    confirmed — shows up here, links to the right page, and clears on read.
11. **Demo panel** (top right, any role): "Advance to next month" moves the
    simulated clock forward without closing the cycle by itself. Reload —
    a manager sees a "new month started" modal (or, if dismissed, a
    persistent banner). "Start fresh cycle" snapshots the roster, records
    that month's plan-vs-actual in `cycle_summary`, and opens the next
    month; draft/submitted/approved requests carry over unchanged. Visit
    `/history` to see it recorded.
12. "Reset demo data" restores the original seed state at any point.

## Code layout

- `app/models` — SQLAlchemy models, one file per domain area.
- `app/schemas` — Pydantic request/response schemas.
- `app/routers` — thin FastAPI routers; business logic stays in `app/services`.
- `app/services` — business logic, including `clock.py` (`get_today()`, the
  only source of "today" in the app — see ASSUMPTIONS.md).
- `app/calc` — pure math (money rounding, date/proration helpers), covered by
  fast pytest golden tests in `app/tests`.
- `app/scripts` — `init_db`, `seed`, `seed_reset` (run via `python -m`).
- `frontend/src` — `components/ui` (primitives), `components/layout` (app
  shell, notification bell, demo panel, rollover gate), `pages`, `lib` (API
  client, auth context, money formatting).
- `docs/flow-matrix.md` — every UI action mapped to its route, endpoint,
  tables written, notification, and UI update.
- `ASSUMPTIONS.md` — every unspecified-detail decision made while building
  this.

## Rules that matter across the whole project

- **Money**: always integer cents (`*_cents` columns). Rounding goes through
  `app/calc/money.py`'s `round_half_up_cents` (ROUND_HALF_UP) — never
  Python's built-in `round()`.
- **Dates**: "today" is always `app.services.clock.get_today(db)`. Nothing
  else calls `date.today()` — this is what makes the demo clock work.
- **Settings**: anything configurable lives in the `setting` table, never
  hardcoded.
- **Auth/scoping**: every route depends on `current_user` plus a role guard;
  team-scoped data additionally calls `assert_team_scope`.
- **No mocked data / no dead buttons**: seed data is deterministic and
  labelled DEMO; anything not yet built is an explicit empty state with a
  next action, not a stub that pretends to work.
