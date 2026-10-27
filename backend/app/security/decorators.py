from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, g, request

from app.errors import Forbidden, TooManyRequests, Unauthorized
from app.security.principal import Principal


class InvalidTokenLimiter:
    """Simple in-memory per-IP counter so we can't be used to hammer CORE with bad tokens."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, q: deque[float], now: float) -> None:
        while q and now - q[0] > 60:
            q.popleft()

    def check(self, ip: str, limit: int) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[ip]
            self._prune(q, now)
            if len(q) >= limit:
                raise TooManyRequests("Demasiados intentos con token inválido.")

    def record(self, ip: str) -> None:
        with self._lock:
            self._hits[ip].append(time.monotonic())


_limiter = InvalidTokenLimiter()


def _settings():
    return current_app.extensions["settings"]


def _bearer() -> str:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


def _authenticate() -> Principal:
    cfg = _settings()
    token = _bearer()
    if not token and cfg.auth_verifier == "dev":
        token = request.headers.get("X-Dev-User", "").strip()
    if not token:
        raise Unauthorized("Falta el token de autenticación.", code="TOKEN_INVALID")
    ip = request.remote_addr or "?"
    _limiter.check(ip, cfg.invalid_token_limit_per_minute)
    try:
        principal = current_app.extensions["verifier"].verify(token)
    except Unauthorized:
        _limiter.record(ip)
        raise
    return principal


def _set(principal: Principal) -> None:
    g.principal = principal
    g.user_id = principal.user_id


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        _set(_authenticate())
        return fn(*args, **kwargs)

    return wrapper


def is_admin(principal: Principal) -> bool:
    return bool(principal.roles & set(_settings().admin_roles))


def require_teacher(fn):
    """Teacher roles, or admin roles (read-only support staff; writes still need course ownership)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        p: Principal = g.principal
        cfg = _settings()
        if not (p.roles & set(cfg.teacher_roles) or p.roles & set(cfg.admin_roles)):
            raise Forbidden("No tenés permisos de docente.", code="FORBIDDEN")
        return fn(*args, **kwargs)

    return wrapper


def _is_allowed_service(principal: Principal, cfg) -> bool:
    if principal.is_service:
        return principal.service in set(cfg.service_modules) or bool(principal.roles & set(cfg.service_roles))
    return bool(principal.roles & set(cfg.service_roles))


def require_service(fn):
    """Service-to-service routes (/results): static SERVICE_TOKENS (constant-time compare) first; else a CORE
    service token (kind=service) whose module is in SERVICE_MODULES."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        cfg = _settings()
        token = _bearer()
        if token and any(hmac.compare_digest(token.encode(), t.encode()) for t in cfg.service_tokens):
            _set(
                Principal(
                    user_id="service", is_service=True, service="static", roles=frozenset(cfg.service_roles)
                )
            )
            return fn(*args, **kwargs)
        principal = _authenticate()
        if not _is_allowed_service(principal, cfg):
            raise Forbidden("Solo disponible para servicios.", code="FORBIDDEN")
        _set(principal)
        return fn(*args, **kwargs)

    return wrapper


def require_service_token(fn):
    """Any CORE service token (kind=service). Used by the CORE simulator's /internal/v1/* routes."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        principal = _authenticate()
        if not principal.is_service:
            raise Forbidden("Solo disponible para tokens de servicio.", code="AUTH_FORBIDDEN")
        _set(principal)
        return fn(*args, **kwargs)

    return wrapper
