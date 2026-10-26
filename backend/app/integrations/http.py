"""Shared outbound HTTP client (design §9.3). Every call has a timeout; POST is never retried."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from flask import g, has_request_context
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.errors import UpstreamError

from .outbound_auth import NoAuth, OutboundAuth

log = logging.getLogger("app.integrations.http")


class HttpClient:
    def __init__(
        self,
        module: str,
        base_url: str,
        auth: OutboundAuth | None = None,
        *,
        timeout: tuple[float, float] = (3, 8),
        max_retries: int = 2,
        pool_maxsize: int = 10,
        session: requests.Session | None = None,
    ):
        self.module = module
        self.base_url = base_url.rstrip("/")
        self.auth = auth or NoAuth()
        self.timeout = timeout
        self.session = session or requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=(502, 503, 504),
            allowed_methods=("GET", "PUT"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=pool_maxsize)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
        template: str | None = None,
    ) -> requests.Response:
        """Returns the response for any status < 500 (callers interpret 4xx). 5xx/timeouts raise UpstreamError."""
        url = f"{self.base_url}{path}"
        for attempt in (1, 2):
            headers = {"Accept": "application/json", **self.auth.headers()}
            if has_request_context() and getattr(g, "correlation_id", None):
                headers["X-Correlation-Id"] = g.correlation_id
            started = time.perf_counter()
            try:
                resp = self.session.request(
                    method, url, json=json, params=params, headers=headers, timeout=self.timeout
                )
            except requests.RequestException as e:
                log.warning(
                    "upstream_unreachable",
                    extra={"module": self.module, "method": method, "path": template or path},
                )
                raise UpstreamError(
                    self.module,
                    status=504,
                    code="UPSTREAM_TIMEOUT",
                    detail=f"El módulo {self.module} no respondió a tiempo.",
                ) from e
            log.info(
                "upstream_call",
                extra={
                    "module": self.module,
                    "method": method,
                    "path": template or path,
                    "upstreamStatus": resp.status_code,
                    "durationMs": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            if resp.status_code == 401 and attempt == 1:
                self.auth.on_unauthorized()
                continue
            if resp.status_code >= 500:
                raise UpstreamError(self.module, upstream_status=resp.status_code)
            return resp
        raise AssertionError("unreachable")  # pragma: no cover

    def rejected(self, resp: requests.Response) -> UpstreamError:
        """Build the error for an unexpected 4xx (our bug or bad config)."""
        return UpstreamError(
            self.module,
            f"El módulo {self.module} rechazó la solicitud.",
            code="UPSTREAM_REJECTED",
            upstream_status=resp.status_code,
        )
