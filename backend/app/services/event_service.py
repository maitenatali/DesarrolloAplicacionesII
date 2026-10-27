"""Transactional outbox: enqueue in the SAME transaction as the business change; dispatch after commit (§12)."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import timedelta
from typing import Any

from flask import Flask, current_app, g, has_request_context
from sqlalchemy import CursorResult, func, select

from app.errors import PublishError
from app.extensions import db
from app.integrations.factory import get_integrations
from app.models import OutboxEvent
from app.time import now_utc

log = logging.getLogger("app.events")


def build_envelope(
    event_type: str, subject: str, data: dict[str, Any], actor_id: str, correlation_id: str | None
) -> dict[str, Any]:
    return {
        "specVersion": "1.0",
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "source": "teacher",
        "occurredAt": now_utc().isoformat().replace("+00:00", "Z"),
        "subject": subject,
        "correlationId": correlation_id or str(uuid.uuid4()),  # CORE requires a UUID
        "causationId": None,
        "actor": {"type": "user" if actor_id else "system", "id": actor_id or "teacher-service"},
        "data": data,
    }


def enqueue(
    session,
    event_type: str,
    subject: str,
    data: dict[str, Any],
    actor_id: str,
    correlation_id: str | None = None,
) -> None:
    if correlation_id is None and has_request_context():
        correlation_id = getattr(g, "correlation_id", None)
    env = build_envelope(event_type, subject, data, actor_id, correlation_id)
    session.add(
        OutboxEvent(id=uuid.UUID(env["eventId"]), event_type=event_type, subject=subject, payload=env)
    )
    if has_request_context():
        g.outbox_dirty = True


def enqueue_notification(
    session,
    *,
    user_id: str,
    type_: str,
    title: str,
    message: str,
    action_url: str | None,
    source_reference: str,
) -> None:
    """Queue a CORE notification (POST /internal/v1/notifications) in the business transaction.

    CORE makes (userId, type, sourceModule, sourceReference) idempotent, so retries never duplicate it.
    """
    payload = {
        "userId": user_id,
        "type": type_,
        "title": title[:200],
        "message": message[:2000],
        "actionUrl": action_url,
        "sourceModule": "teacher",
        "sourceReference": source_reference[:200],
    }
    session.add(
        OutboxEvent(
            id=uuid.uuid4(),
            kind="NOTIFICATION",
            event_type=type_,
            subject=f"user/{user_id}",
            payload=payload,
        )
    )
    if has_request_context():
        g.outbox_dirty = True


def dispatch_due(batch: int | None = None, budget_s: float | None = None) -> dict[str, int]:
    """Deliver due PENDING events. FOR UPDATE SKIP LOCKED lets several dispatchers coexist."""
    cfg = current_app.extensions["settings"]
    batch = batch or cfg.outbox_batch_size
    integ = get_integrations()
    started = time.monotonic()
    sent = failed = retried = 0
    try:
        rows = (
            db.session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.status == "PENDING", OutboxEvent.next_attempt_at <= func.now())
                .order_by(OutboxEvent.created_at)
                .limit(batch)
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .all()
        )
        for ev in rows:
            if budget_s is not None and time.monotonic() - started > budget_s:
                break
            try:
                if ev.kind == "NOTIFICATION":
                    integ.notifications.create(ev.payload)
                else:
                    integ.core_events.publish(ev.payload)
                ev.status, ev.sent_at = "SENT", now_utc()
                sent += 1
            except PublishError as e:
                ev.attempts += 1
                ev.last_error = str(e)[:500]
                if ev.attempts >= cfg.outbox_max_attempts or not e.retryable:
                    ev.status = "FAILED"
                    failed += 1
                    log.error(
                        "outbox_event_failed", extra={"eventId": str(ev.id), "eventType": ev.event_type}
                    )
                else:
                    ev.next_attempt_at = now_utc() + timedelta(seconds=min(5 * 2**ev.attempts, 3600))
                    retried += 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return {"sent": sent, "failed": failed, "retried": retried}


def requeue_failed() -> int:
    n = 0
    for ev in db.session.execute(select(OutboxEvent).where(OutboxEvent.status == "FAILED")).scalars():
        ev.status, ev.attempts, ev.next_attempt_at = "PENDING", 0, now_utc()
        n += 1
    db.session.commit()
    return n


def prune_sent(days: int = 30) -> int:
    from sqlalchemy import delete

    res: CursorResult = db.session.execute(  # type: ignore[assignment]  # DML returns a CursorResult
        delete(OutboxEvent).where(
            OutboxEvent.status == "SENT",
            OutboxEvent.sent_at < func.now() - timedelta(days=days),  # DB clock, same as sent_at writers
        )
    )
    db.session.commit()
    return res.rowcount or 0


def register_inline_dispatch(app: Flask) -> None:
    """After the response is sent, try once to deliver what this request enqueued (failures are swallowed)."""

    @app.after_request
    def _hook(resp):
        if getattr(g, "outbox_dirty", False) and app.extensions["settings"].events_inline_dispatch:

            def _run() -> None:
                try:
                    with app.app_context():
                        dispatch_due(batch=5, budget_s=2)
                except Exception:  # worker will retry
                    log.warning("inline_dispatch_failed", exc_info=True)

            resp.call_on_close(_run)
        return resp
