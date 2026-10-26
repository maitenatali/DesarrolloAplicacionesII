"""The ONLY place that reads the clock. Never call datetime.now()/date.today() elsewhere."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from flask import current_app


def _tz() -> ZoneInfo:
    return current_app.extensions["settings"].tz


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_local() -> datetime:
    return now_utc().astimezone(_tz())


def today_local() -> date:
    return now_local().date()


def to_local(dt: datetime) -> datetime:
    return dt.astimezone(_tz())
