"""Typed settings parsed once from the environment. Fails fast listing ALL problems (design §5)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo


class ConfigError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Invalid configuration:\n - " + "\n - ".join(problems))


def _csv(value: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in value.split(",") if p.strip())


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    port: int = 8080
    app_timezone: str = "America/Argentina/Buenos_Aires"
    log_level: str = "INFO"
    cors_origins: tuple[str, ...] = ()

    database_url: str = ""
    db_pool_size: int = 5
    db_pool_recycle: int = 1800

    auth_verifier: str = "jwt"
    token_cache_ttl: int = 60
    token_cache_max_entries: int = 2000
    core_me_path: str = "/api/v1/auth/me"
    service_tokens: tuple[str, ...] = ()
    core_jwks_url: str = ""
    jwt_algorithms: tuple[str, ...] = ("RS256",)
    jwt_issuer: str = "uadenet-core"
    jwt_audience: str = "uadenet"
    jwt_leeway_seconds: int = 30
    teacher_roles: tuple[str, ...] = ("TEACHER",)
    service_roles: tuple[str, ...] = ("SERVICE",)
    service_modules: tuple[str, ...] = ("student", "analytics")  # service tokens allowed on /results
    admin_roles: tuple[str, ...] = ("ACADEMIC_ADMIN", "ADMIN_STAFF")
    gateway_hmac_enabled: bool = False
    gateway_hmac_secret: str = ""
    invalid_token_limit_per_minute: int = 30

    academic_auth: str = "static_bearer"
    academic_static_token: str = ""
    core_events_auth: str = "service_token"
    core_events_static_token: str = ""
    student_directory_auth: str = "static_bearer"
    student_directory_static_token: str = ""

    mock_core_enabled: bool = False
    mock_core_service_clients: tuple[str, ...] = ()  # "clientId:secret" pairs accepted by the simulator
    mock_dataset: str = "base"  # base = test fixtures (Appendix B) | demo = realistic data for demos
    access_token_ttl: int = 900
    refresh_token_ttl: int = 7 * 24 * 3600
    student_portal_base_url: str = "/student"  # prefix of actionUrl in notifications sent to students

    academic_mode: str = "mock"
    core_events_mode: str = "mock"
    student_directory_mode: str = "mock"
    notifications_mode: str = "mock"

    core_base_url: str = "https://core-api-production-e458.up.railway.app"
    core_service_client_id: str = ""
    core_service_client_secret: str = ""
    academic_base_url: str = ""
    academic_supports_teacher_filter: bool = False
    student_directory_base_url: str = ""
    http_timeout_connect: float = 3.0
    http_timeout_read: float = 8.0
    http_max_retries: int = 2
    academic_course_cache_ttl: int = 60
    academic_fanout_concurrency: int = 6

    passing_grade: Decimal = Decimal("4.0")
    regular_threshold: Decimal = Decimal("75.0")
    final_exam_types: tuple[str, ...] = ("FINAL",)
    final_requires_regular: bool = True
    lock_after_acta: bool = True
    annul_reverts_academic: bool = False

    outbox_poll_seconds: int = 5
    outbox_batch_size: int = 20
    outbox_max_attempts: int = 10
    events_inline_dispatch: bool = True

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def as_flask_config(self) -> dict[str, Any]:
        return {
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_pre_ping": True,
                "pool_recycle": self.db_pool_recycle,
                "pool_size": self.db_pool_size,
            },
            "MAX_CONTENT_LENGTH": 1024 * 1024,
            "JSON_SORT_KEYS": False,
        }

    @classmethod
    def from_env(cls, config_name: str | None = None, environ: Mapping[str, str] | None = None) -> Settings:
        env: dict[str, str] = dict(os.environ if environ is None else environ)
        if config_name == "test":
            env.setdefault("APP_ENV", "test")
            env.setdefault("AUTH_VERIFIER", "dev")
            env.setdefault("INTEGRATIONS_MODE", "mock")
            env.setdefault("EVENTS_INLINE_DISPATCH", "false")
        problems: list[str] = []

        def s(name: str, default: str = "") -> str:
            return env.get(name, default).strip()

        def i(name: str, default: int) -> int:
            raw = s(name)
            if not raw:
                return default
            try:
                return int(raw)
            except ValueError:
                problems.append(f"{name} must be an integer (got {raw!r})")
                return default

        def f(name: str, default: float) -> float:
            raw = s(name)
            if not raw:
                return default
            try:
                return float(raw)
            except ValueError:
                problems.append(f"{name} must be a number (got {raw!r})")
                return default

        def d(name: str, default: str) -> Decimal:
            raw = s(name) or default
            try:
                return Decimal(raw)
            except InvalidOperation:
                problems.append(f"{name} must be a decimal (got {raw!r})")
                return Decimal(default)

        def b(name: str, default: bool) -> bool:
            raw = s(name).lower()
            if not raw:
                return default
            if raw in ("1", "true", "yes", "on"):
                return True
            if raw in ("0", "false", "no", "off"):
                return False
            problems.append(f"{name} must be a boolean (got {raw!r})")
            return default

        def c(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
            raw = s(name)
            return _csv(raw) if raw else default

        def choice(name: str, default: str, allowed: tuple[str, ...]) -> str:
            raw = s(name) or default
            if raw not in allowed:
                problems.append(f"{name} must be one of {allowed} (got {raw!r})")
            return raw

        global_mode = choice("INTEGRATIONS_MODE", "mock", ("mock", "live"))

        def mode(name: str) -> str:
            return choice(name, global_mode, ("mock", "live")) if s(name) else global_mode

        app_env = choice("APP_ENV", "development", ("development", "test", "production"))
        auth_verifier = choice("AUTH_VERIFIER", "jwt", ("introspect", "jwt", "dev"))
        if auth_verifier == "dev" and app_env == "production":
            problems.append("AUTH_VERIFIER=dev is refused when APP_ENV=production")
        tz = s("APP_TIMEZONE") or cls.app_timezone
        try:
            ZoneInfo(tz)
        except Exception:
            problems.append(f"APP_TIMEZONE {tz!r} is not a valid timezone")

        settings = cls(
            app_env=app_env,
            port=i("PORT", 8080),
            app_timezone=tz,
            log_level=(s("LOG_LEVEL") or "INFO").upper(),
            cors_origins=c("CORS_ORIGINS", ()),
            database_url=s("DATABASE_URL"),
            db_pool_size=i("DB_POOL_SIZE", 5),
            db_pool_recycle=i("DB_POOL_RECYCLE", 1800),
            auth_verifier=auth_verifier,
            token_cache_ttl=i("TOKEN_CACHE_TTL_SECONDS", 60),
            token_cache_max_entries=i("TOKEN_CACHE_MAX_ENTRIES", 2000),
            core_me_path=s("CORE_ME_PATH") or "/api/v1/auth/me",
            service_tokens=c("SERVICE_TOKENS", ()),
            core_jwks_url=s("CORE_JWKS_URL"),
            jwt_algorithms=c("JWT_ALGORITHMS", ("RS256",)),
            jwt_issuer=s("JWT_ISSUER", cls.jwt_issuer),
            jwt_audience=s("JWT_AUDIENCE", cls.jwt_audience),
            jwt_leeway_seconds=i("JWT_LEEWAY_SECONDS", 30),
            teacher_roles=c("TEACHER_ROLES", cls.teacher_roles),
            service_roles=c("SERVICE_ROLES", cls.service_roles),
            service_modules=c("SERVICE_MODULES", cls.service_modules),
            mock_core_enabled=b("MOCK_CORE_ENABLED", False),
            mock_core_service_clients=c("MOCK_CORE_SERVICE_CLIENTS", ()),
            mock_dataset=choice("MOCK_DATASET", "base", ("base", "demo")),
            access_token_ttl=i("ACCESS_TOKEN_TTL_SECONDS", 900),
            refresh_token_ttl=i("REFRESH_TOKEN_TTL_SECONDS", 7 * 24 * 3600),
            student_portal_base_url=(s("STUDENT_PORTAL_BASE_URL") or cls.student_portal_base_url).rstrip("/"),
            admin_roles=c("ADMIN_ROLES", cls.admin_roles),
            gateway_hmac_enabled=b("GATEWAY_HMAC_ENABLED", False),
            gateway_hmac_secret=s("GATEWAY_HMAC_SECRET"),
            invalid_token_limit_per_minute=i("INVALID_TOKEN_LIMIT_PER_MINUTE", 30),
            academic_auth=choice(
                "ACADEMIC_AUTH_VERIFIER", "static_bearer", ("static_bearer", "service_token", "none")
            ),
            academic_static_token=s("ACADEMIC_STATIC_TOKEN"),
            core_events_auth=choice(
                "CORE_EVENTS_AUTH_VERIFIER", "service_token", ("static_bearer", "service_token", "none")
            ),
            core_events_static_token=s("CORE_EVENTS_STATIC_TOKEN"),
            student_directory_auth=choice(
                "STUDENT_DIRECTORY_AUTH_VERIFIER", "static_bearer", ("static_bearer", "service_token", "none")
            ),
            student_directory_static_token=s("STUDENT_DIRECTORY_STATIC_TOKEN"),
            academic_mode=mode("ACADEMIC_MODE"),
            core_events_mode=mode("CORE_EVENTS_MODE"),
            student_directory_mode=mode("STUDENT_DIRECTORY_MODE"),
            notifications_mode=mode("NOTIFICATIONS_MODE"),
            core_base_url=(s("CORE_BASE_URL") or cls.core_base_url).rstrip("/"),
            core_service_client_id=s("CORE_SERVICE_CLIENT_ID"),
            core_service_client_secret=s("CORE_SERVICE_CLIENT_SECRET"),
            academic_base_url=s("ACADEMIC_BASE_URL").rstrip("/"),
            academic_supports_teacher_filter=b("ACADEMIC_SUPPORTS_TEACHER_FILTER", False),
            student_directory_base_url=s("STUDENT_DIRECTORY_BASE_URL").rstrip("/"),
            http_timeout_connect=f("HTTP_TIMEOUT_CONNECT", 3.0),
            http_timeout_read=f("HTTP_TIMEOUT_READ", 8.0),
            http_max_retries=i("HTTP_MAX_RETRIES", 2),
            academic_course_cache_ttl=i("ACADEMIC_COURSE_CACHE_TTL", 60),
            academic_fanout_concurrency=i("ACADEMIC_FANOUT_CONCURRENCY", 6),
            passing_grade=d("PASSING_GRADE", "4.0"),
            regular_threshold=d("REGULAR_THRESHOLD", "75.0"),
            final_exam_types=c("FINAL_EXAM_TYPES", ("FINAL",)),
            final_requires_regular=b("FINAL_REQUIRES_REGULAR", True),
            lock_after_acta=b("LOCK_AFTER_ACTA", True),
            annul_reverts_academic=b("ANNUL_REVERTS_ACADEMIC", False),
            outbox_poll_seconds=i("OUTBOX_POLL_SECONDS", 5),
            outbox_batch_size=i("OUTBOX_BATCH_SIZE", 20),
            outbox_max_attempts=i("OUTBOX_MAX_ATTEMPTS", 10),
            events_inline_dispatch=b("EVENTS_INLINE_DISPATCH", True),
        )
        if not settings.database_url:
            problems.append("DATABASE_URL is required")
        for name, m, mode_ in (
            ("ACADEMIC_BASE_URL", settings.academic_base_url, settings.academic_mode),
            (
                "STUDENT_DIRECTORY_BASE_URL",
                settings.student_directory_base_url,
                settings.student_directory_mode,
            ),
        ):
            if mode_ == "live" and not m:
                problems.append(f"{name} is required when its mode is live")
        if settings.auth_verifier == "jwt" and not (settings.core_jwks_url or settings.mock_core_enabled):
            problems.append(
                "CORE_JWKS_URL is required when AUTH_VERIFIER=jwt (or set MOCK_CORE_ENABLED=true)"
            )
        if problems:
            raise ConfigError(problems)
        return settings
