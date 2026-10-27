"""E2E 3/3 — What leaves the teacher module, and the CORE-side features the portal uses.

grade published → outbox (event + student notification, same transaction) → dispatcher → CORE envelope
contract + student sees the notification in CORE (/api/v1/notifications); FINAL acta → per-student
`teacher.course-result-published.v1` for Analítica; wallet balance / top-up idempotency; and every
route of the CORE simulator exercised.
"""

from __future__ import annotations

import uuid

from flask import request_started
from sqlalchemy import select

from app.extensions import db
from app.models import Examen, OutboxEvent
from app.services import event_service

JUAN = "ba310c57-a684-4dbf-a4a4-905fcfbefa08"
LUCAS = "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57"
ANA = "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58"
CORE_PREFIXES = ("/api/v1/auth", "/api/v1/wallets", "/api/v1/notifications", "/internal/", "/.well-known")


def _login(c, email):
    r = c.post("/api/v1/auth/login", json={"email": email, "password": "Uade2026!"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.get_json()['accessToken']}"}


def test_e2e_events_notifications_and_wallet(e2e_app, seeded):
    hit: set[tuple[str, str]] = set()

    def _record(sender, **_):
        from flask import request

        if request.url_rule is not None:
            hit.add((request.method, request.url_rule.rule))

    request_started.connect(_record, e2e_app)
    try:
        _flow(e2e_app)
    finally:
        request_started.disconnect(_record, e2e_app)
    expected = {
        (m, r.rule)
        for r in e2e_app.url_map.iter_rules()
        for m in r.methods - {"HEAD", "OPTIONS"}
        if r.rule.startswith(CORE_PREFIXES)
    }
    assert expected - hit == set(), f"CORE simulator routes not exercised: {sorted(expected - hit)}"


def _flow(app):
    c = app.test_client()
    teacher = _login(c, "maria.gomez@uade.edu.ar")
    integ = app.extensions["integrations"]
    cid = str(uuid.uuid4())

    # ── grade publication → outbox (1 event + 1 notification per student with a new grade) ──
    with app.app_context():
        final_id = db.session.scalar(select(Examen.id).where(Examen.curso_id == 42, Examen.tipo == "FINAL"))
    body = {
        "entries": [
            {"studentId": JUAN, "grade": 8, "absent": False},
            {"studentId": LUCAS, "grade": 3, "absent": False},
            {"studentId": ANA, "grade": None, "absent": True},
        ]
    }
    r = c.put(
        f"/api/v1/courses/42/exams/{final_id}/grades", json=body, headers={**teacher, "X-Correlation-Id": cid}
    )
    assert r.status_code == 200
    with app.app_context():
        rows = db.session.scalars(select(OutboxEvent).order_by(OutboxEvent.created_at)).all()
        kinds = sorted((o.kind, o.event_type) for o in rows)
        assert kinds == [
            ("EVENT", "teacher.grade-published.v1"),
            ("NOTIFICATION", "TEACHER_EXAM_RESULT_PUBLISHED"),
            ("NOTIFICATION", "TEACHER_EXAM_RESULT_PUBLISHED"),
        ]
        stats = event_service.dispatch_due()
        assert stats == {"sent": 3, "failed": 0, "retried": 0}
    # re-saving the same grades publishes nothing new
    assert c.put(f"/api/v1/courses/42/exams/{final_id}/grades", json=body, headers=teacher).status_code == 200
    with app.app_context():
        assert db.session.query(OutboxEvent).filter(OutboxEvent.status == "PENDING").count() == 0

    # CORE envelope contract (POST /internal/v1/events): required fields, UUIDs, source = token module
    env = integ.core_events.published[0]
    assert set(env) >= {
        "specVersion",
        "eventId",
        "eventType",
        "source",
        "occurredAt",
        "subject",
        "correlationId",
        "causationId",
        "actor",
        "data",
    }
    assert env["specVersion"] == "1.0" and env["source"] == "teacher" and env["correlationId"] == cid
    assert uuid.UUID(env["eventId"]) and env["actor"]["type"] in ("user", "service", "system")
    assert {g["studentId"]: g["status"] for g in env["data"]["grades"]} == {
        JUAN: "APROBADO",
        LUCAS: "DESAPROBADO",
    }

    # ── the student sees the notification in CORE (TPO §1: real-time result notification) ──
    student = _login(c, "juan.perez@uade.edu.ar")
    assert c.get("/api/v1/notifications/unread-count", headers=student).get_json() == {"count": 1}
    items = c.get("/api/v1/notifications?read=false", headers=student).get_json()["items"]
    n = items[0]
    assert n["type"] == "TEACHER_EXAM_RESULT_PUBLISHED" and n["sourceModule"] == "teacher"
    assert n["actionUrl"] == f"/student/courses/42/exams/{final_id}" and "8" in n["message"]
    assert c.patch(f"/api/v1/notifications/{n['id']}", json={"read": True}, headers=student).get_json()[
        "readAt"
    ]
    assert (
        c.patch(f"/api/v1/notifications/{n['id']}", json={"read": True}, headers=teacher).status_code == 404
    )
    assert (
        c.patch(f"/api/v1/notifications/{n['id']}", json={"read": False}, headers=student).status_code == 200
    )
    assert c.post("/api/v1/notifications/read-all", headers=student).status_code == 204
    assert c.get("/api/v1/notifications/unread-count", headers=student).get_json() == {"count": 0}

    # ── FINAL acta → one course-result event per decided student (Analítica contract) ──
    acta = c.post(
        "/api/v1/actas", json={"courseId": 42, "type": "FINAL", "examId": final_id}, headers=teacher
    )
    assert acta.status_code == 201
    with app.app_context():
        event_service.dispatch_due()
    results = [
        e for e in integ.core_events.published if e["eventType"] == "teacher.course-result-published.v1"
    ]
    by_student = {e["data"]["studentId"]: e["data"] for e in results}
    assert set(by_student) == {JUAN, LUCAS}  # Ana is AUSENTE: no course result
    assert by_student[JUAN] | {"siteId": None} == {
        "studentId": JUAN,
        "courseId": 42,
        "subjectId": 15,
        "periodId": 8,
        "siteId": None,
        "teacherId": "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034",
        "finalGrade": 8.0,
        "status": "APROBADO",
        "resultDate": "2026-10-19",
        "actaNumber": acta.get_json()["number"],
    }
    assert any(e["eventType"] == "teacher.acta-generated.v1" for e in integ.core_events.published)

    # ── wallet (CORE): balance, history, top-up idempotency and error codes ──────────────
    w = c.get("/api/v1/wallets/me", headers=teacher).get_json()
    assert w["balance"] == "15000.00" and w["currency"] == "ARS"
    key = str(uuid.uuid4())
    top = {"amount": "5000.00", "currency": "ARS", "paymentMethodToken": "mock-approved"}
    t1 = c.post("/api/v1/wallets/me/top-ups", json=top, headers={**teacher, "Idempotency-Key": key})
    assert t1.status_code == 201 and t1.get_json()["balanceAfter"] == "20000.00"
    t2 = c.post("/api/v1/wallets/me/top-ups", json=top, headers={**teacher, "Idempotency-Key": key})
    assert t2.get_json()["transactionId"] == t1.get_json()["transactionId"]  # replay, not a 2nd credit
    conflict = c.post(
        "/api/v1/wallets/me/top-ups",
        json={**top, "amount": "1.00"},
        headers={**teacher, "Idempotency-Key": key},
    )
    assert conflict.status_code == 409 and conflict.get_json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert (
        c.post("/api/v1/wallets/me/top-ups", json=top, headers=teacher).get_json()["code"]
        == "IDEMPOTENCY_KEY_REQUIRED"
    )
    rejected = c.post(
        "/api/v1/wallets/me/top-ups",
        json={**top, "paymentMethodToken": "mock-rejected"},
        headers={**teacher, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert rejected.status_code == 422 and rejected.get_json()["code"] == "WALLET_TOPUP_REJECTED"
    assert (
        c.post(
            "/api/v1/wallets/me/top-ups",
            json={**top, "amount": "1.234"},
            headers={**teacher, "Idempotency-Key": str(uuid.uuid4())},
        ).status_code
        == 400
    )
    assert c.get("/api/v1/wallets/me", headers=teacher).get_json()["balance"] == "20000.00"
    txs = c.get("/api/v1/wallets/me/transactions?limit=10", headers=teacher).get_json()["items"]
    assert [t["concept"] for t in txs] == ["TOP_UP", "TOP_UP"] and txs[0]["amount"] == "5000.00"
    admin = _login(c, "secretaria.academica@uade.edu.ar")  # no wallet:credit:self
    assert (
        c.post(
            "/api/v1/wallets/me/top-ups", json=top, headers={**admin, "Idempotency-Key": str(uuid.uuid4())}
        ).status_code
        == 403
    )

    # ── remaining CORE routes ─────────────────────────────────────────────────────────
    assert c.get("/api/v1/auth/me", headers=teacher).status_code == 200
    assert c.get("/.well-known/jwks.json").status_code == 200
    assert c.post("/api/v1/auth/refresh").status_code == 200
    svc = c.post(
        "/internal/v1/service-auth/token",
        json={"clientId": "student-service", "clientSecret": "student-secret"},
    ).get_json()
    note = {
        "userId": JUAN,
        "type": "PING",
        "title": "t",
        "message": "m",
        "sourceModule": "student",
        "sourceReference": "p/1",
    }
    assert (
        c.post(
            "/internal/v1/notifications", json=note, headers={"Authorization": f"Bearer {svc['accessToken']}"}
        ).status_code
        == 201
    )
    assert c.post("/api/v1/auth/password/forgot", json={"email": "nadie@uade.edu.ar"}).status_code == 202
    assert c.post("/api/v1/auth/logout", headers=teacher).status_code == 204
