"""Service-to-service routes (Student Portal). Decorated per route, not per blueprint (design §10.10)."""

from __future__ import annotations

from flask import Blueprint

from app.extensions import spec
from app.routes._common import resp, validated
from app.schemas.common import json_response
from app.schemas.results import ResultList, ResultQuery
from app.security.decorators import require_service
from app.services import result_service

bp = Blueprint("results", __name__)


@bp.get("/students/<student_id>/results")
@require_service
@spec.validate(query=ResultQuery, resp=resp(HTTP_200=ResultList), tags=["Results"])
def student_results(student_id: str):
    return json_response(result_service.student_results(student_id, validated().query.course_id))


@bp.get("/courses/<int:course_id>/results")
@require_service
@spec.validate(resp=resp(HTTP_200=ResultList), tags=["Results"])
def course_results(course_id: int):
    return json_response(result_service.course_results(course_id))
