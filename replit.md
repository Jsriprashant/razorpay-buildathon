# CONTINUUM

A Workday-replacement app for headcount, hiring requests, vendor contracts and
forecasting (explicitly NOT payroll/benefits). Built as a single Replit web
service split into a Python backend and a React frontend.

## Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 (typed
  models), psycopg v3, PostgreSQL (Replit's built-in database via
  `DATABASE_URL`). Managed with `uv` (see `pyproject.toml`/`uv.lock`).
- **Frontend**: React + Vite + TypeScript + Tailwind (v3) + a hand-rolled
  shadcn-style UI kit + TanStack Query + Recharts. Lives in `frontend/`,
  builds to `frontend/dist`.
- **Serving**: single port. FastAPI serves `/api/v1/*` and mounts the built
  frontend with an SPA fallback for every other route. There is no separate
  frontend dev server — `npm run build` then `uvicorn` handles both dev and
  deployment.
- **Sessions**: Starlette `SessionMiddleware` (signed cookie, `SESSION_SECRET`
  from Replit secrets). Login is a demo user picker (no real passwords).

## Code layout

- `app/models` — SQLAlchemy 2.0 models (one file per domain area).
- `app/schemas` — Pydantic request/response schemas.
- `app/routers` — thin FastAPI routers; all business logic stays in services.
- `app/services` — business logic, including `clock.py` (`get_today()`).
- `app/calc` — pure math only (money rounding, date/proration helpers). No DB
  access, so it's covered by fast pytest golden tests in `app/tests`.
- `app/scripts` — `init_db`, `seed`, `seed_reset` (all run via `python -m`).
- `frontend/src` — `components/ui` (primitives), `components/layout` (app
  shell), `pages`, `lib` (api client, auth context, money formatting).

## Rules that matter across the whole project

- **Money**: always integer cents (`*_cents` columns). Never float, never
  Python's `round()` (banker's rounding). All rounding goes through
  `app/calc/money.py`'s `round_half_up_cents` (ROUND_HALF_UP).
- **Dates**: "today" is always `app.services.clock.get_today(db)`, which
  reads the `demo_today` setting and falls back to the real date. Nothing
  else should call `date.today()`.
- **Settings**: anything configurable lives in the `setting` table
  (`app/services/settings_service.py`), never hardcoded.
- **Auth/scoping**: every route depends on `current_user` (see `app/deps.py`)
  plus a role guard (`require_hr`, `require_manager`, ...). Team-scoped data
  additionally calls `assert_team_scope`.
- **No mocked data / no dead buttons**: seed data is deterministic and
  labelled DEMO; anything not yet built is an explicit "coming soon" empty
  state, not a stub that pretends to work.

## Known deliberate substitution

The frontend UI kit is a small hand-rolled set of shadcn-style primitives
(`frontend/src/components/ui/*`) built with Radix + `class-variance-authority`
+ `tailwind-merge`, rather than running the `shadcn` CLI. This avoids
interactive/network flakiness in the build environment; the resulting
components follow the same conventions shadcn generates (so `npx shadcn add`
can still be used later if needed).

## Project structure

This build is split into 4 project tasks: foundation (this one — schema,
seed, auth, layout, calc) unblocks headcount/recon/plan/forecast and
requests/HR-approvals/vendor-dispatch, which both unblock rollover/
notifications/history/polish. See `.local/tasks/*.md` for each task's spec.
