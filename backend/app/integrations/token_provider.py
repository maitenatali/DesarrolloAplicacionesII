"""CORE service-token cache (design §9.4). Request/response field names are [OPEN]: isolated in _fetch()."""

from __future__ import annotations

import threading
import time

import requests

from app.errors import UpstreamError


class TokenProvider:
    REFRESH_MARGIN_S = 60

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        *,
        timeout: tuple[float, float] = (3, 8),
        session: requests.Session | None = None,
    ):
        self._url = f"{base_url}/internal/v1/service-auth/token"
        self._id, self._secret = client_id, client_secret
        self._timeout = timeout
        self._session = session or requests.Session()
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0

    def invalidate(self) -> None:
        with self._lock:
            self._token = None

    def get_token(self) -> str:
        with self._lock:
            if self._token and time.monotonic() < self._expires_at - self.REFRESH_MARGIN_S:
                return self._token
            self._token, ttl = self._fetch()
            self._expires_at = time.monotonic() + ttl
            return self._token

    def _fetch(self) -> tuple[str, float]:
        # TODO(CORE): confirm exact request/response field names against CORE's /docs-json.
        try:
            resp = self._session.post(
                self._url, json={"clientId": self._id, "clientSecret": self._secret}, timeout=self._timeout
            )
        except requests.RequestException as e:
            raise UpstreamError(
                "core", "No se pudo obtener el token de servicio.", status=504, code="UPSTREAM_TIMEOUT"
            ) from e
        if resp.status_code >= 400:
            raise UpstreamError(
                "core", "CORE rechazó las credenciales de servicio.", upstream_status=resp.status_code
            )
        data = resp.json()
        token = data.get("accessToken") or data.get("access_token") or data.get("token")
        if not token:
            raise UpstreamError("core", "Respuesta de token de servicio inesperada.")
        ttl = float(data.get("expiresIn") or data.get("expires_in") or 900)
        return token, ttl
