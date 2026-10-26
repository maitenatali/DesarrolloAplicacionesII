import dataclasses
import threading

from sqlalchemy import select

from app.integrations.base import Subject
from app.models import Acta, OutboxEvent
from tests.conftest import make_app
from tests.helpers import as_service, as_teacher, exam_body

EX = "/api/v1/courses/42/exams"
H = as_teacher()


def exam_id(client, tipo, course=42, headers=H):
    return next(
        e["id"]
        for e in client.get(f"/api/v1/courses/{course}/exams", headers=headers).get_json()
        if e["type"] == tipo
    )


def grade_final(client, grades=None):
    eid = exam_id(client, "FINAL")
    grades = grades or [
        {"studentId": "alumno-456", "grade": 8},
        {"studentId": "alumno-457", "grade": 3},
        {"studentId": "alumno-458", "absent": True},
    ]
    r = client.put(f"{EX}/{eid}/grades", headers=H, json={"entries": grades})
    assert r.status_code == 200, r.get_data(as_text=True)
    return eid


def gen_final(client, eid, **extra):
    return client.post(
        "/api/v1/actas", headers=H, json={"courseId": 42, "type": "FINAL", "examId": eid, **extra}
    )


def rows(body):
    return {r["studentId"]: (r["grade"], r["result"]) for r in body["rows"]}


def test_final_happy_path(client, seeded, integ):
    eid = grade_final(client)
    r = gen_final(client, eid, notes="Acta final")
    assert r.status_code == 201, r.get_data(as_text=True)
    a = r.get_json()
    assert r.headers["Location"] == f"/api/v1/actas/{a['id']}"
    assert (
        a["number"] == "2026-001"
        and a["type"] == "FINAL"
        and a["status"] == "GENERADA"
        and a["date"] == "2026-10-19"
    )
    assert rows(a) == {
        "alumno-456": (8.0, "APROBADO"),
        "alumno-457": (3.0, "DESAPROBADO"),
        "alumno-458": (None, "AUSENTE"),
    }
    assert [x["order"] for x in a["rows"]] == [1, 2, 3]
    assert a["subject"] == "Desarrollo de Aplicaciones II" and a["commission"] == "DDA2-A"
    assert (
        a["period"] == "2° Cuatrimestre 2026"
        and a["teacherName"] == "María Gómez"
        and a["teacherId"] == "docente-123"
    )
    assert a["counts"] == {"approved": 1, "failed": 1, "absent": 1, "regular": 0, "free": 0}
    assert a["sync"]["ok"] == 2 and a["sync"]["error"] == 0 and a["warnings"] == []
    sent = {
        (u["student_id"], u["status"], u["final_grade"] and float(u["final_grade"]))
        for u in integ.academic.updates
    }
    assert sent == {("alumno-456", "APROBADO", 8.0), ("alumno-457", "DESAPROBADO", 3.0)}  # AUSENTE never sent


def test_attendance_gate_libre(client, seeded):
    eid = grade_final(
        client,
        [
            {"studentId": "alumno-456", "grade": 8},
            {"studentId": "alumno-457", "grade": 8},
            {"studentId": "alumno-458", "grade": 3},
        ],
    )
    a = gen_final(client, eid).get_json()
    # 457 has 50% attendance (LIBRE): passed the exam but the course is NOT approved
    assert rows(a)["alumno-457"] == (8.0, "LIBRE")
    assert rows(a)["alumno-456"] == (8.0, "APROBADO") and rows(a)["alumno-458"] == (3.0, "DESAPROBADO")
    assert a["counts"]["free"] == 1


def test_boundary_4_and_399(client, seeded):
    eid = grade_final(
        client, [{"studentId": "alumno-456", "grade": 4}, {"studentId": "alumno-458", "grade": 3.99}]
    )
    a = gen_final(client, eid).get_json()
    assert rows(a)["alumno-456"] == (4.0, "APROBADO") and rows(a)["alumno-458"] == (3.99, "DESAPROBADO")
    assert rows(a)["alumno-457"] == (None, "AUSENTE")  # enrolled with no grade row


def test_final_requires_regular_off(database_url, seeded):
    app = make_app(database_url, FINAL_REQUIRES_REGULAR="false")
    c = app.test_client()
    eid = grade_final(c, [{"studentId": "alumno-457", "grade": 8}])
    assert rows(gen_final(c, eid).get_json())["alumno-457"] == (8.0, "APROBADO")


def test_no_attendance_rows_means_libre_for_final(client, seeded):
    h = as_teacher("docente-124")
    r = client.post("/api/v1/courses/43/exams", headers=h, json=exam_body(type="FINAL", date="2026-12-03"))
    assert r.status_code == 201
    eid = r.get_json()["id"]
    client.put(
        f"/api/v1/courses/43/exams/{eid}/grades",
        headers=h,
        json={"entries": [{"studentId": "alumno-101", "grade": 8}]},
    )
    a = client.post(
        "/api/v1/actas", headers=h, json={"courseId": 43, "type": "FINAL", "examId": eid}
    ).get_json()
    assert rows(a)["alumno-101"] == (8.0, "LIBRE")


def test_precondition_errors(client, seeded):
    p1 = exam_id(client, "PARCIAL_1")
    final = exam_id(client, "FINAL")
    p2 = exam_id(client, "PARCIAL_2")
    post = lambda body, h=H: client.post("/api/v1/actas", headers=h, json=body)  # noqa: E731
    assert post({"courseId": 42, "type": "FINAL"}).status_code == 400
    assert post({"courseId": 42, "type": "CURSADA", "examId": final}).status_code == 400
    r = post({"courseId": 42, "type": "FINAL", "examId": final})
    assert r.status_code == 409 and r.get_json()["code"] == "NO_GRADES"
    r = post({"courseId": 42, "type": "FINAL", "examId": p1})
    assert r.status_code == 409 and r.get_json()["code"] == "EXAM_NOT_FINAL_TYPE"
    assert post({"courseId": 42, "type": "FINAL", "examId": 99999}).get_json()["code"] == "EXAM_NOT_FOUND"
    client.post(f"{EX}/{p2}/cancellation", headers=H, json={})
    assert post({"courseId": 42, "type": "FINAL", "examId": p2}).get_json()["code"] == "EXAM_CANCELLED"
    assert post({"courseId": 43, "type": "CURSADA"}).status_code == 403
    assert post({"courseId": 44, "type": "CURSADA"}).get_json()["code"] == "COURSE_CANCELLED"
    r = post({"courseId": 43, "type": "CURSADA"}, as_teacher("docente-124"))
    assert r.status_code == 409 and r.get_json()["code"] == "NO_ATTENDANCE_RECORDED"
    assert post({"courseId": 9999, "type": "CURSADA"}).get_json()["code"] == "COURSE_NOT_FOUND"


def test_exam_of_another_course_is_404(client, seeded):
    final = exam_id(client, "FINAL")
    r = client.post("/api/v1/actas", headers=H, json={"courseId": 30, "type": "FINAL", "examId": final})
    assert r.status_code == 404 and r.get_json()["code"] == "EXAM_NOT_FOUND"


def test_cursada_uses_attendance_only(client, seeded, integ):
    # failed parciales must not matter: 457 has 50% attendance -> LIBRE, the rest REGULAR
    r = client.post("/api/v1/actas", headers=H, json={"courseId": 42, "type": "CURSADA"})
    assert r.status_code == 201, r.get_data(as_text=True)
    a = r.get_json()
    assert rows(a) == {
        "alumno-456": (None, "REGULAR"),
        "alumno-457": (None, "LIBRE"),
        "alumno-458": (None, "REGULAR"),
    }
    assert a["counts"] == {"approved": 0, "failed": 0, "absent": 0, "regular": 2, "free": 1}
    assert {(u["student_id"], u["status"], u["final_grade"]) for u in integ.academic.updates} == {
        ("alumno-456", "REGULAR", None),
        ("alumno-457", "LIBRE", None),
        ("alumno-458", "REGULAR", None),
    }
    assert a["sync"]["ok"] == 3


def test_duplicate_then_annul_then_next_number(client, seeded):
    eid = grade_final(client)
    first = gen_final(client, eid).get_json()
    r = gen_final(client, eid)
    assert r.status_code == 409 and r.get_json()["code"] == "ACTA_ALREADY_EXISTS"
    assert r.get_json()["existingActaId"] == first["id"]
    r = client.post(
        f"/api/v1/actas/{first['id']}/annulment", headers=H, json={"reason": "Error en una nota."}
    )
    assert r.status_code == 200 and r.get_json()["status"] == "ANULADA" and r.get_json()["annulmentReason"]
    client.put(f"{EX}/{eid}/grades", headers=H, json={"entries": [{"studentId": "alumno-457", "grade": 5}]})
    second = gen_final(client, eid).get_json()
    assert second["number"] == "2026-002"  # the annulled number is never reused


def test_annulment_rules(client, seeded):
    eid = grade_final(client)
    a = gen_final(client, eid).get_json()
    url = f"/api/v1/actas/{a['id']}/annulment"
    assert client.post(url, headers=H, json={"reason": "corto"}).status_code == 400
    assert client.post(url, headers=H, json={"reason": "   corto   "}).status_code == 400
    assert client.post(url, headers=H, json={"reason": "Motivo suficiente"}).status_code == 200
    r = client.post(url, headers=H, json={"reason": "Motivo suficiente"})
    assert r.status_code == 409 and r.get_json()["code"] == "ACTA_ALREADY_ANNULLED"
    r = client.post(f"/api/v1/actas/{a['id']}/sync", headers=H)
    assert r.status_code == 409 and r.get_json()["code"] == "ACTA_ANNULLED"


def test_results_view_reverts_to_previous_valid_acta(client, seeded):
    cursada = client.post("/api/v1/actas", headers=H, json={"courseId": 42, "type": "CURSADA"}).get_json()
    eid = grade_final(client)
    final = gen_final(client, eid).get_json()
    res = client.get("/api/v1/students/alumno-456/results", headers=as_service()).get_json()
    assert res[0]["actaType"] == "FINAL" and res[0]["result"] == "APROBADO" and res[0]["grade"] == 8.0
    client.post(f"/api/v1/actas/{final['id']}/annulment", headers=H, json={"reason": "Motivo suficiente"})
    res = client.get("/api/v1/students/alumno-456/results", headers=as_service()).get_json()
    assert (
        res[0]["actaType"] == "CURSADA"
        and res[0]["result"] == "REGULAR"
        and res[0]["actaNumber"] == cursada["number"]
    )
    assert res[0]["resultDate"] == "2026-10-19" and res[0]["commission"] == "DDA2-A"
    client.post(f"/api/v1/actas/{cursada['id']}/annulment", headers=H, json={"reason": "Motivo suficiente"})
    assert client.get("/api/v1/students/alumno-456/results", headers=as_service()).get_json() == []


def test_sync_failure_keeps_acta_and_retry(client, seeded, integ, db_session):
    eid = grade_final(client)
    integ.academic.fail_for = {"alumno-457"}
    r = gen_final(client, eid)
    assert r.status_code == 201
    a = r.get_json()
    assert a["sync"]["ok"] == 1 and a["sync"]["error"] == 1
    integ.academic.fail_for = set()
    r = client.post(f"/api/v1/actas/{a['id']}/sync", headers=H)
    assert r.status_code == 200 and r.get_json()["sync"]["ok"] == 2 and r.get_json()["sync"]["error"] == 0
    assert client.get(f"/api/v1/actas/{a['id']}", headers=H).get_json()["sync"]["error"] == 0


def test_ga_down_during_sync_still_creates_acta(client, seeded, integ, monkeypatch):
    eid = grade_final(client)
    from app.errors import UpstreamError

    def boom(*a, **k):
        raise UpstreamError("academic", status=504)

    monkeypatch.setattr(integ.academic, "update_enrollment_result", boom)
    a = gen_final(client, eid).get_json()
    assert a["sync"] == {"ok": 0, "error": 2, "lastAttemptAt": a["sync"]["lastAttemptAt"]}


def test_directory_down_aborts_without_acta(client, seeded, integ, db_session):
    eid = grade_final(client)
    integ.directory.down = True
    r = gen_final(client, eid)
    assert r.status_code == 502 and r.get_json()["code"] == "STUDENT_DIRECTORY_UNAVAILABLE"
    assert db_session.scalars(select(Acta)).all() == []
    assert [e for e in db_session.scalars(select(OutboxEvent)).all() if "acta" in e.event_type] == []


def test_missing_profile_uses_placeholder_and_warns(client, seeded, integ):
    eid = grade_final(client)
    del integ.directory.profiles["alumno-458"]
    a = gen_final(client, eid).get_json()
    assert a["warnings"] == ["PROFILE_MISSING:alumno-458"]
    row = next(r for r in a["rows"] if r["studentId"] == "alumno-458")
    assert row["studentName"] == "alumno-458" and row["studentFileNumber"] == "S/D"


def test_snapshots_survive_course_changes(client, seeded, integ):
    eid = grade_final(client)
    a = gen_final(client, eid).get_json()
    d = integ.academic.courses[42]
    integ.academic.courses[42] = dataclasses.replace(d, subject=Subject(15, "DDA2", "Otro nombre"))
    got = client.get(f"/api/v1/actas/{a['id']}", headers=H).get_json()
    assert got["subject"] == "Desarrollo de Aplicaciones II"


def test_outbox_event_exists_iff_acta_committed(client, seeded, db_session):
    eid = grade_final(client)
    gen_final(client, eid)
    gen_final(client, eid)  # 409: must not add another event
    evs = [
        e
        for e in db_session.scalars(select(OutboxEvent)).all()
        if e.event_type == "teacher.acta-generated.v1"
    ]
    assert len(evs) == 1
    d = evs[0].payload["data"]
    assert d["number"] == "2026-001" and d["counts"]["approved"] == 1 and len(d["results"]) == 3


def test_list_and_visibility(client, seeded_with_acta):
    r = client.get("/api/v1/actas", headers=H)
    body = r.get_json()
    assert body["total"] == 1 and body["limit"] == 50 and body["offset"] == 0
    assert "rows" not in body["items"][0] and body["items"][0]["number"] == "2026-001"
    assert client.get("/api/v1/actas?type=CURSADA", headers=H).get_json()["total"] == 0
    assert client.get("/api/v1/actas?courseId=42&status=GENERADA&limit=1", headers=H).get_json()["total"] == 1
    other = as_teacher("docente-124")
    assert client.get("/api/v1/actas", headers=other).get_json()["total"] == 0
    aid = body["items"][0]["id"]
    assert client.get(f"/api/v1/actas/{aid}", headers=other).status_code == 404
    assert (
        client.post(
            f"/api/v1/actas/{aid}/annulment", headers=other, json={"reason": "Motivo suficiente"}
        ).status_code
        == 404
    )
    assert client.get("/api/v1/actas/999", headers=H).get_json()["code"] == "ACTA_NOT_FOUND"
    assert client.get("/api/v1/actas?limit=500", headers=H).status_code == 400


def test_seeded_acta_blocks_duplicate_final(client, seeded_with_acta):
    eid = exam_id(client, "FINAL")
    r = gen_final(client, eid)
    assert r.status_code == 409 and r.get_json()["code"] == "ACTA_ALREADY_EXISTS"


def test_parallel_generation_one_winner(app, seeded):
    c0 = app.test_client()
    eid = grade_final(c0)
    codes: list[int] = []

    def worker():
        codes.append(
            app.test_client()
            .post("/api/v1/actas", headers=H, json={"courseId": 42, "type": "FINAL", "examId": eid})
            .status_code
        )

    threads = [threading.Thread(target=worker) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(codes) == [201, 409, 409, 409, 409], codes


def test_parallel_numbering_unique_and_gap_free(app, seeded):
    """CURSADA actas for two different courses generated at the same time get distinct, consecutive numbers."""
    h124 = as_teacher("docente-124")
    c = app.test_client()
    ids = [f"alumno-{100 + i}" for i in range(1, 21)]
    r = c.put(
        "/api/v1/courses/43/attendances/2026-10-12",
        headers=h124,
        json={"records": [{"studentId": s, "status": "PRESENTE"} for s in ids]},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    numbers: list[str] = []

    def worker(course, headers):
        r = app.test_client().post(
            "/api/v1/actas", headers=headers, json={"courseId": course, "type": "CURSADA"}
        )
        assert r.status_code == 201, r.get_data(as_text=True)
        numbers.append(r.get_json()["number"])

    threads = [
        threading.Thread(target=worker, args=(42, H)),
        threading.Thread(target=worker, args=(43, h124)),
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(numbers) == ["2026-001", "2026-002"]
