from __future__ import annotations

from flask import Blueprint, g, request

from app.extensions import spec
from app.routes._common import resp
from app.schemas.common import json_response
from app.schemas.exams import (
    CancelRequest,
    ExamCreateRequest,
    ExamDetailDto,
    ExamDto,
    ExamList,
    ExamPatchRequest,
    ExamQuery,
    ExamWithCourseList,
)
from app.security.decorators import require_auth, require_teacher
from app.services import exam_service

bp = Blueprint("exams", __name__)


@bp.get("/courses/<int:course_id>/exams")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=ExamList), tags=["Exams"])
def list_exams(course_id: int):
    return json_response(exam_service.list_exams(g.principal, course_id))


@bp.post("/courses/<int:course_id>/exams")
@require_auth
@require_teacher
@spec.validate(json=ExamCreateRequest, resp=resp(HTTP_201=ExamDto), tags=["Exams"])
def create_exam(course_id: int):
    dto = exam_service.create_exam(g.principal, course_id, request.context.json)
    return json_response(dto, 201, {"Location": f"/api/v1/courses/{course_id}/exams/{dto.id}"})


@bp.get("/courses/<int:course_id>/exams/<int:exam_id>")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=ExamDetailDto), tags=["Exams"])
def get_exam(course_id: int, exam_id: int):
    return json_response(exam_service.get_exam(g.principal, course_id, exam_id))


@bp.patch("/courses/<int:course_id>/exams/<int:exam_id>")
@require_auth
@require_teacher
@spec.validate(json=ExamPatchRequest, resp=resp(HTTP_200=ExamDto), tags=["Exams"])
def patch_exam(course_id: int, exam_id: int):
    return json_response(exam_service.patch_exam(g.principal, course_id, exam_id, request.context.json))


@bp.post("/courses/<int:course_id>/exams/<int:exam_id>/cancellation")
@require_auth
@require_teacher
@spec.validate(json=CancelRequest, resp=resp(HTTP_200=ExamDto), tags=["Exams"])
def cancel_exam(course_id: int, exam_id: int):
    return json_response(exam_service.cancel_exam(g.principal, course_id, exam_id, request.context.json))


@bp.get("/exams")
@require_auth
@require_teacher
@spec.validate(query=ExamQuery, resp=resp(HTTP_200=ExamWithCourseList), tags=["Exams"])
def my_exams():
    return json_response(exam_service.list_my_exams(g.principal, request.context.query))
