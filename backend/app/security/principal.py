from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str | None = None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    is_service: bool = False
    raw_claims: Mapping[str, Any] = field(default_factory=dict)
    name: str | None = None
    status: str = "ACTIVE"

    def docente_keys(self, order: tuple[str, ...] = ("sub", "email", "email_local")) -> list[str]:
        """Candidate identifiers to match GA `docentes[].docenteId`.

        TODO(CORE): the real CORE-user <-> docenteId mapping is [OPEN]; this replicates the frontend heuristic.
        """
        keys: list[str] = []
        for o in order:
            if o == "sub" and self.user_id:
                keys.append(self.user_id)
            elif o == "email" and self.email:
                keys.append(self.email)
            elif o == "email_local" and self.email and "@" in self.email:
                keys.append(self.email.split("@", 1)[0])
        seen: set[str] = set()
        return [k for k in keys if not (k in seen or seen.add(k))]


def principal_from_me(data: Mapping[str, Any]) -> Principal:
    """CORE GET /auth/me -> {id, email, roles[], permissions[], status}."""

    def names(v: Any) -> frozenset[str]:
        out = set()
        for item in v or []:
            out.add(
                str(item.get("name") or item.get("authority")) if isinstance(item, Mapping) else str(item)
            )
        return frozenset(out)

    return Principal(
        user_id=str(data.get("id") or data.get("userId") or data.get("sub") or ""),
        email=data.get("email"),
        roles=names(data.get("roles")),
        permissions=names(data.get("permissions")),
        raw_claims=dict(data),
        name=data.get("name") or data.get("fullName"),
        status=str(data.get("status") or "ACTIVE").upper(),
    )


def principal_from_claims(claims: Mapping[str, Any]) -> Principal:
    """JWT claims -> Principal (future AUTH_VERIFIER=jwt). TODO(CORE): claim names are [OPEN]."""
    data = dict(claims)
    data.setdefault("id", claims.get("sub"))
    return principal_from_me(data)
