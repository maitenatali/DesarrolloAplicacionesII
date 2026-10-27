from __future__ import annotations

from flask import Blueprint, g

from app.extensions import spec
from app.routes._common import resp, validated
from app.schemas.calendar import CalendarDto, CalendarQuery, PurchaseList
from app.schemas.common import json_response
from app.security.decorators import require_auth, require_teacher
from app.services import calendar_service

bp = Blueprint("calendar", __name__)


@bp.get("/calendar")
@require_auth
@require_teacher
@spec.validate(query=CalendarQuery, resp=resp(HTTP_200=CalendarDto), tags=["Calendar"])
def calendar():
    """Exámenes propios + turnos de examen (GA) + eventos académicos + turnos de comedor."""
    return json_response(calendar_service.calendar(g.principal, validated().query))


@bp.get("/purchases")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=PurchaseList), tags=["Calendar"])
def purchases():
    """Historial de compras de la Tienda del Campus (mock en esta entrega)."""
    return json_response(calendar_service.purchases(g.principal))
