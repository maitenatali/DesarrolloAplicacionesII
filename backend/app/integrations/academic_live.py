"""Gestión Académica live adapter (design §9.5). Spanish JSON -> internal dataclasses happens ONLY here.

TODO(GA): exact DTO field names are taken from the design/contract hints; `_pick` tolerates variants.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from cachetools import TTLCache

from app.errors import CourseNotFound, UpstreamError

from .base import (
    AcademicClient,
    CourseDetail,
    CourseSummary,
    Enrollment,
    ExamTurn,
    Period,
    Prerequisite,
    Schedule,
    Subject,
    TeacherAssignment,
)
from .http import HttpClient


def _pick(d: dict, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _date(v: Any) -> date | None:
    return date.fromisoformat(str(v)[:10]) if v else None


def _req_date(d: dict, *keys: str) -> date:
    """Mandatory date in a GA payload; a missing one is an upstream contract break (502), not our bug."""
    v = _date(_pick(d, *keys))
    if v is None:
        raise UpstreamError("academic", f"Gestión Académica no envió {keys[0]}.", code="UPSTREAM_REJECTED")
    return v


def _time(v: Any) -> time:
    return time.fromisoformat(str(v)) if v else time(0, 0)


def _dec(v: Any) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _period(d: dict) -> Period:
    return Period(
        id=int(d["id"]),
        year=int(_pick(d, "anio", "año", "year")),
        number=int(_pick(d, "numero", "cuatrimestre", "number")),
        start=_req_date(d, "fechaInicio", "inicio"),
        end=_req_date(d, "fechaFin", "fin"),
        enroll_from=_date(_pick(d, "inscripcionDesde", "fechaInscripcionDesde")),
        enroll_until=_date(_pick(d, "inscripcionHasta", "fechaInscripcionHasta")),
    )


def _summary(d: dict) -> CourseSummary:
    return CourseSummary(
        id=int(d["id"]),
        code=str(_pick(d, "codigo", "comision", default="")),
        subject_id=int(_pick(d, "asignaturaId", default=(d.get("asignatura") or {}).get("id", 0))),
        period_id=int(_pick(d, "periodoId", default=(d.get("periodo") or {}).get("id", 0))),
        campus_id=_pick(d, "sedeId"),
        modality=str(_pick(d, "modalidad", default="PRESENCIAL")),
        status=str(_pick(d, "estado", default="EN_CURSO")),
        max_seats=int(_pick(d, "cupoMaximo", "cupo", default=0)),
        start=_date(_pick(d, "fechaInicio")),
        end=_date(_pick(d, "fechaFin")),
        active_enrolled=int(_pick(d, "inscriptosActivos", "inscriptos", default=0)),
    )


class AcademicLive(AcademicClient):
    def __init__(
        self,
        http: HttpClient,
        *,
        supports_teacher_filter: bool = False,
        cache_ttl: int = 60,
        fanout_concurrency: int = 6,
    ):
        self.http = http
        self.supports_teacher_filter = supports_teacher_filter
        self.fanout = max(1, fanout_concurrency)
        self._cache: TTLCache = TTLCache(maxsize=512, ttl=cache_ttl)
        self._lock = threading.Lock()

    # -- helpers -------------------------------------------------------------
    def _get_json(self, path: str, *, params: dict | None = None, template: str | None = None) -> Any:
        resp = self.http.request("GET", path, params=params, template=template)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise self.http.rejected(resp)
        return resp.json()

    # -- reads ---------------------------------------------------------------
    def list_periods(self) -> list[Period]:
        return [_period(p) for p in self._get_json("/planificacion/periodos") or []]

    def list_exam_turns(self) -> list[ExamTurn]:
        out = []
        for t in self._get_json("/planificacion/turnos-examen") or []:
            out.append(
                ExamTurn(
                    id=int(t["id"]),
                    name=str(_pick(t, "nombre", "titulo", default="")),
                    start=_req_date(t, "fechaInicio"),
                    end=_req_date(t, "fechaFin"),
                    enroll_from=_req_date(t, "inscripcionDesde", "fechaInscripcionDesde"),
                    enroll_until=_req_date(t, "inscripcionHasta", "fechaInscripcionHasta"),
                )
            )
        return out

    def list_courses(self, period_id: int | None = None) -> list[CourseSummary]:
        params = {"periodoId": period_id} if period_id is not None else None
        return [_summary(c) for c in self._get_json("/planificacion/cursos", params=params) or []]

    def get_course(self, course_id: int, *, fresh: bool = False) -> CourseDetail:
        if not fresh:
            with self._lock:
                hit = self._cache.get(course_id)
            if hit is not None:
                return hit
        data = self._get_json(
            f"/planificacion/cursos/{int(course_id)}", template="/planificacion/cursos/{id}"
        )
        if data is None:
            raise CourseNotFound(course_id)
        detail = self._detail(data)
        with self._lock:
            self._cache[course_id] = detail
        return detail

    def _detail(self, data: dict) -> CourseDetail:
        c = data.get("curso") or data
        subj = c.get("asignatura") or {}
        per = c.get("periodo") or {}
        summary = _summary(
            {
                **c,
                "asignaturaId": _pick(c, "asignaturaId", default=subj.get("id")),
                "periodoId": _pick(c, "periodoId", default=per.get("id")),
            }
        )
        enrollments = [
            Enrollment(
                id=int(e.get("id", 0)),
                student_id=str(_pick(e, "alumnoId", "studentId")),
                enrolled_on=_date(_pick(e, "fechaInscripcion")),
                status=str(_pick(e, "estado", default="CURSANDO")),
                final_grade=_dec(e.get("notaFinal")),
                result_date=_date(e.get("fechaResultado")),
            )
            for e in data.get("inscripciones") or []
        ]
        return CourseDetail(
            course=CourseSummary(
                **{
                    **summary.__dict__,
                    "active_enrolled": sum(1 for e in enrollments if e.status != "BAJA")
                    or summary.active_enrolled,
                }
            ),
            subject=Subject(
                int(subj.get("id", summary.subject_id)),
                str(_pick(subj, "codigo", default="")),
                str(_pick(subj, "nombre", default="")),
            ),
            period=_period(per)
            if per
            else Period(summary.period_id, 0, 0, date.min, date.min, date.min, date.min),
            teachers=[
                TeacherAssignment(
                    int(t.get("id", 0)),
                    str(_pick(t, "docenteId", "teacherId")),
                    str(_pick(t, "rol", "role", default="TITULAR")),
                )
                for t in data.get("docentes") or []
            ],
            enrollments=enrollments,
            schedule=[
                Schedule(
                    int(h.get("id", 0)),
                    _pick(h, "aulaId"),
                    str(_pick(h, "diaSemana", "dia", default="")),
                    _time(_pick(h, "horaInicio")),
                    _time(_pick(h, "horaFin")),
                )
                for h in data.get("horarios") or []
            ],
        )

    def list_courses_for_teacher(
        self, teacher_keys: set[str], period_id: int | None = None
    ) -> list[CourseDetail]:
        if self.supports_teacher_filter:
            # TODO(GA): native ?docenteId= filter. Try each candidate key until one returns results.
            for key in sorted(teacher_keys):
                params = {"docenteId": key, **({"periodoId": period_id} if period_id is not None else {})}
                rows = self._get_json("/planificacion/cursos", params=params) or []
                if rows:
                    return [self.get_course(int(r["id"])) for r in rows]
            return []
        summaries = self.list_courses(period_id)
        if not summaries:
            return []
        with ThreadPoolExecutor(self.fanout) as pool:
            details = list(pool.map(lambda s: self.get_course(s.id), summaries))
        return [d for d in details if any(t.teacher_id in teacher_keys for t in d.teachers)]

    def list_prerequisites(self, subject_id: int) -> list[Prerequisite]:
        rows = (
            self._get_json(
                f"/academica/asignaturas/{int(subject_id)}/correlatividades",
                template="/academica/asignaturas/{id}/correlatividades",
            )
            or []
        )
        return [
            Prerequisite(
                int(r.get("id", 0)),
                int(subject_id),
                int(_pick(r, "asignaturaRequeridaId", "correlativaId", "prerequisiteId")),
                str(_pick(r, "tipo", "kind", default="REGULAR")),
            )
            for r in rows
        ]

    # -- writes --------------------------------------------------------------
    def update_enrollment_result(
        self, course_id: int, student_id: str, *, status: str, final_grade: Decimal | None, result_date: date
    ) -> None:
        path = f"/planificacion/cursos/{int(course_id)}/inscripciones/{quote(student_id, safe='')}"
        body = {
            "estado": status,
            "notaFinal": float(final_grade) if final_grade is not None else None,
            "fechaResultado": result_date.isoformat(),
        }
        resp = self.http.request(
            "PUT", path, json=body, template="/planificacion/cursos/{id}/inscripciones/{alumnoId}"
        )
        if resp.status_code >= 400:
            raise UpstreamError(
                "academic",
                f"GA rechazó la actualización de {student_id}.",
                code="UPSTREAM_REJECTED",
                upstream_status=resp.status_code,
            )
        with self._lock:
            self._cache.pop(course_id, None)
