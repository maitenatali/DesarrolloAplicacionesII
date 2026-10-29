from tests.helpers import ROSTER_42, as_service, as_teacher

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
    assert body["studentId"] == JUAN and body["passingGrade"] == 4.0 and body["average"] == 8.0
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
