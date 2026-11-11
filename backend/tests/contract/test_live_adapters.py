"""Outbound contract tests: live adapters against recorded-style GA / CORE payloads (requests-mock)."""

from datetime import date
from decimal import Decimal

import pytest
import requests
import requests_mock

from app.errors import CourseNotFound, PublishError, StudentDirectoryUnavailable, UpstreamError
from app.integrations.academic_live import AcademicLive
from app.integrations.core_events_live import CoreEventsLive
from app.integrations.http import HttpClient
from app.integrations.outbound_auth import ServiceTokenAuth, StaticBearer
from app.integrations.student_directory_live import StudentDirectoryLive
from app.integrations.token_provider import TokenProvider

GA = "https://gw.test/api/v1/academic"
CORE = "https://core.test"

PERIODO = {
    "id": 8,
    "anio": 2026,
    "numero": 2,
    "fechaInicio": "2026-08-01",
    "fechaFin": "2026-11-30",
    "inscripcionDesde": "2026-07-01",
    "inscripcionHasta": "2026-07-31",
}
CURSO_42 = {
    "curso": {
        "id": 42,
        "codigo": "DDA2-A",
        "estado": "EN_CURSO",
        "modalidad": "PRESENCIAL",
        "sedeId": 2,
        "cupoMaximo": 45,
        "fechaInicio": "2026-08-10",
        "fechaFin": "2026-11-30",
        "asignatura": {"id": 15, "codigo": "DDA2", "nombre": "Desarrollo de Aplicaciones II"},
        "periodo": PERIODO,
    },
    "docentes": [{"id": 3, "docenteId": "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", "rol": "TITULAR"}],
    "inscripciones": [
        {
            "id": 71,
            "alumnoId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08",
            "fechaInscripcion": "2026-07-15",
            "estado": "CURSANDO",
        },
        {
            "id": 74,
            "alumnoId": "00000000-0000-4000-8000-000000000999",
            "fechaInscripcion": "2026-07-15",
            "estado": "BAJA",
            "notaFinal": 7,
        },
    ],
    "horarios": [
        {"id": 9, "aulaId": 4, "diaSemana": "MONDAY", "horaInicio": "18:00:00", "horaFin": "20:00:00"}
    ],
}


def ga(auth=None, **kw):
    return AcademicLive(HttpClient("academic", GA, auth or StaticBearer("tok"), max_retries=0), **kw)


def test_get_course_normalises_spanish_payload_and_caches():
    with requests_mock.Mocker() as m:
        m.get(f"{GA}/planificacion/cursos/42", json=CURSO_42)
        a = ga()
        d = a.get_course(42)
        assert (d.course.code, d.subject.name, d.period.label) == (
            "DDA2-A",
            "Desarrollo de Aplicaciones II",
            "2° Cuatrimestre 2026",
        )
        assert (
            d.teachers[0].teacher_id == "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"
            and d.schedule[0].weekday == "MONDAY"
        )
        assert [e.status for e in d.enrollments] == ["CURSANDO", "BAJA"] and d.course.active_enrolled == 1
        a.get_course(42)
        assert m.call_count == 1  # TTL cache
        a.get_course(42, fresh=True)
        assert m.call_count == 2
        assert m.request_history[0].headers["Authorization"] == "Bearer tok"


def test_course_not_found_and_server_errors():
    with requests_mock.Mocker() as m:
        m.get(f"{GA}/planificacion/cursos/1", status_code=404)
        m.get(f"{GA}/planificacion/cursos/2", status_code=503)
        m.get(f"{GA}/planificacion/cursos/3", status_code=400)
        m.get(f"{GA}/planificacion/cursos/4", exc=requests.exceptions.ConnectTimeout)
        a = ga()
        with pytest.raises(CourseNotFound):
            a.get_course(1)
        with pytest.raises(UpstreamError) as e:
            a.get_course(2)
        assert e.value.status == 502 and e.value.code == "UPSTREAM_ERROR"
        with pytest.raises(UpstreamError) as e:
            a.get_course(3)
        assert e.value.code == "UPSTREAM_REJECTED"
        with pytest.raises(UpstreamError) as e:
            a.get_course(4)
        assert e.value.status == 504 and e.value.code == "UPSTREAM_TIMEOUT"


def test_periods_turns_prereqs():
    with requests_mock.Mocker() as m:
        m.get(f"{GA}/planificacion/periodos", json=[PERIODO])
        m.get(
            f"{GA}/planificacion/turnos-examen",
            json=[
                {
                    "id": 7,
                    "nombre": "Turno final",
                    "fechaInicio": "2026-12-01",
                    "fechaFin": "2026-12-15",
                    "inscripcionDesde": "2026-11-10",
                    "inscripcionHasta": "2026-11-25",
                }
            ],
        )
        m.get(
            f"{GA}/academica/asignaturas/15/correlatividades",
            json=[{"id": 5, "asignaturaRequeridaId": 12, "tipo": "APROBADA"}],
        )
        a = ga()
        assert a.list_periods()[0].id == 8
        assert a.list_exam_turns()[0].name == "Turno final"
        p = a.list_prerequisites(15)[0]
        assert (p.subject_id, p.prerequisite_id, p.kind) == (15, 12, "APROBADA")


def test_list_courses_for_teacher_fanout_filters_by_docente():
    other = {
        **CURSO_42,
        "curso": {**CURSO_42["curso"], "id": 43},
        "docentes": [{"id": 4, "docenteId": "7c2f1a90-3d55-4e21-9b8c-0a1f4d6e2b34"}],
    }
    with requests_mock.Mocker() as m:
        m.get(
            f"{GA}/planificacion/cursos",
            json=[
                {"id": 42, "asignaturaId": 15, "periodoId": 8},
                {"id": 43, "asignaturaId": 15, "periodoId": 8},
            ],
        )
        m.get(f"{GA}/planificacion/cursos/42", json=CURSO_42)
        m.get(f"{GA}/planificacion/cursos/43", json=other)
        mine = ga().list_courses_for_teacher({"5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"}, period_id=8)
        assert [d.course.id for d in mine] == [42]
        assert m.request_history[0].qs == {"periodoid": ["8"]}


def test_list_courses_for_teacher_native_filter():
    with requests_mock.Mocker() as m:
        m.get(f"{GA}/planificacion/cursos", json=[{"id": 42}])
        m.get(f"{GA}/planificacion/cursos/42", json=CURSO_42)
        got = ga(supports_teacher_filter=True).list_courses_for_teacher(
            {"5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"}
        )
        assert [d.course.id for d in got] == [42]
        assert m.request_history[0].qs == {"docenteid": ["5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034"]}


def test_update_enrollment_result_put_body_and_url_encoding():
    with requests_mock.Mocker() as m:
        m.put(requests_mock.ANY, status_code=200, json={})
        ga().update_enrollment_result(
            42, "alumno/45 6", status="APROBADO", final_grade=Decimal("8.5"), result_date=date(2026, 12, 3)
        )
        req = m.request_history[0]
        assert req.method == "PUT" and req.url.endswith(
            "/planificacion/cursos/42/inscripciones/alumno%2F45%206"
        )
        assert req.json() == {"estado": "APROBADO", "notaFinal": 8.5, "fechaResultado": "2026-12-03"}
        ga().update_enrollment_result(
            42,
            "ba310c57-a684-4dbf-a4a4-905fcfbefa08",
            status="REGULAR",
            final_grade=None,
            result_date=date(2026, 12, 3),
        )
        assert m.request_history[1].json()["notaFinal"] is None


def test_update_enrollment_result_errors():
    with requests_mock.Mocker() as m:
        m.put(f"{GA}/planificacion/cursos/42/inscripciones/a", status_code=422)
        m.put(f"{GA}/planificacion/cursos/42/inscripciones/b", status_code=500)
        with pytest.raises(UpstreamError) as e:
            ga().update_enrollment_result(
                42, "a", status="APROBADO", final_grade=Decimal(8), result_date=date.today()
            )
        assert e.value.code == "UPSTREAM_REJECTED"
        with pytest.raises(UpstreamError):
            ga().update_enrollment_result(
                42, "b", status="APROBADO", final_grade=Decimal(8), result_date=date.today()
            )


def test_401_invalidates_service_token_and_retries_once():
    with requests_mock.Mocker() as m:
        m.post(
            f"{CORE}/internal/v1/service-auth/token",
            [
                {"json": {"accessToken": "t1", "expiresIn": 900}},
                {"json": {"accessToken": "t2", "expiresIn": 900}},
            ],
        )
        m.get(f"{GA}/planificacion/periodos", [{"status_code": 401}, {"json": [PERIODO]}])
        provider = TokenProvider(CORE, "cid", "secret")
        a = ga(ServiceTokenAuth(provider))
        assert a.list_periods()[0].id == 8
        auths = [r.headers["Authorization"] for r in m.request_history if r.url.startswith(GA)]
        assert auths == ["Bearer t1", "Bearer t2"]


# ---------------------------------------------------------------- token provider
def test_token_provider_caches_until_refresh_margin():
    with requests_mock.Mocker() as m:
        m.post(f"{CORE}/internal/v1/service-auth/token", json={"accessToken": "t1", "expiresIn": 900})
        p = TokenProvider(CORE, "cid", "secret")
        assert p.get_token() == p.get_token() == "t1"
        assert m.call_count == 1 and m.request_history[0].json() == {
            "clientId": "cid",
            "clientSecret": "secret",
        }
        p.invalidate()
        p.get_token()
        assert m.call_count == 2


def test_token_provider_short_lived_token_refreshes():
    with requests_mock.Mocker() as m:
        m.post(f"{CORE}/internal/v1/service-auth/token", json={"accessToken": "t", "expiresIn": 30})
        p = TokenProvider(CORE, "c", "s")
        p.get_token()
        p.get_token()
        assert m.call_count == 2  # < 60 s to expiry -> refreshed every time


def test_token_provider_failures():
    with requests_mock.Mocker() as m:
        m.post(f"{CORE}/internal/v1/service-auth/token", status_code=401)
        with pytest.raises(UpstreamError):
            TokenProvider(CORE, "c", "s").get_token()
        m.post(f"{CORE}/internal/v1/service-auth/token", exc=requests.exceptions.ConnectTimeout)
        with pytest.raises(UpstreamError) as e:
            TokenProvider(CORE, "c", "s").get_token()
        assert e.value.status == 504


# ---------------------------------------------------------------- CORE events
def events(status=202):
    return CoreEventsLive(HttpClient("core", CORE, StaticBearer("svc"), max_retries=0)), status


@pytest.mark.parametrize(
    "status,retryable", [(500, True), (503, True), (429, True), (400, False), (422, False)]
)
def test_publish_error_classification(status, retryable):
    with requests_mock.Mocker() as m:
        m.post(f"{CORE}/internal/v1/events", status_code=status)
        with pytest.raises(PublishError) as e:
            CoreEventsLive(HttpClient("core", CORE, StaticBearer("svc"), max_retries=0)).publish(
                {"eventId": "x"}
            )
        assert e.value.retryable is retryable


def test_publish_ok_and_network_error_retryable():
    with requests_mock.Mocker() as m:
        m.post(f"{CORE}/internal/v1/events", status_code=202)
        c = CoreEventsLive(HttpClient("core", CORE, StaticBearer("svc"), max_retries=0))
        c.publish({"eventId": "x"})
        assert (
            m.request_history[0].json() == {"eventId": "x"}
            and m.request_history[0].headers["Authorization"] == "Bearer svc"
        )
        m.post(f"{CORE}/internal/v1/events", exc=requests.exceptions.ConnectionError)
        with pytest.raises(PublishError) as e:
            c.publish({"eventId": "y"})
        assert e.value.retryable is True


def test_post_is_never_auto_retried():
    http = HttpClient("core", CORE, max_retries=3)
    adapter = http.session.get_adapter(CORE)
    assert "POST" not in adapter.max_retries.allowed_methods and "GET" in adapter.max_retries.allowed_methods
    assert http.timeout == (3, 8)


# ---------------------------------------------------------------- student directory
def test_directory_live():
    """Backoffice GET /api/v1/users/{userId} (module 8 data-flow sheet)."""
    base = "https://dir.test"
    juan = "ba310c57-a684-4dbf-a4a4-905fcfbefa08"
    unknown = "00000000-0000-4000-8000-000000000999"
    with requests_mock.Mocker() as m:
        m.get(
            f"{base}/api/v1/users/{juan}",
            json={
                "userId": juan,
                "email": "jperez@uade.edu.ar",
                "firstName": "Juan",
                "lastName": "Pérez",
                "documentId": "40123456",
                "fileNumber": "1102345",
                "roles": ["STUDENT"],
                "status": "ACTIVE",
                "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90",
                "careerId": None,
            },
        )
        m.get(f"{base}/api/v1/users/{unknown}", status_code=404)
        d = StudentDirectoryLive(HttpClient("student-directory", base, StaticBearer("t"), max_retries=0))
        got = d.get_profiles([juan, unknown])
        assert set(got) == {juan}
        assert got[juan].full_name == "Juan Pérez" and got[juan].file_number == "1102345"
        assert got[juan].document == "40123456"
        assert d.get_profiles([]) == {}
        m.get(f"{base}/api/v1/users/{juan}", status_code=500)
        with pytest.raises(StudentDirectoryUnavailable):
            d.get_profiles([juan])
