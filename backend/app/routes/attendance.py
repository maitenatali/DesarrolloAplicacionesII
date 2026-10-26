from __future__ import annotations

from flask import Blueprint, g, request

from app.extensions import spec
from app.routes._common import parse_day, resp
from app.schemas.attendance import AttendanceDto, AttendanceList, AttendancePutRequest, AttendanceSummaryDto
from app.schemas.common import json_response
from app.security.decorators import require_auth, require_teacher
from app.services import attendance_service

bp = Blueprint("attendance", __name__)


@bp.get("/courses/<int:course_id>/attendances")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=AttendanceList), tags=["Attendance"])
def list_attendances(course_id: int):
    return json_response(attendance_service.list_attendances(g.principal, course_id))


@bp.get("/courses/<int:course_id>/attendances/<day>")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=AttendanceDto), tags=["Attendance"])
def get_attendance(course_id: int, day: str):
    return json_response(attendance_service.get_attendance(g.principal, course_id, parse_day(day)))


@bp.put("/courses/<int:course_id>/attendances/<day>")
@require_auth
@require_teacher
@spec.validate(
    json=AttendancePutRequest, resp=resp(HTTP_200=AttendanceDto, HTTP_201=AttendanceDto), tags=["Attendance"]
)
def put_attendance(course_id: int, day: str):
    dto, created = attendance_service.put_attendance(
        g.principal, course_id, parse_day(day), request.context.json
    )
    return json_response(dto, 201 if created else 200)


@bp.get("/courses/<int:course_id>/attendance-summary")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=AttendanceSummaryDto), tags=["Attendance"])
def attendance_summary(course_id: int):
    return json_response(attendance_service.attendance_summary(g.principal, course_id))
