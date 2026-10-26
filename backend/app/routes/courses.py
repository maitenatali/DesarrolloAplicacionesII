from __future__ import annotations

from flask import Blueprint, g, request

from app.constants import DEGRADED_HEADER
from app.extensions import spec
from app.routes._common import resp
from app.schemas.common import json_response
from app.schemas.courses import (
    CourseDto,
    CourseList,
    ExamTurnList,
    ExamTypeList,
    MeDto,
    PeriodList,
    PeriodQuery,
    PrerequisiteList,
    RosterList,
)
from app.security.decorators import require_auth, require_teacher
from app.services import course_service

bp = Blueprint("courses", __name__)


@bp.get("/me")
@require_auth
@spec.validate(resp=resp(HTTP_200=MeDto), tags=["Courses"])
def me():
    return json_response(course_service.me(g.principal))


@bp.get("/periods")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=PeriodList), tags=["Courses"])
def periods():
    return json_response(course_service.list_periods())


@bp.get("/exam-turns")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=ExamTurnList), tags=["Courses"])
def exam_turns():
    return json_response(course_service.list_exam_turns())


@bp.get("/exam-types")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=ExamTypeList), tags=["Exams"])
def exam_types():
    return json_response(course_service.exam_types())


@bp.get("/courses")
@require_auth
@require_teacher
@spec.validate(query=PeriodQuery, resp=resp(HTTP_200=CourseList), tags=["Courses"])
def list_courses():
    return json_response(course_service.list_courses(g.principal, request.context.query.period_id))


@bp.get("/courses/<int:course_id>")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=CourseDto), tags=["Courses"])
def get_course(course_id: int):
    return json_response(course_service.get_course(g.principal, course_id))


@bp.get("/courses/<int:course_id>/students")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=RosterList), tags=["Courses"])
def students(course_id: int):
    roster, degraded = course_service.students(g.principal, course_id)
    return json_response(roster, headers={DEGRADED_HEADER: "student-directory"} if degraded else None)


@bp.get("/courses/<int:course_id>/prerequisites")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=PrerequisiteList), tags=["Courses"])
def prerequisites(course_id: int):
    return json_response(course_service.prerequisites(g.principal, course_id))
