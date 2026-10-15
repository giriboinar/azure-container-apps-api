"""Task API — FastAPI service designed to run on Azure Container Apps.

Endpoints:
    GET  /health          Liveness probe (used by the container liveness probe)
    GET  /ready           Readiness probe (used by the container readiness probe)
    GET  /metrics         Prometheus exposition format
    POST /api/tasks       Create a task            -> 201
    GET  /api/tasks       List tasks (max 100)
    GET  /api/tasks/{id}  Get one task             -> 404 if missing
    PATCH /api/tasks/{id} Partially update a task  -> 404 if missing
    DELETE /api/tasks/{id} Delete a task           -> 204, 404 if missing

Storage is in-memory (thread-safe). That is deliberate for a stateless
container demo: Container Apps can scale to zero and reschedule replicas at
any time, so durable state belongs in a managed store (Azure Cosmos DB or
PostgreSQL) — see README "Production hardening".
"""

import threading
import uuid

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from app.models import Task, TaskCreate, TaskUpdate

SERVICE_NAME = "tasks-api"
SERVICE_VERSION = "0.1.0"

app = FastAPI(title="Task API", version=SERVICE_VERSION)

# ---- metrics ---------------------------------------------------------------
tasks_created = Counter("tasks_created_total", "Tasks created via POST /api/tasks")
tasks_deleted = Counter("tasks_deleted_total", "Tasks deleted via DELETE /api/tasks/{id}")

# ---- in-memory store (demo only; see module docstring) ---------------------
_store: dict[str, Task] = {}
_lock = threading.Lock()


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up. Keep this cheap — no downstream calls."""
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Readiness: the app can serve traffic."""
    return {"status": "ready", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/metrics")
def metrics() -> Response:
    """Prometheus scrape endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate) -> Task:
    task = Task(id=uuid.uuid4().hex[:12], title=payload.title.strip(), done=False)
    with _lock:
        _store[task.id] = task
    tasks_created.inc()
    return task


@app.get("/api/tasks", response_model=list[Task])
def list_tasks() -> list[Task]:
    with _lock:
        return list(_store.values())[:100]


@app.get("/api/tasks/{task_id}", response_model=Task)
def get_task(task_id: str) -> Task:
    with _lock:
        task = _store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.patch("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: str, payload: TaskUpdate) -> Task:
    with _lock:
        task = _store.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        data = task.model_dump()
        if payload.title is not None:
            data["title"] = payload.title.strip()
        if payload.done is not None:
            data["done"] = payload.done
        updated = Task(**data)
        _store[task_id] = updated
    return updated


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: str) -> None:
    with _lock:
        if _store.pop(task_id, None) is None:
            raise HTTPException(status_code=404, detail="task not found")
    tasks_deleted.inc()
    return None
