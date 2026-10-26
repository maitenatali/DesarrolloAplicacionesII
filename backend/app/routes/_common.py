from __future__ import annotations

from datetime import date

from spectree import Response

from app.errors import ValidationFailed
from app.schemas.common import ProblemDetail

_ERRORS = {
    "HTTP_400": ProblemDetail,
    "HTTP_401": ProblemDetail,
    "HTTP_403": ProblemDetail,
    "HTTP_404": ProblemDetail,
    "HTTP_409": ProblemDetail,
    "HTTP_502": ProblemDetail,
    "HTTP_504": ProblemDetail,
}


def resp(**ok) -> Response:
    """Success model(s) + the standard problem+json error set."""
    return Response(**ok, **_ERRORS)


def parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationFailed(
            [{"field": "date", "code": "INVALID_DATE", "message": "La fecha debe tener formato YYYY-MM-DD."}]
        ) from None
