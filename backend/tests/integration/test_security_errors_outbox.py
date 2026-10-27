import logging
from datetime import UTC, datetime

import pytest
import requests
import requests_mock
from sqlalchemy import select, text

from app.errors import PublishError
from app.extensions import db
from app.models import OutboxEvent
from app.services import event_service
from tests.conftest import make_app
from tests.helpers import as_service, as_teacher, attendance_body

CORE = "https://core.test"
ME = f"{CORE}/api/v1/auth/me"


@pytest.fixture()
def core_app(database_url):
    return make_app(
        database_url, AUTH_VERIFIER="introspect", CORE_BASE_URL=CORE, TOKEN_CACHE_TTL_SECONDS="60"
    )


def bearer(t="tok-abc"):
    return {"Authorization": f"Bearer {t}"}


def me_ok(**over):
    return {
        "id": "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034",
        "email": "maria.gomez@uade.edu.ar",
        "careerIds": [],
        "roles": ["TEACHER"],
        "permissions": [],
        "status": "ACTIVE",
        **over,
    }


# ---------------------------------------------------------------- introspection verifier
def test_no_token_is_401(client):
    r = client.get("/api/v1/courses")
    assert r.status_code == 401 and r.get_json()["code"] == "TOKEN_INVALID"
    assert r.mimetype == "application/problem+json"


def test_valid_token_caches_and_maps_owner(core_app):
    c = core_app.test_client()
    with requests_mock.Mocker() as m:
        m.get(ME, json=me_ok())
        r1 = c.get("/api/v1/courses", headers=bearer())
        r2 = c.get("/api/v1/courses/42", headers=bearer())
        assert r1.status_code == 200 and [x["id"] for x in r1.get_json()].count(42) == 1
        assert r2.status_code == 200  # CORE user id == GA docenteId (Backoffice UUID)
        assert m.call_count == 1  # second call within TTL did not hit CORE
        assert m.request_history[0].headers["Authorization"] == "Bearer tok-abc"


def test_rejected_token_is_401(core_app):
    with requests_mock.Mocker() as m:
        m.get(ME, status_code=401)
        r = core_app.test_client().get("/api/v1/courses", headers=bearer("bad"))
        assert r.status_code == 401 and r.get_json()["code"] == "TOKEN_INVALID"


def test_core_unreachable_fails_closed_503(core_app):
    with requests_mock.Mocker() as m:
        m.get(ME, exc=requests.exceptions.ConnectTimeout)
        r = core_app.test_client().get("/api/v1/courses", headers=bearer())
        assert r.status_code == 503 and r.get_json()["code"] == "AUTH_UNAVAILABLE"
        m.get(ME, status_code=500)
        assert core_app.test_client().get("/api/v1/courses", headers=bearer("t2")).status_code == 503


def test_inactive_user_is_401(core_app):
    with requests_mock.Mocker() as m:
        m.get(ME, json=me_ok(status="SUSPENDED"))
        assert core_app.test_client().get("/api/v1/courses", headers=bearer()).status_code == 401


def test_non_teacher_role_is_403(core_app):
    with requests_mock.Mocker() as m:
        m.get(ME, json=me_ok(roles=["STUDENT"]))
        r = core_app.test_client().get("/api/v1/courses", headers=bearer())
        assert r.status_code == 403 and r.get_json()["code"] == "FORBIDDEN"


def test_raw_token_never_logged(core_app, caplog):
    caplog.set_level(logging.DEBUG)
    with requests_mock.Mocker() as m:
        m.get(ME, json=me_ok())
        core_app.test_client().get("/api/v1/courses", headers=bearer("super-secret-token-123"))
    assert "super-secret-token-123" not in caplog.text


def test_invalid_token_rate_limit(database_url):
    app = make_app(
        database_url, AUTH_VERIFIER="introspect", CORE_BASE_URL=CORE, INVALID_TOKEN_LIMIT_PER_MINUTE="3"
    )
    c = app.test_client()
    with requests_mock.Mocker() as m:
        m.get(ME, status_code=401)
        codes = [c.get("/api/v1/courses", headers=bearer(f"bad{i}")).status_code for i in range(5)]
    assert codes == [401, 401, 401, 429, 429]


# ---------------------------------------------------------------- service routes
def test_service_routes(client, seeded_with_acta):
    url = "/api/v1/students/ba310c57-a684-4dbf-a4a4-905fcfbefa08/results"
    assert client.get(url, headers=as_service()).status_code == 200
    assert client.get(url, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get(url, headers=as_teacher()).status_code == 403  # teacher token
    assert client.get(url).status_code == 401
    ok = client.get(url, headers={"Authorization": "Bearer svc-token-2"})  # overlap for rotation
    assert ok.status_code == 200
    body = client.get("/api/v1/courses/42/results", headers=as_service()).get_json()
    assert {r["studentId"] for r in body} == {
        "ba310c57-a684-4dbf-a4a4-905fcfbefa08",
        "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57",
        "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58",
    }
    assert client.get("/api/v1/courses/42/results", headers=as_teacher()).status_code == 403
    only = client.get(f"{url}?courseId=999", headers=as_service()).get_json()
    assert only == []


def test_dev_verifier_refused_in_production(database_url):
    from app.config import ConfigError

    with pytest.raises(ConfigError):
        make_app(database_url, APP_ENV="production", AUTH_VERIFIER="dev")


# ---------------------------------------------------------------- error conventions
def test_problem_json_shape_and_correlation_id(client):
    cid = "6f1c2d3e-77aa-4b10-90ce-5c4d1e77a201"
    r = client.get(
        "/api/v1/courses/42",
        headers={**as_teacher("99999999-9999-4999-8999-999999999999"), "X-Correlation-Id": cid},
    )
    body = r.get_json()
    assert r.status_code == 403 and r.mimetype == "application/problem+json"
    assert body["code"] == "COURSE_NOT_ASSIGNED" and body["correlationId"] == cid and body["status"] == 403
    assert body["title"] == "Forbidden" and body["detail"] and r.headers["X-Correlation-Id"] == cid
    assert body["instance"] == "/api/v1/courses/42"
    # CORE requires UUID correlation ids: a non-UUID inbound value is replaced
    r2 = client.get("/api/v1/courses/42", headers={**as_teacher(), "X-Correlation-Id": "abc-123"})
    assert r2.headers["X-Correlation-Id"] != "abc-123" and len(r2.headers["X-Correlation-Id"]) == 36


def test_unknown_field_and_malformed_json_are_400(client):
    h = as_teacher()
    body = attendance_body()
    body["bogus"] = 1
    r = client.put("/api/v1/courses/42/attendances/2026-10-12", headers=h, json=body)
    assert r.status_code == 400 and r.get_json()["code"] == "VALIDATION_ERROR"
    assert r.get_json()["errors"][0]["field"] == "bogus"
    r = client.put(
        "/api/v1/courses/42/attendances/2026-10-12",
        headers={**h, "Content-Type": "application/json"},
        data="{not json",
    )
    assert r.status_code == 400 and r.get_json()["code"] == "MALFORMED_JSON"


def test_validation_error_paths_are_camel_case(client, seeded):
    eid = client.get("/api/v1/courses/42/exams", headers=as_teacher()).get_json()[0]["id"]
    r = client.put(
        f"/api/v1/courses/42/exams/{eid}/grades",
        headers=as_teacher(),
        json={
            "entries": [
                {"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 5},
                {"studentId": "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", "grade": 11},
            ]
        },
    )
    e = r.get_json()["errors"][0]
    assert e["field"] == "entries[1].grade" and e["code"]


def test_http_errors_are_problem_json(client):
    r = client.get("/api/v1/nope")
    assert (
        r.status_code == 404
        and r.get_json()["code"] == "NOT_FOUND"
        and r.mimetype == "application/problem+json"
    )
    r = client.post("/api/v1/health")
    assert r.status_code == 405 and r.get_json()["code"] == "METHOD_NOT_ALLOWED"


def test_security_headers(client):
    r = client.get("/api/v1/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["Cache-Control"] == "no-store"


def test_every_route_is_documented(app):
    import re

    from app.extensions import spec

    with app.app_context():
        paths = set(spec.spec["paths"])

    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/v1"):
            doc = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule)
            assert doc in paths, f"{rule.rule} is not documented in OpenAPI"


def test_swagger_is_served(client):
    assert client.get("/apidocs/openapi.json").status_code == 200
    assert client.get("/apidocs/swagger/").status_code == 200


# ---------------------------------------------------------------- outbox dispatcher
def _enqueue(app, n=1):
    with app.app_context():
        for i in range(n):
            event_service.enqueue(
                db.session,
                "teacher.exam-created.v1",
                f"exam/{i}",
                {"i": i},
                "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034",
                "cid",
            )
        db.session.commit()


def _rows():
    return db.session.scalars(select(OutboxEvent).order_by(OutboxEvent.created_at)).all()


def test_dispatch_marks_sent(app, integ):
    _enqueue(app, 2)
    with app.app_context():
        assert event_service.dispatch_due() == {"sent": 2, "failed": 0, "retried": 0}
        assert [r.status for r in _rows()] == ["SENT", "SENT"] and _rows()[0].sent_at is not None
    env = integ.core_events.published[0]
    assert env["specVersion"] == "1.0" and env["source"] == "teacher" and env["correlationId"] == "cid"
    assert env["eventId"] in {str(i) for i in _rows_ids(app)}


def _rows_ids(app):
    with app.app_context():
        return [r.id for r in _rows()]


def test_dispatch_retry_backoff_then_failed(app, integ):
    _enqueue(app)
    integ.core_events.fail_next(1, retryable=True)
    with app.app_context():
        assert event_service.dispatch_due()["retried"] == 1
        row = _rows()[0]
        assert row.status == "PENDING" and row.attempts == 1
        delta = row.next_attempt_at - datetime(2026, 10, 19, 15, 0, 10, tzinfo=UTC)  # 5s * 2^1 backoff
        assert abs(delta.total_seconds()) < 2
        assert "Fallo simulado" in row.last_error
        db.session.execute(text("update outbox_event set next_attempt_at = now()"))
        db.session.commit()
    integ.core_events.fail_next(1, retryable=False)
    with app.app_context():
        assert event_service.dispatch_due()["failed"] == 1
        assert _rows()[0].status == "FAILED"
        assert event_service.requeue_failed() == 1 and _rows()[0].status == "PENDING"


def test_dispatch_skip_locked_never_double_publishes(app, integ):
    _enqueue(app, 3)
    with app.app_context():
        with db.engine.connect() as other:  # another dispatcher holding the rows
            other.execute(text("select id from outbox_event where status='PENDING' for update"))
            assert event_service.dispatch_due() == {"sent": 0, "failed": 0, "retried": 0}
            other.rollback()
        assert event_service.dispatch_due()["sent"] == 3
    assert len(integ.core_events.published) == 3


def test_publish_error_flags():
    assert PublishError("x").retryable is True and PublishError("x", retryable=False).retryable is False


def test_inline_dispatch_after_response(database_url):
    app = make_app(database_url, EVENTS_INLINE_DISPATCH="true")
    with app.app_context():
        db.session.execute(
            text("truncate outbox_event, acta_detalle, acta, calificacion, examen, asistencia, clase")
        )
        db.session.commit()
    c = app.test_client()
    r = c.put("/api/v1/courses/42/attendances/2026-10-12", headers=as_teacher(), json=attendance_body())
    assert r.status_code == 201
    r.close()  # triggers call_on_close
    with app.app_context():
        assert [x.status for x in _rows()] == ["SENT"]


def test_outbox_prune(app):
    _enqueue(app)
    with app.app_context():
        event_service.dispatch_due()
        db.session.execute(text("update outbox_event set sent_at = now() - interval '31 days'"))
        db.session.commit()
        assert event_service.prune_sent(30) == 1 and _rows() == []


def test_ready_reports_outbox(client, app):
    _enqueue(app, 2)
    assert client.get("/api/v1/health/ready").get_json()["outboxPending"] == 2


def test_validation_messages_are_spanish(client, seeded):
    h = as_teacher()
    eid = client.get("/api/v1/courses/42/exams", headers=h).get_json()[0]["id"]
    url = f"/api/v1/courses/42/exams/{eid}/grades"

    def msgs(body):
        r = client.put(url, headers=h, json=body)
        assert r.status_code == 400
        return {e["field"]: e["message"] for e in r.get_json()["errors"]}

    assert msgs({"entries": [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 11}]}) == {
        "entries[0].grade": "Debe ser menor o igual a 10."
    }
    assert msgs({"entries": [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 7.123}]})[
        "entries[0].grade"
    ] == ("Admite como máximo 2 decimales.")
    assert msgs({"entries": [{"grade": 5}]})["entries[0].studentId"] == "Campo obligatorio."
    assert msgs({"entries": [], "x": 1}) == {
        "entries": "Debe tener al menos 1 elemento(s).",
        "x": "Campo no permitido.",
    }
    r = client.post(
        "/api/v1/courses/42/exams",
        headers=h,
        json={
            "type": "x y!",
            "date": "mañana",
            "startTime": "18:00",
            "durationMinutes": 0,
            "modality": "HIBRIDA",
        },
    )
    m = {e["field"]: e["message"] for e in r.get_json()["errors"]}
    assert m["type"].startswith("El tipo solo admite") and m["date"].startswith("Debe ser una fecha")
    assert m["durationMinutes"] == "Debe ser mayor o igual a 1." and "Valores válidos" in m["modality"]
    assert not any("should" in v.lower() or "input" in v.lower() for v in m.values())


def test_acta_generated_at_uses_app_clock(client, seeded):
    h = as_teacher()
    r = client.post("/api/v1/actas", headers=h, json={"courseId": 42, "type": "CURSADA"})
    assert r.get_json()["generatedAt"].startswith("2026-10-19T15:00")
