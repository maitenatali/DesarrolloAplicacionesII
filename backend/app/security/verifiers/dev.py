from __future__ import annotations

from flask import request

from app.errors import Unauthorized
from app.integrations.fixtures import TEACHER_NAME
from app.security.principal import Principal

from .base import TokenVerifier


class DevVerifier(TokenVerifier):
    """Local only: trusts X-Dev-User / X-Dev-Roles / X-Dev-Name (the bearer token is ignored).

    Boot refuses it when APP_ENV=production.
    """

    def verify(self, token: str) -> Principal:
        user = request.headers.get("X-Dev-User", "").strip()
        if not user:
            raise Unauthorized("Falta X-Dev-User.", code="TOKEN_INVALID")
        roles = frozenset(
            r.strip() for r in request.headers.get("X-Dev-Roles", "ROLE_DOCENTE").split(",") if r.strip()
        )
        return Principal(
            user_id=user,
            email=request.headers.get("X-Dev-Email") or None,
            roles=roles,
            name=request.headers.get("X-Dev-Name") or TEACHER_NAME.get(user),
            raw_claims={"sub": user},
        )
