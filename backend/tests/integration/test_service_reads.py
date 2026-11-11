"""Other modules (student, analytics, academic) READ our data with a service token; they never write."""

from tests.helpers import ROSTER_42, as_other_teacher, as_service, as_teacher, attendance_body, exam_body

JUAN, LUCAS, ANA = ROSTER_42
READS = [
    "/api/v1/courses/42/attendances",
    "/api/v1/courses/42/attendances/2026-08-11",
    "/api/v1/courses/42/attendance-summary",
    "/api/v1/courses/42/exams",
    "/api/v1/courses/42/grades",
    "/api/v1/actas",
]


def test_service_token_reads_course_data(client, seeded):
    for url in READS:
        r = client.get(url, headers=as_service())
        assert r.status_code == 200, (url, r.get_json())


def test_service_reads_exam_detail_and_exam_grades(client, seeded):
    exams = client.get("/api/v1/courses/42/exams", headers=as_service()).get_json()
    exam_id = exams[0]["id"] if isinstance(exams, list) else exams["items"][0]["id"]
    assert client.get(f"/api/v1/courses/42/exams/{exam_id}", headers=as_service()).status_code == 200
    assert client.get(f"/api/v1/courses/42/exams/{exam_id}/grades", headers=as_service()).status_code == 200


def test_service_sees_all_actas_and_filters_by_student(client, seeded_with_acta):
    body = client.get("/api/v1/actas", headers=as_service()).get_json()
    assert body["total"] >= 1
    acta_id = body["items"][0]["id"]
    detail = client.get(f"/api/v1/actas/{acta_id}", headers=as_service())
    assert detail.status_code == 200
    mine = client.get(f"/api/v1/actas?studentId={JUAN}", headers=as_service()).get_json()
    assert mine["total"] >= 1
    nobody = client.get("/api/v1/actas?studentId=eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", headers=as_service())
    assert nobody.get_json()["total"] == 0


def test_service_cannot_write_anything(client, seeded):
    assert client.put(
        "/api/v1/courses/42/attendances/2026-09-08", json=attendance_body(), headers=as_service()
    ).status_code in (401, 403)
    created = client.post("/api/v1/courses/42/exams", json=exam_body(), headers=as_service())
    assert created.status_code in (401, 403)
    assert client.put(
        "/api/v1/courses/42/exams/1/grades",
        json={"entries": [{"studentId": JUAN, "grade": 9}]},
        headers=as_service(),
    ).status_code in (401, 403)
    assert client.post("/api/v1/actas", json={}, headers=as_service()).status_code in (401, 403)


def test_no_token_is_401_and_a_student_is_403(client, seeded):
    for url in READS:
        assert client.get(url).status_code == 401
        student = {"X-Dev-User": JUAN, "X-Dev-Roles": "STUDENT"}
        assert client.get(url, headers=student).status_code == 403


def test_teachers_keep_ownership_rules(client, seeded):
    assert client.get("/api/v1/courses/42/grades", headers=as_teacher()).status_code == 200
    other = client.get("/api/v1/courses/42/grades", headers=as_other_teacher())
    assert other.status_code == 403 and other.get_json()["code"] == "COURSE_NOT_ASSIGNED"
    # the other teacher doesn't see actas that aren't theirs
    assert client.get("/api/v1/actas", headers=as_other_teacher()).get_json()["total"] == 0
