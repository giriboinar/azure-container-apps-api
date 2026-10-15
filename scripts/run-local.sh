#!/usr/bin/env bash
# Run the API locally (no Docker needed).
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv 2>/dev/null || true
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

PORT="${PORT:-8000}"
echo "Starting Task API on http://localhost:${PORT}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
