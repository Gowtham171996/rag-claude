import time


def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "vector_db" in data["checks"]
    assert data["checks"]["vector_db"] == "ok"


def test_health_response_time(client):
    start = time.monotonic()
    client.get("/api/v1/health")
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms < 500  # generous limit for CI environments


def test_health_no_auth_required(client):
    # Health endpoint must be reachable without X-API-Key
    response = client.get("/api/v1/health")
    assert response.status_code != 401
