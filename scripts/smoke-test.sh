#!/usr/bin/env bash
# Smoke-test a running API (local or deployed). Fails fast on any error.
set -euo pipefail

BASE="${1:-http://localhost:8000}"
echo "Smoking $BASE"

curl -fsS "$BASE/health" | grep -q '"status":"ok"' && echo "OK  /health"

ID=$(curl -fsS -X POST "$BASE/api/tasks" \
  -H 'Content-Type: application/json' \
  -d '{"title":"smoke test"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "OK  POST /api/tasks -> $ID"

curl -fsS "$BASE/api/tasks/$ID" | grep -q smoke && echo "OK  GET /api/tasks/{id}"
curl -fsS -X PATCH "$BASE/api/tasks/$ID" \
  -H 'Content-Type: application/json' -d '{"done":true}' | grep -q '"done":true' \
  && echo "OK  PATCH /api/tasks/{id}"
curl -fsS -o /dev/null -w "%{http_code}" -X DELETE "$BASE/api/tasks/$ID" | grep -q 204 \
  && echo "OK  DELETE /api/tasks/{id} -> 204"
curl -fsS "$BASE/metrics" | grep -q tasks_created_total && echo "OK  /metrics"

echo "All smoke tests passed."
