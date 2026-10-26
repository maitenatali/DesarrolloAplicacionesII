from __future__ import annotations

from app.errors import PublishError, UpstreamError

from .base import CoreEventsClient
from .http import HttpClient


class CoreEventsLive(CoreEventsClient):
    """POST {CORE}/internal/v1/events. 4xx (except 429/401) = not retryable (e.g. unknown event type)."""

    def __init__(self, http: HttpClient):
        self.http = http

    def publish(self, envelope: dict) -> None:
        try:
            resp = self.http.request(
                "POST", "/internal/v1/events", json=envelope, template="/internal/v1/events"
            )
        except UpstreamError as e:
            raise PublishError(f"CORE no disponible: {e.detail}", retryable=True) from e
        if resp.status_code in (401, 429):
            raise PublishError(f"CORE respondió {resp.status_code}", retryable=True)
        if resp.status_code >= 400:
            raise PublishError(
                f"CORE rechazó el evento ({resp.status_code}): {resp.text[:200]}", retryable=False
            )
