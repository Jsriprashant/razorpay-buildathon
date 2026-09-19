---
name: uv-managed Python venv volatility
description: Why a direct .pythonlibs/bin/python3 call can fail with "No module named X" even right after a successful install, and how to avoid it.
---

`uv` manages the project's Python venv at `.pythonlibs/`. That directory is
not stable across shell invocations in this environment — a later `uv run
...` call (including ones triggered indirectly, e.g. by a workflow restart)
can remove and recreate `.pythonlibs` from scratch based on `pyproject.toml`/
`uv.lock`, even though the packages were installed moments earlier.

**Why:** a `.pythonlibs/bin/python3 -m pytest` that worked once failed later
in the same session with `No module named pytest`, purely because an
intervening `uv run` call had rebuilt the venv.

**How to apply:** never cache or hardcode the `.pythonlibs/bin/...`
interpreter path across steps. Always invoke Python tooling via `uv run
<command>` (e.g. `uv run pytest`, `uv run python -m app.scripts.init_db`,
`uv run uvicorn ...`) so `uv` resolves/recreates the venv consistently right
before running.
