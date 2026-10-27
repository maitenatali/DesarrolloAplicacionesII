"""Shared Pydantic bases. English camelCase keys; Decimal grades serialise as JSON numbers (design §7)."""

from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Annotated

from flask import Response
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


# --- scalar types -----------------------------------------------------------------
GradeIn = Annotated[Decimal, Field(ge=0, le=10, max_digits=4, decimal_places=2)]
GradeOut = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]
Pct = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]
HHmm = Annotated[time, PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str, when_used="json")]
Instant = Annotated[
    datetime,
    PlainSerializer(
        lambda d: d.astimezone(UTC).isoformat().replace("+00:00", "Z"), return_type=str, when_used="json"
    ),
]


class ProblemError(ApiModel):
    field: str
    code: str
    message: str


class ProblemDetail(BaseModel):
    """application/problem+json (RFC 7807-style)."""

    model_config = ConfigDict(extra="allow")
    type: str = "about:blank"
    title: str
    status: int
    code: str
    detail: str
    instance: str | None = None
    correlationId: str | None = None
    errors: list[ProblemError] | None = None


def json_response(model: BaseModel, status: int = 200, headers: dict[str, str] | None = None) -> Response:
    resp = Response(model.model_dump_json(by_alias=True), status=status, mimetype="application/json")
    for k, v in (headers or {}).items():
        resp.headers[k] = v
    return resp
