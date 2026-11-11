from tests.helpers import ROSTER_42, as_service, as_teacher, exam_body

JUAN, LUCAS, ANA = ROSTER_42
OUTSIDER = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"


def as_student(student_id: str) -> dict[str, str]:
    return {"X-Dev-User": student_id, "X-Dev-Roles": "STUDENT"}


def att(student_id: str, course_id: int = 42) -> str:
    return f"/api/v1/students/{student_id}/courses/{course_id}/attendance"


def grades(student_id: str, course_id: int = 42) -> str:
    return f"/api/v1/students/{student_id}/courses/{course_id}/grades"


def test_attendance_returns_only_that_student_with_every_class(client, seeded):
    r = client.get(att(LUCAS), headers=as_service())
    assert r.status_code == 200
    body = r.get_json()
    assert body["studentId"] == LUCAS and body["courseId"] == 42 and body["threshold"] == 75.0
    assert (body["classesRecorded"], body["present"], body["absences"], body["justified"]) == (4, 2, 2, 0)
    assert body["attendancePercentage"] == 50.0 and body["condition"] == "LIBRE"
    assert [c["date"] for c in body["classes"]] == ["2026-08-11", "2026-08-18", "2026-08-25", "2026-09-01"]
    assert [c["status"] for c in body["classes"]] == ["PRESENTE", "AUSENTE", "PRESENTE", "AUSENTE"]


def test_attendance_justified_counts_and_note(client, seeded):
    body = client.get(att(ANA), headers=as_service()).get_json()
    assert body["condition"] == "REGULAR" and body["justified"] == 1
    assert body["classes"][1] == {"date": "2026-08-18", "status": "JUSTIFICADO", "note": "Certificado médico"}


def test_attendance_without_classes_is_zero_and_libre(client):
    body = client.get(att(JUAN), headers=as_service()).get_json()
    assert body["classesRecorded"] == 0 and body["condition"] == "LIBRE" and body["classes"] == []


def test_grades_list_course_exams_with_the_student_grade(client, seeded):
    r = client.get(grades(JUAN), headers=as_service())
    assert r.status_code == 200
    body = r.get_json()
    assert body["studentId"] == JUAN and body["passingGrade"] == 4.0
    # Solo P1 cargado: todavía cursando, sin nota de cursada (nunca el "promedio de lo que haya").
    assert body["average"] is None and body["situation"]["status"] == "CURSANDO"
    assert body["situation"]["recupEnabled"] is False and body["situation"]["finalEnabled"] is False
    by = {e["type"]: e for e in body["exams"]}
    assert list(by) == ["PARCIAL_1", "PARCIAL_2", "FINAL"]
    p1 = by["PARCIAL_1"]
    assert p1["grade"] == 8.0 and p1["absent"] is False and p1["passed"] is True
    assert p1["category"] == "PARCIAL" and p1["gradedBy"] == "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"
    assert (
        by["FINAL"]["category"] == "FINAL" and by["FINAL"]["grade"] is None and by["FINAL"]["passed"] is None
    )
    assert "studentName" not in p1  # no data about other students


def test_grades_absent_student(client, seeded):
    body = client.get(grades(ANA), headers=as_service()).get_json()
    p1 = next(e for e in body["exams"] if e["type"] == "PARCIAL_1")
    assert p1["absent"] is True and p1["grade"] is None and body["average"] is None


def test_grades_situation_after_recup(client, seeded):
    """Juan: P1 = 8, P2 = 2 -> debe recuperar P2; con el recuperatorio (6) la cursada es (8 + 6) / 2."""
    h = as_teacher()
    exams = {e["type"]: e["id"] for e in client.get("/api/v1/courses/42/exams", headers=h).get_json()}
    put = lambda eid, g: client.put(  # noqa: E731
        f"/api/v1/courses/42/exams/{eid}/grades",
        headers=h,
        json={"entries": [{"studentId": JUAN, "grade": g}]},
    )
    assert put(exams["PARCIAL_2"], 2).status_code == 200
    s = client.get(grades(JUAN), headers=as_service()).get_json()["situation"]
    assert s["status"] == "DEBE_RECUPERAR_P2" and s["recovers"] == "P2" and s["recupEnabled"] is True
    recup = client.post(
        "/api/v1/courses/42/exams", headers=h, json=exam_body(type="RECUPERATORIO", date="2026-11-02")
    ).get_json()["id"]
    assert put(recup, 6).status_code == 200
    body = client.get(grades(JUAN), headers=as_service()).get_json()
    s = body["situation"]
    assert (s["status"], s["p2Effective"], s["cursadaGrade"], body["average"]) == (
        "PENDIENTE_FINAL",
        6.0,
        7.0,
        7.0,
    )
    assert s["finalEnabled"] is True and s["finalGrade"] is None


def test_student_can_read_own_data_only(client, seeded):
    assert client.get(att(JUAN), headers=as_student(JUAN)).status_code == 200
    assert client.get(grades(JUAN), headers=as_student(JUAN)).status_code == 200
    other = client.get(grades(LUCAS), headers=as_student(JUAN))
    assert other.status_code == 403 and other.get_json()["code"] == "FORBIDDEN"
    assert client.get(att(JUAN), headers=as_teacher()).status_code == 403
    assert client.get(att(JUAN)).status_code == 401


def test_not_enrolled_and_unknown_course(client, seeded):
    r = client.get(att(OUTSIDER), headers=as_service())
    assert r.status_code == 404 and r.get_json()["code"] == "STUDENT_NOT_ENROLLED"
    assert client.get(grades(OUTSIDER), headers=as_student(OUTSIDER)).status_code == 404
    r = client.get(grades(JUAN, course_id=99999), headers=as_service())
    assert r.status_code == 404 and r.get_json()["code"] == "COURSE_NOT_FOUND"
