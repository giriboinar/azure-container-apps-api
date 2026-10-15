"""API tests. No Azure credentials needed — the app runs fully locally."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create(title="Write tests"):
    r = client.post("/api/tasks", json={"title": title})
    assert r.status_code == 201
    return r.json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_reports_version():
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["version"] == "0.1.0"


def test_metrics_exposes_prometheus_format():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "tasks_created_total" in r.text


def test_create_task_returns_201_with_id():
    task = _create("Deploy to Container Apps")
    assert task["id"]
    assert task["title"] == "Deploy to Container Apps"
    assert task["done"] is False


def test_create_task_rejects_empty_title():
    r = client.post("/api/tasks", json={"title": "   "})
    assert r.status_code == 422


def test_create_task_rejects_missing_title():
    r = client.post("/api/tasks", json={})
    assert r.status_code == 422


def test_create_task_rejects_overlong_title():
    r = client.post("/api/tasks", json={"title": "x" * 201})
    assert r.status_code == 422


def test_list_tasks_contains_created():
    task = _create("List me")
    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert any(t["id"] == task["id"] for t in r.json())


def test_get_task_by_id():
    task = _create("Fetch me")
    r = client.get(f"/api/tasks/{task['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Fetch me"


def test_get_task_missing_returns_404():
    r = client.get("/api/tasks/does-not-exist")
    assert r.status_code == 404


def test_patch_task_marks_done():
    task = _create("Patch me")
    r = client.patch(f"/api/tasks/{task['id']}", json={"done": True})
    assert r.status_code == 200
    assert r.json()["done"] is True


def test_patch_task_updates_title():
    task = _create("Old title")
    r = client.patch(f"/api/tasks/{task['id']}", json={"title": "New title"})
    assert r.status_code == 200
    assert r.json()["title"] == "New title"


def test_patch_task_missing_returns_404():
    r = client.patch("/api/tasks/does-not-exist", json={"done": True})
    assert r.status_code == 404


def test_delete_task_returns_204_and_removes():
    task = _create("Delete me")
    r = client.delete(f"/api/tasks/{task['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404


def test_delete_task_missing_returns_404():
    r = client.delete("/api/tasks/does-not-exist")
    assert r.status_code == 404


def _counter_value(text, name):
    for line in text.splitlines():
        if line.startswith(name + " "):
            return float(line.split(" ", 1)[1])
    raise AssertionError(f"counter {name} not found in /metrics")


def test_metrics_counter_increments_on_create():
    before = _counter_value(client.get("/metrics").text, "tasks_created_total")
    _create("Count me")
    after = _counter_value(client.get("/metrics").text, "tasks_created_total")
    assert after == before + 1
