from tests.helpers import as_teacher


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}
    assert r.headers["X-Correlation-Id"]


def test_ready(client):
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 200
    body = r.get_json()
    assert body["migrationHead"] == "0003"
    assert body["integrations"] == {
        "academic": "mock",
        "coreEvents": "mock",
        "studentDirectory": "mock",
        "notifications": "mock",
        "campus": "mock",
        "core": "external",
    }


def test_courses_for_teacher(client):
    r = client.get("/api/v1/courses", headers=as_teacher())
    assert r.status_code == 200, r.get_data(as_text=True)
    ids = [c["id"] for c in r.get_json()]
    assert ids == [42, 44, 30] or sorted(ids) == [30, 42, 44]
