from __future__ import annotations

import logging

from app.errors import PublishError

from .base import CoreEventsClient

log = logging.getLogger("app.integrations.core_events.mock")


class CoreEventsMock(CoreEventsClient):
    def __init__(self) -> None:
        self.published: list[dict] = []
        self._fail: list[PublishError] = []

    def fail_next(self, n: int = 1, *, retryable: bool = True) -> None:
        self._fail.extend(PublishError("Fallo simulado", retryable=retryable) for _ in range(n))

    def publish(self, envelope: dict) -> None:
        if self._fail:
            raise self._fail.pop(0)
        self.published.append(envelope)
        log.info(
            "mock_event_published",
            extra={"eventType": envelope.get("eventType"), "eventId": envelope.get("eventId")},
        )
