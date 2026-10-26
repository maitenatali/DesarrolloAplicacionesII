from sqlalchemy import select

from app.models import Asistencia, Clase, OutboxEvent
from tests.helpers import ROSTER_42, as_other_teacher, as_teacher, attendance_body

URL = "/api/v1/courses/42/attendances"


def outbox(db_session, event_type=None):
    q = select(OutboxEvent)
    if event_type:
        q = q.where(OutboxEvent.event_type == event_type)
    return db_session.scalars(q).all()


def test_put_creates_then_replaces(client, db_session):
    day = "2026-10-12"
    r = client.put(f"{URL}/{day}", headers=as_teacher(), json=attendance_body(notes="Primera"))
    assert r.status_code == 201, r.get_data(as_text=True)
    assert len(r.get_json()["records"]) == 3
    marks = {"alumno-456": "AUSENTE", "alumno-457": "JUSTIFICADO", "alumno-458": "PRESENTE"}
    body = attendance_body(marks, notes="Corregida")
    body["records"][1]["note"] = "Certificado"
    r = client.put(f"{URL}/{day}", headers=as_teacher("docente-123"), json=body)
    assert r.status_code == 200
    got = {x["studentId"]: x for x in r.get_json()["records"]}
    assert got["alumno-456"]["status"] == "AUSENTE" and got["alumno-457"]["note"] == "Certificado"
    assert r.get_json()["notes"] == "Corregida"
    clase = db_session.scalar(select(Clase))
    assert clase.creado_por == "docente-123"
    assert len(db_session.scalars(select(Asistencia)).all()) == 3  # no leftovers
    assert len(outbox(db_session, "teacher.attendance-recorded.v1")) == 2


def test_event_payload(client, db_session):
    client.put(
        f"{URL}/2026-10-12",
        headers=as_teacher(),
        json=attendance_body(
            {"alumno-456": "PRESENTE", "alumno-457": "AUSENTE", "alumno-458": "JUSTIFICADO"}
        ),
    )
    ev = outbox(db_session)[0].payload
    assert (
        ev["eventType"] == "teacher.attendance-recorded.v1"
        and ev["subject"] == "course/42/attendance/2026-10-12"
    )
    assert ev["data"]["counts"] == {"present": 1, "absent": 1, "justified": 1}
    assert ev["source"] == "teacher" and ev["actor"]["id"] == "docente-123" and ev["correlationId"]


def test_validation_errors(client, db_session):
    h = as_teacher()
    r = client.put(f"{URL}/2026-10-20", headers=h, json=attendance_body())  # tomorrow vs frozen 2026-10-19
    assert r.status_code == 400 and r.get_json()["code"] == "DATE_IN_FUTURE"
    dup = attendance_body()
    dup["records"].append({"studentId": "alumno-456", "status": "AUSENTE"})
    r = client.put(f"{URL}/2026-10-12", headers=h, json=dup)
    assert r.status_code == 400 and r.get_json()["code"] == "DUPLICATE_STUDENT"
    unknown = attendance_body()
    unknown["records"][0]["studentId"] = "alumno-000"
    r = client.put(f"{URL}/2026-10-12", headers=h, json=unknown)
    assert r.status_code == 400 and r.get_json()["code"] == "STUDENT_NOT_ENROLLED"
    partial = {"records": [{"studentId": "alumno-456", "status": "PRESENTE"}]}
    r = client.put(f"{URL}/2026-10-12", headers=h, json=partial)
    assert r.status_code == 400 and r.get_json()["code"] == "INCOMPLETE_ROSTER"
    assert {e["message"] for e in r.get_json()["errors"]} == {"Falta alumno-457.", "Falta alumno-458."}
    bad = attendance_body()
    bad["records"][0]["status"] = "X"
    assert client.put(f"{URL}/2026-10-12", headers=h, json=bad).get_json()["code"] == "VALIDATION_ERROR"
    assert client.put(f"{URL}/not-a-date", headers=h, json=attendance_body()).status_code == 400
    assert outbox(db_session) == [] and db_session.scalars(select(Clase)).all() == []  # nothing persisted


def test_not_assigned_is_403(client):
    r = client.put(f"{URL}/2026-10-12", headers=as_other_teacher(), json=attendance_body())
    assert r.status_code == 403 and r.get_json()["code"] == "COURSE_NOT_ASSIGNED"


def test_get_list_and_not_recorded(client, seeded):
    h = as_teacher()
    r = client.get(f"{URL}/2026-08-18", headers=h)
    assert r.status_code == 200
    recs = {x["studentId"]: x for x in r.get_json()["records"]}
    assert recs["alumno-458"] == {
        "studentId": "alumno-458",
        "status": "JUSTIFICADO",
        "note": "Certificado médico",
    }
    r = client.get(f"{URL}/2026-01-01", headers=h)
    assert r.status_code == 404 and r.get_json()["code"] == "ATTENDANCE_NOT_RECORDED"
    items = client.get(URL, headers=h).get_json()
    assert [i["date"] for i in items] == ["2026-09-01", "2026-08-25", "2026-08-18", "2026-08-11"]
    assert items[2] == {
        "date": "2026-08-18",
        "notes": None,
        "total": 3,
        "present": 1,
        "absent": 1,
        "justified": 1,
        "updatedAt": items[2]["updatedAt"],
    }


def test_summary_matches_seed(client, seeded):
    s = client.get("/api/v1/courses/42/attendance-summary", headers=as_teacher()).get_json()
    assert s["threshold"] == 75.0
    by = {x["studentId"]: x for x in s["students"]}
    assert (by["alumno-456"]["condition"], by["alumno-456"]["attendancePercentage"]) == ("REGULAR", 100.0)
    assert (by["alumno-457"]["condition"], by["alumno-457"]["attendancePercentage"]) == ("LIBRE", 50.0)
    assert by["alumno-458"]["justified"] == 1 and by["alumno-458"]["condition"] == "REGULAR"


def test_summary_omits_students_without_rows(client):
    assert (
        client.get("/api/v1/courses/42/attendance-summary", headers=as_teacher()).get_json()["students"] == []
    )


def test_locked_by_cursada_acta_until_annulled(client, seeded):
    h = as_teacher()
    acta = client.post("/api/v1/actas", headers=h, json={"courseId": 42, "type": "CURSADA"})
    assert acta.status_code == 201, acta.get_data(as_text=True)
    r = client.put(f"{URL}/2026-10-12", headers=h, json=attendance_body())
    assert r.status_code == 409 and r.get_json()["code"] == "ATTENDANCE_LOCKED_BY_ACTA"
    assert (
        client.post(
            f"/api/v1/actas/{acta.get_json()['id']}/annulment",
            headers=h,
            json={"reason": "Corrección de asistencia"},
        ).status_code
        == 200
    )
    assert client.put(f"{URL}/2026-10-12", headers=h, json=attendance_body()).status_code == 201


def test_roster_constant():
    assert ROSTER_42 == ["alumno-456", "alumno-457", "alumno-458"]
