from __future__ import annotations

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from spectree import SpecTree

from app.models.base import Base

db = SQLAlchemy(model_class=Base)
migrate = Migrate()


def _before(req, resp, req_validation_error, instance, model_adapter=None):
    """SpecTree hook: malformed JSON / schema violations -> 400 problem+json (design §7.2)."""
    from app.errors import BadRequest, ValidationFailed, format_validation_errors

    if req.method in ("POST", "PUT", "PATCH") and req.data and req.mimetype == "application/json":
        if req.get_json(silent=True) is None:
            raise BadRequest("El cuerpo de la solicitud no es JSON válido.", code="MALFORMED_JSON")
    if req_validation_error is not None:
        raise ValidationFailed(format_validation_errors(req_validation_error))


spec = SpecTree(
    "flask",
    title="teacher-service",
    version="1.0.0",
    path="apidocs",
    validation_error_status=400,
    before=_before,
    description="Portal Docente (UADEnet) - asistencia, exámenes, calificaciones y actas.",
)
