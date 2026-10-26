from __future__ import annotations

from dataclasses import dataclass

from flask import current_app

from app.config import Settings

from .academic_live import AcademicLive
from .academic_mock import AcademicMock
from .base import AcademicClient, CoreEventsClient, StudentDirectoryClient
from .core_events_live import CoreEventsLive
from .core_events_mock import CoreEventsMock
from .http import HttpClient
from .outbound_auth import NoAuth, OutboundAuth, ServiceTokenAuth, StaticBearer
from .student_directory_live import StudentDirectoryLive
from .student_directory_mock import StudentDirectoryMock
from .token_provider import TokenProvider


@dataclass
class Integrations:
    academic: AcademicClient
    core_events: CoreEventsClient
    directory: StudentDirectoryClient
    modes: dict[str, str]


def _auth(kind: str, static_token: str, provider: TokenProvider | None) -> OutboundAuth:
    if kind == "static_bearer":
        return StaticBearer(static_token)
    if kind == "service_token" and provider is not None:
        return ServiceTokenAuth(provider)
    return NoAuth()


def build_integrations(cfg: Settings) -> Integrations:
    timeout = (cfg.http_timeout_connect, cfg.http_timeout_read)
    provider = None
    if "live" in (cfg.academic_mode, cfg.core_events_mode, cfg.student_directory_mode):
        provider = TokenProvider(
            cfg.core_base_url, cfg.core_service_client_id, cfg.core_service_client_secret, timeout=timeout
        )

    if cfg.academic_mode == "live":
        academic: AcademicClient = AcademicLive(
            HttpClient(
                "academic",
                cfg.academic_base_url,
                _auth(cfg.academic_auth, cfg.academic_static_token, provider),
                timeout=timeout,
                max_retries=cfg.http_max_retries,
            ),
            supports_teacher_filter=cfg.academic_supports_teacher_filter,
            cache_ttl=cfg.academic_course_cache_ttl,
            fanout_concurrency=cfg.academic_fanout_concurrency,
        )
    else:
        academic = AcademicMock()

    if cfg.core_events_mode == "live":
        events: CoreEventsClient = CoreEventsLive(
            HttpClient(
                "core",
                cfg.core_base_url,
                _auth(cfg.core_events_auth, cfg.core_events_static_token, provider),
                timeout=timeout,
                max_retries=cfg.http_max_retries,
            )
        )
    else:
        events = CoreEventsMock()

    if cfg.student_directory_mode == "live":
        directory: StudentDirectoryClient = StudentDirectoryLive(
            HttpClient(
                "student-directory",
                cfg.student_directory_base_url,
                _auth(cfg.student_directory_auth, cfg.student_directory_static_token, provider),
                timeout=timeout,
                max_retries=cfg.http_max_retries,
            )
        )
    else:
        directory = StudentDirectoryMock()

    return Integrations(
        academic,
        events,
        directory,
        {
            "academic": cfg.academic_mode,
            "coreEvents": cfg.core_events_mode,
            "studentDirectory": cfg.student_directory_mode,
        },
    )


def get_integrations() -> Integrations:
    return current_app.extensions["integrations"]
