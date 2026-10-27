"""Test fixtures. Tests need a REAL PostgreSQL (partial indexes, views, advisory locks, ON CONFLICT).

Database source, in order: $TEST_DATABASE_URL -> testcontainers (postgres:16, needs Docker) -> pixeltable-pgserver
(pip-installable embedded Postgres, handy where Docker is unavailable).
"""

from __future__ import annotations

import os

import pytest
from flask_migrate import upgrade
from freezegun import freeze_time
from sqlalchemy import text

from app import MIGRATIONS_DIR, create_app
from app.extensions import db
from app.integrations.factory import build_integrations

FROZEN_NOW = "2026-10-19 15:00:00"  # 12:00 America/Argentina/Buenos_Aires
SERVICE_TOKEN = "svc-token-1"
_server = None  # keep the embedded server alive for the whole session


def _psycopg_url(url: str) -> str:
    return (
        url.replace("postgresql://", "postgresql+psycopg://", 1) if url.startswith("postgresql://") else url
    )


@pytest.fixture(scope="session")
def database_url(tmp_path_factory):
    global _server
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield _psycopg_url(url)
        return
    try:
        from testcontainers.postgres import PostgresContainer

        container = PostgresContainer("postgres:16")
        container.start()
    except Exception:
        container = None
    if container is not None:
        yield _psycopg_url(container.get_connection_url().replace("+psycopg2", ""))
        container.stop()
        return
    try:
        import pixeltable_pgserver
    except ImportError:
        pytest.skip(
            "No PostgreSQL available: set TEST_DATABASE_URL, start Docker, or `pip install pixeltable-pgserver`"
        )
    _server = pixeltable_pgserver.get_server(str(tmp_path_factory.mktemp("pg")), cleanup_mode="stop")
    import psycopg

    base = _server.get_uri()
    with psycopg.connect(base, autocommit=True) as conn:
        conn.execute("create database teacher_test")
    yield _psycopg_url(base.rsplit("/", 1)[0] + "/teacher_test")


def make_app(database_url: str, **env: str):
    environ = {"DATABASE_URL": database_url, "SERVICE_TOKENS": f"{SERVICE_TOKEN},svc-token-2", **env}
    return create_app("test", environ)


@pytest.fixture(scope="session")
def app(database_url):
    application = make_app(database_url)
    with application.app_context():
        upgrade(directory=MIGRATIONS_DIR)
    return application


TABLES = (
    "acta_detalle, acta, calificacion, examen, asistencia, clase, outbox_event, "
    "mock_core_user, mock_core_session, mock_core_wallet_tx, mock_core_notification"
)


@pytest.fixture(autouse=True)
def _clean(app):
    with app.app_context():
        db.session.execute(text(f"truncate {TABLES} restart identity cascade"))
        db.session.commit()
    app.extensions["integrations"] = build_integrations(app.extensions["settings"])
    from app.security import decorators

    decorators._limiter = decorators.InvalidTokenLimiter()
    yield


@pytest.fixture(autouse=True)
def _frozen_clock():
    with freeze_time(FROZEN_NOW, tick=True):
        yield


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def integ(app):
    return app.extensions["integrations"]


@pytest.fixture()
def seeded(app):
    """Course 42 with attendance, exams and grades (no acta, so nothing is locked)."""
    from app.seed import load_seed

    with app.app_context():
        load_seed(include_acta=False)


@pytest.fixture()
def seeded_with_acta(app):
    from app.seed import load_seed

    with app.app_context():
        load_seed(include_acta=True)


@pytest.fixture()
def db_session(app):
    with app.app_context():
        yield db.session


# ---------------------------------------------------------------- end-to-end (real JWT, local CORE)
STUDENT_CLIENT = ("student-service", "student-secret")


@pytest.fixture()
def e2e_app(app, database_url):
    """App as it runs in this delivery: RS256 JWTs signed by the local CORE simulator, all modules mocked."""
    from app.mock_core import keys
    from app.seed import load_mock_core_seed

    keys.reset_cache()
    application = make_app(
        database_url,
        APP_ENV="development",
        AUTH_VERIFIER="jwt",
        MOCK_CORE_ENABLED="true",
        MOCK_CORE_SERVICE_CLIENTS=f"{STUDENT_CLIENT[0]}:{STUDENT_CLIENT[1]}",
        EVENTS_INLINE_DISPATCH="false",
    )
    with application.app_context():
        load_mock_core_seed()
    return application
