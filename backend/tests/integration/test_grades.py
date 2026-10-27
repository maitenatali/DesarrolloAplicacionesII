from sqlalchemy import select

from app.models import Calificacion, OutboxEvent
from tests.helpers import as_other_teacher, as_teacher, exam_body

EX = "/api/v1/courses/42/exams"


def exam_id(client, tipo):
    return next(e["id"] for e in client.get(EX, headers=as_teacher()).get_json() if e["type"] == tipo)


def put(client, eid, entries, headers=None):
    return client.put(f"{EX}/{eid}/grades", headers=headers or as_teacher(), json={"entries": entries})


def grade_events(db_session):
    return [
        e
        for e in db_session.scalars(select(OutboxEvent)).all()
        if e.event_type == "teacher.grade-published.v1"
    ]


def test_get_lists_every_enrolled_student(client, seeded):
    eid = exam_id(client, "PARCIAL_1")
    r = client.get(f"{EX}/{eid}/grades", headers=as_teacher())
    assert r.status_code == 200
    body = r.get_json()
    by = {e["studentId"]: e for e in body["entries"]}
    assert (
        by["ba310c57-a684-4dbf-a4a4-905fcfbefa08"]["grade"] == 8.0
        and by["ba310c57-a684-4dbf-a4a4-905fcfbefa08"]["studentName"] == "Juan Pérez"
    )
    assert (
        by["ba310c57-a684-4dbf-a4a4-905fcfbefa08"]["fileNumber"] == "123456"
        and by["ba310c57-a684-4dbf-a4a4-905fcfbefa08"]["gradedBy"] == "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"
    )
    assert (
        by["d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58"]["absent"] is True
        and by["d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58"]["grade"] is None
    )
    assert body["summary"] == {
        "enrolled": 3,
        "graded": 2,
        "absent": 1,
        "pending": 0,
        "average": 6.5,
        "passed": 2,
        "failed": 0,
    }
    p2 = exam_id(client, "PARCIAL_2")
    s = client.get(f"{EX}/{p2}/grades", headers=as_teacher()).get_json()["summary"]
    assert (
        s["pending"] == 3
        and s["average"] is None
        and all(
            e["gradedAt"] is None
            for e in client.get(f"{EX}/{p2}/grades", headers=as_teacher()).get_json()["entries"]
        )
    )


def test_upsert_update_and_resend_emit_events_only_on_change(client, seeded, db_session):
    eid = exam_id(client, "PARCIAL_2")
    n0 = len(grade_events(db_session))
    r = put(
        client,
        eid,
        [
            {"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 8.5, "absent": False},
            {"studentId": "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", "grade": None, "absent": True},
        ],
    )
    assert r.status_code == 200 and r.get_json()["saved"] == 2 and r.get_json()["cleared"] == 0
    assert len(grade_events(db_session)) == n0 + 1
    ev = grade_events(db_session)[-1].payload["data"]
    assert ev["grades"] == [
        {"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 8.5, "status": "APROBADO"}
    ]  # absent not published
    put(
        client, eid, [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 9, "absent": False}]
    )  # changed
    assert len(grade_events(db_session)) == n0 + 2
    put(
        client, eid, [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 9.0, "absent": False}]
    )  # unchanged re-save
    assert len(grade_events(db_session)) == n0 + 2
    row = db_session.scalar(
        select(Calificacion).where(
            Calificacion.examen_id == eid, Calificacion.alumno_id == "ba310c57-a684-4dbf-a4a4-905fcfbefa08"
        )
    )
    assert str(row.nota) == "9.00" and row.cargada_por == "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"


def test_null_grade_not_absent_deletes_row(client, seeded, db_session):
    eid = exam_id(client, "PARCIAL_1")
    r = put(
        client, eid, [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": None, "absent": False}]
    )
    assert r.get_json()["cleared"] == 1 and r.get_json()["saved"] == 0
    assert (
        db_session.scalar(
            select(Calificacion).where(
                Calificacion.examen_id == eid,
                Calificacion.alumno_id == "ba310c57-a684-4dbf-a4a4-905fcfbefa08",
            )
        )
        is None
    )


def test_validation_all_or_nothing(client, seeded, db_session):
    eid = exam_id(client, "PARCIAL_2")
    ok = {"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 7, "absent": False}
    for bad, code in (
        (
            {"studentId": "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", "grade": 7, "absent": True},
            "GRADE_WITH_ABSENT",
        ),
        (
            {"studentId": "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", "grade": 10.01, "absent": False},
            "VALIDATION_ERROR",
        ),
        (
            {"studentId": "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", "grade": 7.123, "absent": False},
            "VALIDATION_ERROR",
        ),
        (
            {"studentId": "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", "grade": -1, "absent": False},
            "VALIDATION_ERROR",
        ),
        (
            {"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 5, "absent": False},
            "DUPLICATE_STUDENT",
        ),
        (
            {"studentId": "00000000-0000-4000-8000-000000000000", "grade": 5, "absent": False},
            "STUDENT_NOT_ENROLLED",
        ),
    ):
        r = put(client, eid, [ok, bad])
        assert r.status_code == 400 and r.get_json()["code"] == code, (bad, r.get_json())
    assert db_session.scalars(select(Calificacion).where(Calificacion.examen_id == eid)).all() == []
    assert grade_events(db_session) == []
    assert put(client, eid, []).status_code == 400


def test_boundary_grades_ok(client, seeded):
    eid = exam_id(client, "PARCIAL_2")
    r = put(
        client,
        eid,
        [
            {"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 0, "absent": False},
            {"studentId": "c3a1e0d2-5b6f-4c7a-8d9e-0f1a2b3c4d57", "grade": 10, "absent": False},
            {"studentId": "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58", "grade": 4.25, "absent": False},
        ],
    )
    assert r.status_code == 200 and r.get_json()["saved"] == 3


def test_cancelled_exam_and_foreign_teacher(client, seeded):
    eid = exam_id(client, "PARCIAL_2")
    assert (
        put(
            client,
            eid,
            [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 7}],
            as_other_teacher(),
        ).status_code
        == 403
    )
    client.post(f"{EX}/{eid}/cancellation", headers=as_teacher(), json={})
    r = put(client, eid, [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 7}])
    assert r.status_code == 409 and r.get_json()["code"] == "EXAM_CANCELLED"


def test_locked_by_valid_final_acta(client, seeded_with_acta):
    eid = exam_id(client, "FINAL")
    r = put(client, eid, [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 7}])
    assert r.status_code == 409 and r.get_json()["code"] == "EXAM_LOCKED_BY_ACTA"


def test_matrix_non_cancelled_only(client, seeded):
    h = as_teacher()
    p2 = exam_id(client, "PARCIAL_2")
    put(client, p2, [{"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "grade": 7, "absent": False}])
    cancelled = client.post(f"{EX}", headers=h, json=exam_body(type="TP_1")).get_json()["id"]
    client.post(f"{EX}/{cancelled}/cancellation", headers=h, json={})
    m = client.get("/api/v1/courses/42/grades", headers=h).get_json()
    assert [e["type"] for e in m["exams"]] == ["PARCIAL_1", "PARCIAL_2", "FINAL"]
    row = next(r for r in m["rows"] if r["studentId"] == "ba310c57-a684-4dbf-a4a4-905fcfbefa08")
    p1 = exam_id(client, "PARCIAL_1")
    assert row["grades"][str(p1)] == {"grade": 8.0, "absent": False} and row["average"] == 7.5
    r458 = next(r for r in m["rows"] if r["studentId"] == "d4b2f1e3-6c7a-4d8b-9eaf-102b3c4d5e58")
    assert r458["average"] is None and r458["grades"][str(p1)]["absent"] is True
