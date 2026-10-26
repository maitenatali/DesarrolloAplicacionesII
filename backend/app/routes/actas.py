from __future__ import annotations

from flask import Blueprint, g, request

from app.extensions import spec
from app.routes._common import resp
from app.schemas.actas import (
    ActaCreatedDto,
    ActaCreateRequest,
    ActaDto,
    ActaPage,
    ActaQuery,
    AnnulRequest,
    SyncResponse,
)
from app.schemas.common import json_response
from app.security.decorators import require_auth, require_teacher
from app.services import acta_service

bp = Blueprint("actas", __name__)


@bp.get("/actas")
@require_auth
@require_teacher
@spec.validate(query=ActaQuery, resp=resp(HTTP_200=ActaPage), tags=["Actas"])
def list_actas():
    return json_response(acta_service.list_actas(g.principal, request.context.query))


@bp.get("/actas/<int:acta_id>")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=ActaDto), tags=["Actas"])
def get_acta(acta_id: int):
    return json_response(acta_service.get_acta(g.principal, acta_id))


@bp.post("/actas")
@require_auth
@require_teacher
@spec.validate(json=ActaCreateRequest, resp=resp(HTTP_201=ActaCreatedDto), tags=["Actas"])
def create_acta():
    dto = acta_service.generate_acta(g.principal, request.context.json)
    return json_response(dto, 201, {"Location": f"/api/v1/actas/{dto.id}"})


@bp.post("/actas/<int:acta_id>/annulment")
@require_auth
@require_teacher
@spec.validate(json=AnnulRequest, resp=resp(HTTP_200=ActaDto), tags=["Actas"])
def annul_acta(acta_id: int):
    return json_response(acta_service.annul_acta(g.principal, acta_id, request.context.json))


@bp.post("/actas/<int:acta_id>/sync")
@require_auth
@require_teacher
@spec.validate(resp=resp(HTTP_200=SyncResponse), tags=["Actas"])
def sync_acta(acta_id: int):
    return json_response(acta_service.resync_acta(g.principal, acta_id))
