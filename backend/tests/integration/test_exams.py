from datetime import date

from freezegun import freeze_time
from sqlalchemy import select

from app.models import Examen, OutboxEvent
from tests.helpers import as_teacher, exam_body

URL = "/api/v1/courses/42/exams"


def create(client, **over):
    return client.post(URL, headers=as_teacher(), json=exam_body(**over))


def test_create_returns_201_location_and_event(client, db_session):
    r = create(client)
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert r.headers["Location"] == f"/api/v1/courses/42/exams/{body['id']}"
    assert body["type"] == "PARCIAL_2" and body["status"] == "PROGRAMADO" and body["phase"] == "UPCOMING"
    assert body["endTime"] == "20:00" and body["gradedCount"] == 0 and body["createdAt"].endswith("Z")
    ev = db_session.scalars(select(OutboxEvent)).all()
    assert (
        len(ev) == 1
        and ev[0].event_type == "teacher.exam-created.v1"
        and ev[0].subject == f"exam/{body['id']}"
    )
    assert ev[0].payload["data"]["startTime"] == "18:00"
    exam = db_session.scalar(select(Examen))
    assert exam.creado_por == "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"


def test_duplicate_type_then_cancel_frees_slot(client):
    first = create(client).get_json()
    r = create(client, type="PARCIAL_2")
    assert r.status_code == 409 and r.get_json()["code"] == "EXAM_TYPE_ALREADY_EXISTS"
    assert client.post(f"{URL}/{first['id']}/cancellation", headers=as_teacher(), json={}).status_code == 200
    assert create(client).status_code == 201


def test_type_normalisation_and_defaults(client):
    r = create(client, type="parcial 3", name=None)
    assert (
        r.status_code == 201 and r.get_json()["type"] == "PARCIAL_3" and r.get_json()["name"] == "Parcial 3"
    )
    r = create(client, type="x y!")
    assert r.status_code == 400 and r.get_json()["code"] == "VALIDATION_ERROR"
    assert create(client, type="recup-1").get_json()["type"] == "RECUP_1"


def test_validation(client):
    assert create(client, date="2026-10-18").status_code == 400  # past on create (today 2026-10-19)
    assert create(client, durationMinutes=0).status_code == 400
    assert create(client, durationMinutes=601).status_code == 400
    assert create(client, modality="HIBRIDA").status_code == 400
    r = create(client, surprise=1)
    assert r.status_code == 400 and r.get_json()["code"] == "VALIDATION_ERROR"
    assert create(client, startTime="25:00").status_code == 400


def test_cancelled_course_409(client):
    r = client.post("/api/v1/courses/44/exams", headers=as_teacher(), json=exam_body())
    assert r.status_code == 409 and r.get_json()["code"] == "COURSE_CANCELLED"


def test_patch_allows_past_date_and_refreshes(client):
    e = create(client).get_json()
    r = client.patch(
        f"{URL}/{e['id']}", headers=as_teacher(), json={"date": "2026-10-01", "description": "x"}
    )
    assert (
        r.status_code == 200 and r.get_json()["date"] == "2026-10-01" and r.get_json()["description"] == "x"
    )
    assert r.get_json()["phase"] == "COMPLETED"
    r = client.patch(f"{URL}/{e['id']}", headers=as_teacher(), json={"description": None})
    assert r.get_json()["description"] is None


def test_patch_type_rules(client, seeded):
    h = as_teacher()
    exams = {e["type"]: e for e in client.get(URL, headers=h).get_json()}
    r = client.patch(f"{URL}/{exams['PARCIAL_1']['id']}", headers=h, json={"type": "TP_1"})
    assert r.status_code == 409 and r.get_json()["code"] == "EXAM_HAS_GRADES"
    r = client.patch(f"{URL}/{exams['PARCIAL_2']['id']}", headers=h, json={"type": "FINAL"})
    assert r.status_code == 409 and r.get_json()["code"] == "EXAM_TYPE_ALREADY_EXISTS"
    r = client.patch(f"{URL}/{exams['PARCIAL_2']['id']}", headers=h, json={"type": "tp 9"})
    assert r.status_code == 200 and r.get_json()["type"] == "TP_9"


def test_cancel_idempotent_keeps_grades_and_cancelled_is_immutable(client, seeded):
    h = as_teacher()
    p1 = next(e for e in client.get(URL, headers=h).get_json() if e["type"] == "PARCIAL_1")
    assert client.post(f"{URL}/{p1['id']}/cancellation", headers=h, json={"reason": "x"}).status_code == 200
    r = client.post(f"{URL}/{p1['id']}/cancellation", headers=h, json={})
    assert (
        r.status_code == 200
        and r.get_json()["status"] == "CANCELADO"
        and r.get_json()["phase"] == "CANCELLED"
    )
    assert client.get(f"{URL}/{p1['id']}", headers=h).get_json()["gradedCount"] == 2  # grades kept
    r = client.patch(f"{URL}/{p1['id']}", headers=h, json={"name": "nuevo"})
    assert r.status_code == 409 and r.get_json()["code"] == "EXAM_CANCELLED"


def test_cancel_blocked_by_valid_final_acta(client, seeded_with_acta):
    h = as_teacher()
    final = next(e for e in client.get(URL, headers=h).get_json() if e["type"] == "FINAL")
    r = client.post(f"{URL}/{final['id']}/cancellation", headers=h, json={})
    assert r.status_code == 409 and r.get_json()["code"] == "EXAM_HAS_ACTA"


def test_phase_rules(client):
    h = as_teacher()
    past = create(client, type="TP_1", date="2026-10-19", startTime="09:00", durationMinutes=120).get_json()
    running = create(
        client, type="TP_2", date="2026-10-19", startTime="11:00", durationMinutes=120
    ).get_json()
    later = create(client, type="RECUP_1", date="2026-10-19", startTime="18:00").get_json()
    assert (past["phase"], running["phase"], later["phase"]) == ("COMPLETED", "UPCOMING", "UPCOMING")
    with freeze_time("2026-10-19 23:30:00"):  # 20:30 local: the 18:00-20:00 exam is over
        assert client.get(f"{URL}/{later['id']}", headers=h).get_json()["phase"] == "COMPLETED"


def test_detail_grading_progress_and_other_course_404(client, seeded):
    h = as_teacher()
    p1 = next(e for e in client.get(URL, headers=h).get_json() if e["type"] == "PARCIAL_1")
    d = client.get(f"{URL}/{p1['id']}", headers=h).get_json()
    assert d["gradingProgress"] == {"enrolled": 3, "graded": 2, "absent": 1, "pending": 0}
    r = client.get(f"/api/v1/courses/44/exams/{p1['id']}", headers=h)  # exam of course 42 via course 44
    assert r.status_code == 404 and r.get_json()["code"] == "EXAM_NOT_FOUND"


def test_my_exams_across_courses(client, seeded):
    h = as_teacher()
    upcoming = client.get("/api/v1/exams?phase=UPCOMING", headers=h).get_json()
    assert [e["type"] for e in upcoming] == ["FINAL"]
    assert upcoming[0]["course"] == {
        "id": 42,
        "code": "DDA2-A",
        "subjectName": "Desarrollo de Aplicaciones II",
    }
    allx = client.get("/api/v1/exams?from=2026-01-01&to=2026-12-31", headers=h).get_json()
    assert [e["type"] for e in allx] == ["PARCIAL_1", "PARCIAL_2", "FINAL"]
    limited = client.get("/api/v1/exams?from=2026-01-01&limit=2", headers=h).get_json()
    assert len(limited) == 2
    assert client.get("/api/v1/exams?phase=BOGUS", headers=h).status_code == 400


def test_list_exams_includes_cancelled(client, seeded):
    h = as_teacher()
    p2 = next(e for e in client.get(URL, headers=h).get_json() if e["type"] == "PARCIAL_2")
    client.post(f"{URL}/{p2['id']}/cancellation", headers=h, json={})
    got = client.get(URL, headers=h).get_json()
    assert [e["phase"] for e in got if e["type"] == "PARCIAL_2"] == ["CANCELLED"]
    assert client.get("/api/v1/exams?from=2026-01-01", headers=h).get_json().__len__() == 2
    assert (
        client.get("/api/v1/exams?from=2026-01-01&includeCancelled=true", headers=h).get_json().__len__() == 3
    )


def test_date_constant():
    assert date(2026, 10, 19).isoformat() == "2026-10-19"
