# azure-container-apps-api

A Task REST API (FastAPI) packaged as a hardened Docker image and deployed to
**Azure Container Apps** with **Bicep** infrastructure-as-code and a
**GitHub Actions** CI/CD pipeline (test → build → Trivy scan → Docker Hub push
→ manual Azure deploy).

Part of a daily DevOps project series — each project practices a different
platform. Previous: AWS EC2/Terraform/Ansible (`mokku-journey-devops`),
AWS Lambda serverless (`aws-lambda-serverless-api`).

## Quickstart (local)

```bash
./scripts/run-local.sh        # venv + uvicorn on http://localhost:8000
./scripts/smoke-test.sh       # exercises every endpoint; try also:
./scripts/smoke-test.sh https://<your-fqdn>   # against a deployed app
python -m pytest tests/ -q    # 16 unit tests, no Azure needed
```

## Docker

```bash
docker build -t tasks-api:local .
docker run --rm -p 8000:8000 -e PORT=8000 tasks-api:local
curl -s localhost:8000/health
```

The image is multi-stage (`python:3.12-slim-bookworm`), runs as non-root
`appuser`, ships no dev/test files (see `.dockerignore`), and has a
`HEALTHCHECK` on `/health`.

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe → `{"status":"ok"}` |
| GET | `/ready` | Readiness probe → `{"status":"ready","version":"0.1.0"}` |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/tasks` | Create → `201` (`{"title":"..."}`) |
| GET | `/api/tasks` | List (max 100) |
| GET | `/api/tasks/{id}` | Get one → `404` if missing |
| PATCH | `/api/tasks/{id}` | Partial update (`title`, `done`) |
| DELETE | `/api/tasks/{id}` | Delete → `204`, `404` if missing |

## CI/CD

- **`ci.yml`** (on push to `main` + PRs): pytest → Docker build → Trivy image
  scan (**fails on HIGH/CRITICAL**) → push `:latest` + `:sha-<sha>` to Docker Hub.
  The push is skipped with a warning until the repo secrets
  `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` are set — the pipeline never claims
  a push it did not do.
- **`cd.yml`** (manual `workflow_dispatch` only): `az containerapp update` to the
  chosen image tag + smoke test. Needs the `AZURE_CREDENTIALS` repo secret
  (service-principal JSON, contributor on the resource group).

See [docs/architecture.md](docs/architecture.md) for the full design and
[infra/bicep/README.md](infra/bicep/README.md) for deployment steps.

## Observability

- Probes: liveness `/health`, readiness `/ready` (also the Docker HEALTHCHECK).
- Autoscaling: KEDA HTTP scaler, 50 concurrent requests/replica, 0–3 replicas
  (scale-to-zero on idle).
- Ready-made KQL queries in [monitoring/log-analytics-queries.kql](monitoring/log-analytics-queries.kql):
  log tail, error rate, p50/p95 latency, scaling events, probe failures.

## Project layout

```
├── app/                  # FastAPI service (main.py, models.py)
├── tests/                # 16 pytest tests (no cloud credentials needed)
├── Dockerfile            # multi-stage, pinned base, non-root, HEALTHCHECK
├── infra/bicep/          # main.bicep + .bicepparam — env, app, probes, scale
├── monitoring/           # Log Analytics KQL queries
├── scripts/              # run-local.sh, smoke-test.sh
├── docs/                 # architecture.md
└── .github/workflows/    # ci.yml (test→scan→push), cd.yml (manual deploy)
```

## Notes & limits (honest)

- Task storage is **in-memory** — fine for a stateless-container demo, not for
  production (see architecture.md "Production hardening").
- Azure resources are **not** provisioned by CI; deployment is a deliberate
  manual step (cost rule: nothing paid runs without approval).
- No live deployment exists yet — the deploy steps are documented and ready.
