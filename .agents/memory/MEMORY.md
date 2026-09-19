# Memory Index

- [uv-managed Python venv volatility](uv-python-venv.md) — .pythonlibs can vanish between calls; always invoke via `uv run`, not a cached venv path.
- [Vite react-ts scaffold TS strictness](vite-react-ts-strictness.md) — default tsconfig needs a tweak, and hand-rolled shadcn-style components need explicit type imports.
- [SQLAlchemy circular FK pattern](sqlalchemy-circular-fk.md) — how to model mutually-referencing tables (team↔worker, worker↔position) without a hard cycle.
- [Postgres reset lock contention](postgres-reset-lock-contention.md) — a mid-request drop_all/reseed must close the request's own DB session first or it can hang on lock contention.
- [Date-only arithmetic/display timezone bug](date-arithmetic-timezone-bug.md) — never let `new Date("YYYY-MM-DD")` flow into local-time getters/formatters; use `parseISO` or manual UTC math instead.
