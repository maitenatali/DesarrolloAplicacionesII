from tests.helpers import as_admin, as_other_teacher, as_service, as_teacher


def test_me(client):
    r = client.get("/api/v1/me", headers=as_teacher())
    assert r.status_code == 200
    body = r.get_json()
    assert body["userId"] == "docente-123" and body["teacherIds"] == ["docente-123"]


def test_teacher_sees_only_own_courses_sorted(client):
    r = client.get("/api/v1/courses", headers=as_teacher())
    assert r.status_code == 200
    assert [c["id"] for c in r.get_json()] == [44, 42, 30] or [c["id"] for c in r.get_json()] == [42, 44, 30]
    other = client.get("/api/v1/courses", headers=as_other_teacher()).get_json()
    assert other == []


def test_course_list_period_filter_and_shape(client):
    body = client.get("/api/v1/courses?periodId=7", headers=as_teacher()).get_json()
    assert [c["id"] for c in body] == [30]
    c = client.get("/api/v1/courses/42", headers=as_teacher()).get_json()
    assert c["subject"] == {"id": 15, "code": "DDA2", "name": "Desarrollo de Aplicaciones II"}
    assert c["period"]["label"] == "2° Cuatrimestre 2026"
    assert c["schedule"] == [{"roomId": 4, "weekday": "MONDAY", "startTime": "18:00", "endTime": "20:00"}]
    assert c["teachers"] == [{"teacherId": "docente-123", "role": "TITULAR"}]


def test_foreign_course_is_403_and_unknown_is_404(client):
    r = client.get("/api/v1/courses/43", headers=as_teacher())
    assert r.status_code == 403 and r.get_json()["code"] == "COURSE_NOT_ASSIGNED"
    r = client.get("/api/v1/courses/9999", headers=as_teacher())
    assert r.status_code == 404 and r.get_json()["code"] == "COURSE_NOT_FOUND"


def test_admin_can_read_but_not_write_foreign_course(client):
    assert client.get("/api/v1/courses/43", headers=as_admin()).status_code == 200
    r = client.post(
        "/api/v1/courses/43/exams",
        headers=as_admin(),
        json={
            "type": "TP_1",
            "date": "2026-11-01",
            "startTime": "10:00",
            "durationMinutes": 60,
            "modality": "VIRTUAL",
        },
    )
    assert r.status_code == 403


def test_roster_with_attendance_and_final_result(client, seeded_with_acta):
    body = client.get("/api/v1/courses/42/students", headers=as_teacher()).get_json()
    assert [s["studentId"] for s in body] == ["alumno-456", "alumno-457", "alumno-458"]
    s456, s457 = body[0], body[1]
    assert s456["profile"]["fullName"] == "Juan Pérez" and s456["profile"]["fileNumber"] == "123456"
    assert s456["attendance"] == {
        "classesRecorded": 4,
        "present": 4,
        "justified": 0,
        "absences": 0,
        "attendancePercentage": 100.0,
        "condition": "REGULAR",
    }
    assert s457["attendance"]["condition"] == "LIBRE" and s457["attendance"]["attendancePercentage"] == 50.0
    assert s456["finalResult"] == {
        "grade": 8.0,
        "result": "APROBADO",
        "actaNumber": "2026-001",
        "date": "2026-12-03",
    }
    assert body[2]["finalResult"]["grade"] is None and body[2]["finalResult"]["result"] == "AUSENTE"


def test_roster_excludes_baja_and_degrades_when_directory_down(client, integ):
    import dataclasses

    d = integ.academic.courses[42]
    integ.academic.courses[42] = dataclasses.replace(
        d,
        enrollments=d.enrollments
        + [dataclasses.replace(d.enrollments[0], id=99, student_id="alumno-999", status="BAJA")],
    )
    assert len(client.get("/api/v1/courses/42/students", headers=as_teacher()).get_json()) == 3
    integ.directory.down = True
    r = client.get("/api/v1/courses/42/students", headers=as_teacher())
    assert r.status_code == 200 and r.headers["X-Degraded"] == "student-directory"
    assert all(s["profile"] is None for s in r.get_json())


def test_unknown_profile_is_null(client, integ):
    del integ.directory.profiles["alumno-458"]
    body = client.get("/api/v1/courses/42/students", headers=as_teacher()).get_json()
    assert body[-1]["studentId"] == "alumno-458" and body[-1]["profile"] is None


def test_ga_failure_is_502_or_504_never_demo_data(client, integ):
    integ.academic.down = True
    r = client.get("/api/v1/courses", headers=as_teacher())
    assert r.status_code == 504 and r.get_json()["code"] == "UPSTREAM_TIMEOUT"


def test_periods_turns_prereqs_types(client):
    p = client.get("/api/v1/periods", headers=as_teacher()).get_json()
    assert p[1]["label"] == "2° Cuatrimestre 2026" and p[1]["enrollmentFrom"] == "2026-07-01"
    assert (
        client.get("/api/v1/exam-turns", headers=as_teacher()).get_json()[0]["name"]
        == "Turno final diciembre"
    )
    pre = client.get("/api/v1/courses/42/prerequisites", headers=as_teacher()).get_json()
    assert pre == [
        {"id": 5, "prerequisiteSubjectId": 12, "kind": "APROBADA"},
        {"id": 6, "prerequisiteSubjectId": 13, "kind": "REGULAR"},
    ]
    assert {t["type"] for t in client.get("/api/v1/exam-types", headers=as_teacher()).get_json()} >= {"FINAL"}


def test_service_token_cannot_use_teacher_routes(client):
    assert client.get("/api/v1/courses", headers=as_service()).status_code == 401
