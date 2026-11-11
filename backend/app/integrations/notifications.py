from __future__ import annotations

import logging

from flask import current_app

from app.errors import AppError, PublishError, UpstreamError

from .base import NotificationsClient
from .http import HttpClient

log = logging.getLogger("app.integrations.notifications")


class NotificationsMock(NotificationsClient):
    """Without CORE: stores the notification in the local CORE simulator (if enabled) so the portal
    can show it; otherwise only logs it. `sent` keeps every payload for tests."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    def create(self, payload: dict) -> None:
        self.sent.append(payload)
        if not current_app.extensions["settings"].mock_core_enabled:
            log.info(
                "mock_notification", extra={"type": payload.get("type"), "userId": payload.get("userId")}
            )
            return
        from app.mock_core.schemas import NotificationCreateRequest
        from app.mock_core.service import create_notification

        try:
            create_notification(NotificationCreateRequest.model_validate(payload), commit=False)
        except AppError as e:
            if e.code == "NOTIFICATION_ALREADY_EXISTS":
                return  # idempotent, same as CORE's 409
            raise PublishError(f"{e.code}: {e.detail}", retryable=False) from e


class NotificationsLive(NotificationsClient):
    """POST {CORE}/internal/v1/notifications with the service token."""

    def __init__(self, http: HttpClient):
        self.http = http

    def create(self, payload: dict) -> None:
        try:
            resp = self.http.request(
                "POST", "/internal/v1/notifications", json=payload, template="/internal/v1/notifications"
            )
        except UpstreamError as e:
            raise PublishError(f"CORE no disponible: {e.detail}", retryable=True) from e
        if resp.status_code == 409:
            return
        if resp.status_code in (401, 429) or resp.status_code >= 500:
            raise PublishError(f"CORE respondió {resp.status_code}", retryable=True)
        if resp.status_code >= 400:
            raise PublishError(f"CORE rechazó la notificación ({resp.status_code})", retryable=False)
