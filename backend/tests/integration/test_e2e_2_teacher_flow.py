"""E2E 2/3 — A teacher runs a whole course through the API with a real JWT, touching EVERY teacher-service
endpoint: courses → attendance → exams → grades → actas (CURSADA + FINAL) → results → calendar/purchases.
At the end it asserts that no /api/v1 route of the teacher service was left unexercised.
"""

from __future__ import annotations

from flask import request_started

from tests.conftest import STUDENT_CLIENT

JUAN = "ba310c57-a684-4dbf-a4a4-905fcfbefa08"
LUCAS = "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57"
ANA = "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58"
TEACHER_ID = "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"
MOCK_CORE_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/wallets",
    "/api/v1/notifications",
    "/internal/",
    "/.well-known",
)


def test_e2e_full_teacher_flow_covers_every_endpoint(e2e_app):
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
        if r.rule.startswith("/api/v1") and not r.rule.startswith(MOCK_CORE_PREFIXES)
    }
    assert expected - hit == set(), f"endpoints not exercised: {sorted(expected - hit)}"


def _flow(app):
    c = app.test_client()
    tok = c.post("/api/v1/auth/login", json={"email": "maria.gomez@uade.edu.ar", "password": "Uade2026!"})
    h = {"Authorization": f"Bearer {tok.get_json()['accessToken']}"}

    def ok(r, status=200):
        assert r.status_code == status, (r.request.method, r.request.path, r.status_code, r.get_json())
        return r.get_json()

    # ── health + identity + catalogs ────────────────────────────────────────────────
    assert ok(c.get("/api/v1/health"))["status"] == "ok"
    ready = ok(c.get("/api/v1/health/ready"))
    assert ready["migrationHead"] == "0003" and ready["integrations"]["core"] == "mock"
    assert ok(c.get("/api/v1/me", headers=h))["teacherIds"] == [TEACHER_ID]
    assert ok(c.get("/api/v1/periods", headers=h))[1]["label"] == "2° Cuatrimestre 2026"
    assert ok(c.get("/api/v1/exam-turns", headers=h))[0]["name"] == "Turno final diciembre"
    assert "FINAL" in {t["type"] for t in ok(c.get("/api/v1/exam-types", headers=h))}

    # ── courses (BFF over Gestión Académica) ────────────────────────────────────────
    courses = ok(c.get("/api/v1/courses?periodId=8", headers=h))
    assert {x["id"] for x in courses} == {42, 44}  # 43 belongs to another teacher
    course = ok(c.get("/api/v1/courses/42", headers=h))
    assert course["teachers"][0]["teacherId"] == TEACHER_ID and course["subject"]["code"] == "DDA2"
    roster = ok(c.get("/api/v1/courses/42/students", headers=h))
    assert [s["studentId"] for s in roster] == [JUAN, LUCAS, ANA]
    assert roster[0]["profile"]["fullName"] == "Juan Pérez"
    assert len(ok(c.get("/api/v1/courses/42/prerequisites", headers=h))) == 2

    # ── attendance: 4 classes → Juan 100 %, Lucas 50 % (LIBRE), Ana 100 % (justified) ──
    marks = {
        "2026-09-28": {JUAN: "PRESENTE", LUCAS: "PRESENTE", ANA: "PRESENTE"},
        "2026-10-05": {JUAN: "PRESENTE", LUCAS: "AUSENTE", ANA: "JUSTIFICADO"},
        "2026-10-12": {JUAN: "PRESENTE", LUCAS: "PRESENTE", ANA: "PRESENTE"},
        "2026-10-19": {JUAN: "PRESENTE", LUCAS: "AUSENTE", ANA: "PRESENTE"},
    }
    for day, m in marks.items():
        body = {"notes": None, "records": [{"studentId": s, "status": st} for s, st in m.items()]}
        ok(c.put(f"/api/v1/courses/42/attendances/{day}", json=body, headers=h), 201)
    future = c.put(
        "/api/v1/courses/42/attendances/2026-12-01",
        json={"records": [{"studentId": s, "status": "PRESENTE"} for s in (JUAN, LUCAS, ANA)]},
        headers=h,
    )
    assert future.status_code == 400 and future.get_json()["code"] == "DATE_IN_FUTURE"
    assert len(ok(c.get("/api/v1/courses/42/attendances", headers=h))) == 4
    day = ok(c.get("/api/v1/courses/42/attendances/2026-10-05", headers=h))
    assert {r["studentId"]: r["status"] for r in day["records"]}[ANA] == "JUSTIFICADO"
    summary = {
        s["studentId"]: s for s in ok(c.get("/api/v1/courses/42/attendance-summary", headers=h))["students"]
    }
    assert summary[LUCAS]["condition"] == "LIBRE" and summary[ANA]["condition"] == "REGULAR"

    # ── exams ─────────────────────────────────────────────────────────────────────────
    exam_body = {
        "type": "parcial 1",
        "date": "2026-10-21",
        "startTime": "18:00",
        "durationMinutes": 120,
        "modality": "PRESENCIAL",
    }
    p1 = ok(c.post("/api/v1/courses/42/exams", json=exam_body, headers=h), 201)
    assert p1["type"] == "PARCIAL_1" and p1["phase"] == "UPCOMING"
    dup = c.post("/api/v1/courses/42/exams", json=exam_body, headers=h)
    assert dup.status_code == 409 and dup.get_json()["code"] == "EXAM_TYPE_ALREADY_EXISTS"
    patched = ok(c.patch(f"/api/v1/courses/42/exams/{p1['id']}", json={"name": "Primer Parcial"}, headers=h))
    assert patched["name"] == "Primer Parcial"
    tp = ok(c.post("/api/v1/courses/42/exams", json={**exam_body, "type": "TP_1"}, headers=h), 201)
    assert (
        ok(c.post(f"/api/v1/courses/42/exams/{tp['id']}/cancellation", json={}, headers=h))["status"]
        == "CANCELADO"
    )
    final = ok(
        c.post(
            "/api/v1/courses/42/exams", json={**exam_body, "type": "FINAL", "date": "2026-12-03"}, headers=h
        ),
        201,
    )
    assert len(ok(c.get("/api/v1/courses/42/exams", headers=h))) == 3
    assert ok(c.get(f"/api/v1/courses/42/exams/{final['id']}", headers=h))["gradingProgress"]["pending"] == 3
    upcoming = ok(c.get("/api/v1/exams?phase=UPCOMING", headers=h))
    assert {e["id"] for e in upcoming} == {p1["id"], final["id"]}

    # ── grades ───────────────────────────────────────────────────────────────────────
    grades = {
        "entries": [
            {"studentId": JUAN, "grade": 8, "absent": False},
            {"studentId": LUCAS, "grade": 9.5, "absent": False},
            {"studentId": ANA, "grade": None, "absent": True},
        ]
    }
    saved = ok(c.put(f"/api/v1/courses/42/exams/{p1['id']}/grades", json=grades, headers=h))
    assert saved["saved"] == 3
    bad = c.put(
        f"/api/v1/courses/42/exams/{p1['id']}/grades",
        json={"entries": [{"studentId": JUAN, "grade": 10.5, "absent": False}]},
        headers=h,
    )
    assert bad.status_code == 400
    sheet = ok(c.get(f"/api/v1/courses/42/exams/{p1['id']}/grades", headers=h))
    assert sheet["summary"]["graded"] == 2 and sheet["summary"]["absent"] == 1
    final_grades = {
        "entries": [
            {"studentId": JUAN, "grade": 8, "absent": False},
            {"studentId": LUCAS, "grade": 9, "absent": False},
            {"studentId": ANA, "grade": 3.5, "absent": False},
        ]
    }
    ok(c.put(f"/api/v1/courses/42/exams/{final['id']}/grades", json=final_grades, headers=h))
    matrix = ok(c.get("/api/v1/courses/42/grades", headers=h))
    assert len(matrix["exams"]) == 2 and len(matrix["rows"]) == 3

    # ── actas ───────────────────────────────────────────────────────────────────────
    cursada = ok(c.post("/api/v1/actas", json={"courseId": 42, "type": "CURSADA"}, headers=h), 201)
    res = {r["studentId"]: r["result"] for r in cursada["rows"]}
    assert res == {JUAN: "REGULAR", LUCAS: "LIBRE", ANA: "REGULAR"}
    assert cursada["number"] == "2026-001" and cursada["sync"]["ok"] == 3
    locked = c.put(
        "/api/v1/courses/42/attendances/2026-10-19",
        json={"records": [{"studentId": s, "status": "PRESENTE"} for s in (JUAN, LUCAS, ANA)]},
        headers=h,
    )
    assert locked.status_code == 409 and locked.get_json()["code"] == "ATTENDANCE_LOCKED_BY_ACTA"

    fin = ok(
        c.post("/api/v1/actas", json={"courseId": 42, "type": "FINAL", "examId": final["id"]}, headers=h), 201
    )
    res = {r["studentId"]: r["result"] for r in fin["rows"]}
    # Lucas passed the exam (9) but is LIBRE by attendance → not approved (design §11.3)
    assert res == {JUAN: "APROBADO", LUCAS: "LIBRE", ANA: "DESAPROBADO"}
    assert fin["teacherName"] == "María Gómez" and fin["number"] == "2026-002"
    again = c.post("/api/v1/actas", json={"courseId": 42, "type": "FINAL", "examId": final["id"]}, headers=h)
    assert again.status_code == 409 and again.get_json()["existingActaId"] == fin["id"]

    page = ok(c.get("/api/v1/actas?courseId=42", headers=h))
    assert page["total"] == 2
    assert ok(c.get(f"/api/v1/actas/{fin['id']}", headers=h))["counts"]["approved"] == 1
    assert ok(c.post(f"/api/v1/actas/{fin['id']}/sync", headers=h))["sync"]["error"] == 0
    annulled = ok(
        c.post(
            f"/api/v1/actas/{cursada['id']}/annulment",
            json={"reason": "Error en la carga de asistencia"},
            headers=h,
        )
    )
    assert annulled["status"] == "ANULADA"

    # ── results for the Student Portal (service token) ───────────────────────────────
    svc = ok(
        c.post(
            "/internal/v1/service-auth/token",
            json={"clientId": STUDENT_CLIENT[0], "clientSecret": STUDENT_CLIENT[1]},
        )
    )
    sh = {"Authorization": f"Bearer {svc['accessToken']}"}
    mine = ok(c.get(f"/api/v1/students/{JUAN}/results", headers=sh))
    assert mine[0]["result"] == "APROBADO" and mine[0]["grade"] == 8.0
    assert len(ok(c.get("/api/v1/courses/42/results", headers=sh))) == 3
    own_att = ok(c.get(f"/api/v1/students/{JUAN}/courses/42/attendance", headers=sh))
    assert own_att["studentId"] == JUAN and len(own_att["classes"]) == own_att["classesRecorded"] > 0
    own_grades = ok(c.get(f"/api/v1/students/{JUAN}/courses/42/grades", headers=sh))
    assert own_grades["studentId"] == JUAN and own_grades["exams"]

    # ── calendar (exams + exam turns + events + dining) and store purchases ─────────
    cal = ok(c.get("/api/v1/calendar?from=2026-10-01&to=2026-12-31", headers=h))
    kinds = {i["kind"] for i in cal["items"]}
    assert kinds == {"EXAM", "EXAM_TURN", "ACADEMIC_EVENT", "DINING_RESERVATION"} and cal["degraded"] == []
    assert c.get("/api/v1/calendar?from=2026-10-10&to=2026-10-01", headers=h).status_code == 400
    purchases = ok(c.get("/api/v1/purchases", headers=h))
    assert (
        purchases[0]["total"] == "2400.00" and purchases[0]["items"][0]["productName"] == "Cuaderno A4 UADE"
    )
