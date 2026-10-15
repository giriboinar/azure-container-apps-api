# Architecture

## Request flow

```
                    ┌─────────────────────────────────────────────┐
                    │           Azure Container Apps              │
                    │              environment                    │
Client ──HTTPS──▶   │  ┌──────────────────────────────────────┐   │
                    │  │  Container App: tasks-api            │   │
                    │  │  (external ingress, port 8000)       │   │
                    │  │                                      │   │
                    │  │  ┌──────────────────────────────┐    │   │
                    │  │  │ tasks-api container          │    │   │
                    │  │  │  uvicorn + FastAPI          │    │   │
                    │  │  │  /health /ready /metrics    │    │   │
                    │  │  │  /api/tasks (in-memory)     │    │   │
                    │  │  │  liveness + readiness       │    │   │
                    │  │  │  probes, HTTP autoscaling   │    │   │
                    │  │  └──────────────────────────────┘    │   │
                    │  └──────────────────────────────────────┘   │
                    │                    │                        │
                    │                    ▼                        │
                    │           Log Analytics workspace           │
                    │   (ContainerAppConsoleLogs + SystemLogs)    │
                    └─────────────────────────────────────────────┘
```

## Components

| Layer | Choice | Why |
|---|---|---|
| App | FastAPI (Python 3.12) | Async, typed, auto-docs; matches the user's Python/DevOps stack |
| Container | Multi-stage Docker, `python:3.12-slim-bookworm`, non-root `appuser` | Small attack surface, reproducible, least privilege |
| Platform | Azure Container Apps (consumption) | Serverless containers: scale-to-zero, KEDA autoscaling, no cluster to manage |
| IaC | Bicep (`infra/bicep/`) | Azure-native, concise; the whole environment is one `az deployment` |
| CI | GitHub Actions (`ci.yml`) | pytest → Docker build → Trivy scan (gate) → Docker Hub push |
| CD | GitHub Actions (`cd.yml`, manual dispatch) | Image swap via `az containerapp update` + smoke test; human-gated |
| Observability | `/metrics` (Prometheus) + Log Analytics KQL | Probes keep replicas healthy; KQL queries answer "what broke?" |

## Scaling

- KEDA HTTP scaler: target 50 concurrent requests per replica, 0–3 replicas.
- `minReplicas: 0` = scale-to-zero: no traffic → no running replicas → no compute
  charge (consumption plan). First request after idle pays a cold start (~seconds).

## Security notes

- Non-root container user; no secrets baked into the image (config via env vars).
- Trivy gates the pipeline on HIGH/CRITICAL image vulnerabilities.
- Docker Hub push needs repo secrets; Azure deploy needs a scoped service
  principal (`AZURE_CREDENTIALS`) — neither lives in the repo.
- Ingress is HTTPS-terminated by the platform; the app itself only listens on
  the container port.

## Production hardening (deliberately out of scope)

- Replace the in-memory store with Azure Cosmos DB or PostgreSQL (stateless
  replicas must not own state).
- Private ingress + Azure Front Door / API Management in front.
- Managed identity instead of service-principal secret for deploys.
- Azure Monitor alerts on the KQL queries in `monitoring/`.
