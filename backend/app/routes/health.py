from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from pydantic import BaseModel
from sqlalchemy import func, select, text

from app.extensions import db, spec
from app.models import OutboxEvent
from app.routes._common import resp

bp = Blueprint("health", __name__)


class HealthDto(BaseModel):
    status: str


class ReadyDto(BaseModel):
    status: str
    integrations: dict[str, str]
    migrationHead: str | None = None
    outboxPending: int = 0
    outboxFailed: int = 0


@bp.get("/health")
@spec.validate(resp=resp(HTTP_200=HealthDto), tags=["Health"])
def health():
    return jsonify({"status": "ok"})


@bp.get("/health/ready")
@spec.validate(resp=resp(HTTP_200=ReadyDto, HTTP_503=HealthDto), tags=["Health"])
def ready():
    modes = current_app.extensions["integrations"].modes
    try:
        db.session.execute(text("select 1"))
        head = db.session.scalar(text("select version_num from alembic_version"))
        counts = dict(
            db.session.execute(select(OutboxEvent.status, func.count()).group_by(OutboxEvent.status)).all()
        )
    except Exception:
        db.session.rollback()
        return jsonify({"status": "unavailable"}), 503
    return jsonify(
        {
            "status": "ok",
            "integrations": modes,
            "migrationHead": head,
            "outboxPending": counts.get("PENDING", 0),
            "outboxFailed": counts.get("FAILED", 0),
        }
    )
