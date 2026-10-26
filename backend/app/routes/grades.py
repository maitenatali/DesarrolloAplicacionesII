from __future__ import annotations

from flask import Blueprint, g, request

from app.extensions import spec
from app.routes._common import resp
from app.schemas.common import json_response
from app.schemas.grades import GradeMatrix, GradesResponse, GradesUpsertRequest, GradesUpsertResponse
from app.security.decorators import require_auth, require_teacher
from app.services import grade_service

bp = Blueprint("grades", __name__)


@bp.get("/courses/<int:course_id>/exams/<int:exam_id>/grades")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=GradesResponse), tags=["Grades"])
def get_grades(course_id: int, exam_id: int):
    return json_response(grade_service.get_exam_grades(g.principal, course_id, exam_id))


@bp.put("/courses/<int:course_id>/exams/<int:exam_id>/grades")
@require_auth
@require_teacher
@spec.validate(json=GradesUpsertRequest, resp=resp(HTTP_200=GradesUpsertResponse), tags=["Grades"])
def put_grades(course_id: int, exam_id: int):
    return json_response(grade_service.upsert_grades(g.principal, course_id, exam_id, request.context.json))


@bp.get("/courses/<int:course_id>/grades")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=GradeMatrix), tags=["Grades"])
def grade_matrix(course_id: int):
    return json_response(grade_service.course_matrix(g.principal, course_id))
