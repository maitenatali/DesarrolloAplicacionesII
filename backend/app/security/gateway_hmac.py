"""Optional gateway signed-header check. Format is [OPEN]; disabled by default (design §8.6)."""

from __future__ import annotations

from flask import Flask, Request, request

from app.errors import Unauthorized


def verify(req: Request) -> bool:
    """TODO(CORE): header names/algorithm unknown - do NOT invent them. Fails closed until implemented."""
    return False


def register_gateway_hmac(app: Flask) -> None:
    if not app.extensions["settings"].gateway_hmac_enabled:
        return

    @app.before_request
    def _check():
        if request.path.startswith(("/api/v1/health", "/apidocs")):
            return None
        if not verify(request):
            raise Unauthorized("Firma del gateway inválida.", code="TOKEN_INVALID")
        return None
