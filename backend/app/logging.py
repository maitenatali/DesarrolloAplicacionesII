"""JSON logging with correlation id; secrets are redacted (design §14)."""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from datetime import UTC, datetime

from flask import Flask, g, request

_SECRET_KEYS = re.compile(r"(password|secret|token|authorization)", re.I)
_STD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.correlationId = getattr(g, "correlation_id", None)
            record.userId = getattr(g, "user_id", None)
        except RuntimeError:  # outside app context
            record.correlationId = None
            record.userId = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        for k, v in record.__dict__.items():
            if k in _STD or k.startswith("_"):
                continue
            payload[k] = "[REDACTED]" if _SECRET_KEYS.search(k) else v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(app: Flask) -> None:
    level = app.extensions["settings"].log_level
    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationFilter())
    root.handlers = [handler]
    root.setLevel(level)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def register_correlation_id(app: Flask) -> None:
    access = logging.getLogger("app.access")

    @app.before_request
    def _start():
        inbound = request.headers.get("X-Correlation-Id", "").strip()
        g.correlation_id = inbound[:100] if inbound else str(uuid.uuid4())
        g.started = time.perf_counter()

    @app.after_request
    def _end(resp):
        resp.headers["X-Correlation-Id"] = getattr(g, "correlation_id", "")
        rule = request.url_rule.rule if request.url_rule else request.path
        access.info(
            "request",
            extra={
                "method": request.method,
                "path": rule,
                "status": resp.status_code,
                "durationMs": round(
                    (time.perf_counter() - getattr(g, "started", time.perf_counter())) * 1000, 1
                ),
            },
        )
        return resp


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def _headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        if request.path.startswith("/api/") and not request.path.startswith("/apidocs"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp
