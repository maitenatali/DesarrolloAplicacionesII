"""Attendance and grades of ONE student in one course, for the Student Portal.

Same data the teacher sees (asistencia_por_alumno view, calificacion), filtered to a single student so the
caller never receives the rest of the commission.
"""

from __future__ import annotations

from decimal import Decimal

from flask import current_app
from sqlalchemy import select

from app.constants import EXAM_TYPE_CATALOG, AttendanceStatus, Condition, ExamStatus
from app.errors import NotFound
from app.extensions import db
from app.integrations.factory import get_integrations
from app.models import Asistencia, AsistenciaPorAlumno, Calificacion, Clase, Examen
from app.schemas.students import (
    StudentAttendanceDto,
    StudentClassAttendance,
    StudentExamGrade,
    StudentGradesDto,
)
from app.services import rules
from app.time import now_local

_CATEGORY = {t["type"]: t["category"] for t in EXAM_TYPE_CATALOG}


def _require_enrollment(student_id: str, course_id: int) -> None:
    """404 for an unknown course (CourseNotFound) or a student never enrolled in it. Students with BAJA
    still see their history."""
    detail = get_integrations().academic.get_course(course_id)
    if not any(e.student_id == student_id for e in detail.enrollments):
        raise NotFound("El alumno no está inscripto en este curso.", code="STUDENT_NOT_ENROLLED")


def student_attendance(student_id: str, course_id: int) -> StudentAttendanceDto:
    _require_enrollment(student_id, course_id)
    summary = db.session.get(AsistenciaPorAlumno, (course_id, student_id))
    marks = {
        a.clase_id: a
        for a in db.session.scalars(
            select(Asistencia)
            .join(Clase, Clase.id == Asistencia.clase_id)
            .where(Clase.curso_id == course_id, Asistencia.alumno_id == student_id)
        )
    }
    classes = db.session.scalars(select(Clase).where(Clase.curso_id == course_id).order_by(Clase.fecha)).all()
    return StudentAttendanceDto(
        student_id=student_id,
        course_id=course_id,
        threshold=current_app.extensions["settings"].regular_threshold,
        classes_recorded=summary.clases_registradas if summary else 0,
        present=summary.presentes if summary else 0,
        justified=summary.justificados if summary else 0,
        absences=summary.inasistencias if summary else 0,
        attendance_percentage=summary.porcentaje_asistencia if summary else Decimal("0.00"),
        condition=Condition(summary.condicion) if summary else Condition.LIBRE,
        classes=[
            StudentClassAttendance(
                date=c.fecha,
                status=AttendanceStatus(marks[c.id].estado) if c.id in marks else None,
                note=marks[c.id].observacion if c.id in marks else None,
            )
            for c in classes
        ],
    )


def student_grades(student_id: str, course_id: int) -> StudentGradesDto:
    _require_enrollment(student_id, course_id)
    passing = current_app.extensions["settings"].passing_grade
    exams = db.session.scalars(
        select(Examen)
        .where(Examen.curso_id == course_id, Examen.estado != ExamStatus.CANCELADO)
        .order_by(Examen.fecha, Examen.hora_inicio, Examen.id)
    ).all()
    cals = {
        c.examen_id: c
        for c in db.session.scalars(
            select(Calificacion).where(
                Calificacion.alumno_id == student_id, Calificacion.examen_id.in_([e.id for e in exams])
            )
        )
    }
    now = now_local()
    rows: list[StudentExamGrade] = []
    for e in exams:
        cal = cals.get(e.id)
        grade = cal.nota if cal else None
        rows.append(
            StudentExamGrade(
                exam_id=e.id,
                type=e.tipo,
                name=e.nombre,
                category=_CATEGORY.get(e.tipo.upper()),
                date=e.fecha,
                status=ExamStatus(e.estado),
                phase=rules.exam_phase(e.estado, e.fecha, e.hora_inicio, e.duracion_minutos, now),
                grade=grade,
                absent=bool(cal and cal.ausente),
                passed=None if grade is None else grade >= passing,
                graded_at=cal.cargada_en if cal else None,
                graded_by=cal.cargada_por if cal else None,
            )
        )
    return StudentGradesDto(
        student_id=student_id,
        course_id=course_id,
        passing_grade=passing,
        average=rules.mean([r.grade for r in rows if r.grade is not None], 2),
        exams=rows,
    )
