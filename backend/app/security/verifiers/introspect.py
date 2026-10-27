from __future__ import annotations

import hashlib
import threading

import requests
from cachetools import TTLCache

from app.errors import ServiceUnavailable, Unauthorized
from app.security.principal import Principal, principal_from_me

from .base import TokenVerifier


class CoreIntrospectionVerifier(TokenVerifier):
    """Opaque bearer token: ask CORE who owns it (GET /auth/me). Fails CLOSED (design §8.2)."""

    def __init__(
        self,
        base_url: str,
        me_path: str,
        *,
        cache_ttl: int = 60,
        cache_max: int = 2000,
        timeout: tuple[float, float] = (2, 4),
        session: requests.Session | None = None,
    ):
        self._url = f"{base_url.rstrip('/')}{me_path}"
        self._timeout = timeout
        self._session = session or requests.Session()
        self._cache: TTLCache | None = (
            TTLCache(maxsize=cache_max, ttl=max(cache_ttl, 1)) if cache_ttl > 0 else None
        )
        self._lock = threading.Lock()

    def verify(self, token: str) -> Principal:
        key = hashlib.sha256(token.encode()).hexdigest()  # never store/log the raw token
        if self._cache is not None:
            with self._lock:
                hit = self._cache.get(key)
            if hit is not None:
                return hit
        try:
            resp = self._session.get(
                self._url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=self._timeout,
            )
        except requests.RequestException as e:
            raise ServiceUnavailable("No se pudo validar la sesión.", code="AUTH_UNAVAILABLE") from e
        if resp.status_code in (401, 403):
            raise Unauthorized("Token inválido o vencido.", code="TOKEN_INVALID")
        if resp.status_code >= 500 or resp.status_code >= 400:
            raise ServiceUnavailable("No se pudo validar la sesión.", code="AUTH_UNAVAILABLE")
        principal = principal_from_me(resp.json())
        if principal.status != "ACTIVE" or not principal.user_id:
            raise Unauthorized("Usuario inactivo.", code="TOKEN_INVALID")
        if self._cache is not None:
            with self._lock:
                self._cache[key] = principal
        return principal
