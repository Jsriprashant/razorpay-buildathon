#!/usr/bin/env bash
set -euo pipefail

# Keep post-merge setup deterministic and non-interactive. The running workflow
# is reconciled separately after this script completes.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

cd frontend
npm install --no-audit --no-fund
npm run build
cd ..

uv run python -m app.scripts.init_db
uv run python -m app.scripts.seed