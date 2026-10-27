from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Principal:
    """Who is calling. Built from a CORE access token (JWT claims) or CORE GET /auth/me.

    CORE contract: `sub` / `id` is the Backoffice user UUID, the same id Gestión Académica stores in
    `docentes[].docenteId`. User and service tokens share the scheme; service tokens carry kind=service.
    """

    user_id: str
    email: str | None = None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    career_ids: tuple[str, ...] = ()
    is_service: bool = False
    service: str | None = None  # module name of a service token (e.g. "student")
    raw_claims: Mapping[str, Any] = field(default_factory=dict)
    name: str | None = None
    status: str = "ACTIVE"

    def docente_keys(self) -> list[str]:
        """Identifiers that may appear in GA `docentes[].docenteId`: the CORE/Backoffice user UUID."""
        return [self.user_id] if self.user_id else []


def _names(v: Any) -> frozenset[str]:
    if isinstance(v, str):
        return frozenset(p.strip() for p in v.split(",") if p.strip())
    out = set()
    for item in v or []:
        out.add(str(item.get("name") or item.get("authority")) if isinstance(item, Mapping) else str(item))
    return frozenset(out)


def principal_from_me(data: Mapping[str, Any]) -> Principal:
    """CORE GET /api/v1/auth/me -> {id, email, careerIds[], roles[], permissions[], status}."""
    kind = str(data.get("kind") or "user")
    return Principal(
        user_id=str(data.get("id") or data.get("userId") or data.get("sub") or ""),
        email=data.get("email"),
        roles=_names(data.get("roles")),
        permissions=_names(data.get("permissions")),
        career_ids=tuple(str(c) for c in data.get("careerIds") or ()),
        is_service=kind == "service",
        service=data.get("service"),
        raw_claims=dict(data),
        name=data.get("name"),
        status=str(data.get("status") or "ACTIVE").upper(),
    )


def principal_from_claims(claims: Mapping[str, Any]) -> Principal:
    """CORE RS256 access-token claims (same names as /internal/v1/auth/introspect) -> Principal."""
    data = dict(claims)
    data.setdefault("id", claims.get("sub"))
    return principal_from_me(data)
