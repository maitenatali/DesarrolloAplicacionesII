"""Per-student routes for the Student Portal: a service token, or the student's own token (design §10.10)."""

from __future__ import annotations

from flask import Blueprint

from app.extensions import spec
from app.routes._common import resp
from app.schemas.common import json_response
from app.schemas.students import StudentAttendanceDto, StudentGradesDto
from app.security.decorators import require_service_or_self
from app.services import student_service

bp = Blueprint("students", __name__)


@bp.get("/students/<student_id>/courses/<int:course_id>/attendance")
@require_service_or_self
@spec.validate(resp=resp(HTTP_200=StudentAttendanceDto), tags=["Students"])
def student_attendance(student_id: str, course_id: int):
    """Resumen de asistencia del alumno en el curso + el detalle de cada clase registrada."""
    return json_response(student_service.student_attendance(student_id, course_id))


@bp.get("/students/<student_id>/courses/<int:course_id>/grades")
@require_service_or_self
@spec.validate(resp=resp(HTTP_200=StudentGradesDto), tags=["Students"])
def student_grades(student_id: str, course_id: int):
    """Exámenes del curso (sin los cancelados) con la nota de ese alumno."""
    return json_response(student_service.student_grades(student_id, course_id))
