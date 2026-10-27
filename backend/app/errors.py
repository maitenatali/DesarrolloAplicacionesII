"""AppError hierarchy and handlers -> application/problem+json (design §13)."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, g, has_request_context, jsonify, request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

log = logging.getLogger("app.errors")


class AppError(Exception):
    status = 500
    code = "INTERNAL_ERROR"
    title = "Internal Server Error"

    def __init__(self, detail: str, *, code: str | None = None, **extra: Any):
        super().__init__(detail)
        self.detail = detail
        self.extra = extra
        if code:
            self.code = code


class BadRequest(AppError):
    status, title, code = 400, "Bad Request", "VALIDATION_ERROR"


class Unauthorized(AppError):
    status, title, code = 401, "Unauthorized", "TOKEN_INVALID"


class Forbidden(AppError):
    status, title, code = 403, "Forbidden", "FORBIDDEN"


class NotFound(AppError):
    status, title, code = 404, "Not Found", "NOT_FOUND"


class Conflict(AppError):
    status, title, code = 409, "Conflict", "CONFLICT"


class TooManyRequests(AppError):
    status, title, code = 429, "Too Many Requests", "TOO_MANY_REQUESTS"


class ServiceUnavailable(AppError):
    status, title, code = 503, "Service Unavailable", "SERVICE_UNAVAILABLE"


class UpstreamError(AppError):
    status, title, code = 502, "Bad Gateway", "UPSTREAM_ERROR"

    def __init__(
        self,
        module: str,
        detail: str | None = None,
        *,
        status: int = 502,
        code: str | None = None,
        upstream_status: int | None = None,
        **extra: Any,
    ):
        super().__init__(detail or f"El módulo {module} no respondió correctamente.", code=code, **extra)
        self.module = module
        self.status = status
        self.upstream_status = upstream_status
        if status == 504:
            self.title = "Gateway Timeout"
            self.code = code or "UPSTREAM_TIMEOUT"


class CourseNotFound(NotFound):
    code = "COURSE_NOT_FOUND"

    def __init__(self, course_id: int | None = None):
        super().__init__("El curso no existe.")


class PublishError(Exception):
    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class StudentDirectoryUnavailable(UpstreamError):
    def __init__(self):
        super().__init__(
            "student-directory",
            "No se pudo obtener el padrón de alumnos.",
            code="STUDENT_DIRECTORY_UNAVAILABLE",
        )


def _camel(loc: tuple[Any, ...]) -> str:
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += ("." if out else "") + str(part)
    return out


def _es_message(e: Any) -> str:
    """Spanish, user-presentable text for a Pydantic error (the UI shows it; `code` stays the stable contract)."""
    t = str(e.get("type", ""))
    ctx = e.get("ctx") or {}
    if t == "value_error":  # our own validators already raise Spanish messages
        return str(e.get("msg", "")).removeprefix("Value error, ") or "Valor inválido."
    fixed = {
        "missing": "Campo obligatorio.",
        "extra_forbidden": "Campo no permitido.",
        "string_type": "Debe ser un texto.",
        "int_type": "Debe ser un número entero.",
        "int_parsing": "Debe ser un número entero.",
        "int_from_float": "Debe ser un número entero.",
        "bool_type": "Debe ser verdadero o falso.",
        "bool_parsing": "Debe ser verdadero o falso.",
        "decimal_type": "Debe ser un número.",
        "decimal_parsing": "Debe ser un número.",
        "float_parsing": "Debe ser un número.",
        "date_type": "Debe ser una fecha con formato YYYY-MM-DD.",
        "date_parsing": "Debe ser una fecha con formato YYYY-MM-DD.",
        "date_from_datetime_parsing": "Debe ser una fecha con formato YYYY-MM-DD.",
        "time_type": "Debe ser una hora con formato HH:mm.",
        "time_parsing": "Debe ser una hora con formato HH:mm.",
        "list_type": "Debe ser una lista.",
        "dict_type": "Debe ser un objeto.",
        "model_attributes_type": "Debe ser un objeto.",
        "json_invalid": "JSON inválido.",
        "enum": f"Valor no permitido. Valores válidos: {ctx.get('expected', '')}.",
        "literal_error": f"Valor no permitido. Valores válidos: {ctx.get('expected', '')}.",
    }
    if t in fixed:
        return fixed[t]
    if t == "less_than_equal":
        return f"Debe ser menor o igual a {ctx.get('le')}."
    if t == "less_than":
        return f"Debe ser menor que {ctx.get('lt')}."
    if t == "greater_than_equal":
        return f"Debe ser mayor o igual a {ctx.get('ge')}."
    if t == "greater_than":
        return f"Debe ser mayor que {ctx.get('gt')}."
    if t == "string_too_short":
        return f"Debe tener al menos {ctx.get('min_length')} caracteres."
    if t == "string_too_long":
        return f"Debe tener como máximo {ctx.get('max_length')} caracteres."
    if t == "too_short":
        return f"Debe tener al menos {ctx.get('min_length')} elemento(s)."
    if t == "too_long":
        return f"Debe tener como máximo {ctx.get('max_length')} elemento(s)."
    if t == "decimal_max_places":
        return f"Admite como máximo {ctx.get('decimal_places')} decimales."
    if t in ("decimal_max_digits", "decimal_whole_digits"):
        return "Tiene demasiados dígitos."
    return "Valor inválido."


def format_validation_errors(err: ValidationError) -> list[dict[str, str]]:
    items = []
    for e in err.errors():
        msg = _es_message(e)
        items.append(
            {
                "field": _camel(tuple(e.get("loc", ()))),
                "code": str(e.get("type", "invalid")).upper(),
                "message": msg,
            }
        )
    return items


class ValidationFailed(BadRequest):
    def __init__(self, errors: list[dict[str, str]], detail: str = "La solicitud no es válida."):
        super().__init__(detail, errors=errors)


def problem(status: int, title: str, code: str, detail: str, **extra: Any):
    body = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        "instance": request.path if has_request_context() else None,  # same field CORE returns
        "correlationId": getattr(g, "correlation_id", None),
        **extra,
    }
    resp = jsonify(body)
    resp.status_code = status
    resp.mimetype = "application/problem+json"
    return resp


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def _app_error(e: AppError):
        if e.status >= 500:
            log.warning("app_error", extra={"code": e.code, "status": e.status})
        return problem(e.status, e.title, e.code, e.detail, **e.extra)

    @app.errorhandler(ValidationError)
    def _pyd(e: ValidationError):
        return problem(
            400,
            "Bad Request",
            "VALIDATION_ERROR",
            "La solicitud no es válida.",
            errors=format_validation_errors(e),
        )

    @app.errorhandler(IntegrityError)
    def _integrity(e: IntegrityError):
        from app.extensions import db

        db.session.rollback()
        constraint = getattr(getattr(e.orig, "diag", None), "constraint_name", None)
        log.warning("integrity_error", extra={"constraint": constraint})
        return problem(409, "Conflict", "CONFLICT", "La operación entra en conflicto con datos existentes.")

    @app.errorhandler(HTTPException)
    def _http(e: HTTPException):
        names = {
            400: "BAD_REQUEST",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            413: "PAYLOAD_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
        }
        code = names.get(e.code or 500, (e.name or "ERROR").upper().replace(" ", "_"))
        detail = {404: "Recurso no encontrado.", 405: "Método no permitido."}.get(
            e.code or 0, e.description or ""
        )
        return problem(e.code or 500, e.name, code, detail)

    @app.errorhandler(Exception)
    def _any(e: Exception):
        log.exception("unhandled_error")
        return problem(500, "Internal Server Error", "INTERNAL_ERROR", "Ocurrió un error inesperado.")
