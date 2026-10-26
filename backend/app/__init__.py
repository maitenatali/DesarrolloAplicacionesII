"""teacher-service application factory (design Appendix C)."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

from flask import Flask, redirect, request

from app.config import Settings
from app.errors import register_error_handlers
from app.extensions import db, migrate, spec
from app.integrations.factory import build_integrations
from app.logging import configure_logging, register_correlation_id, register_security_headers
from app.security.gateway_hmac import register_gateway_hmac
from app.security.verifiers import build_verifier

MIGRATIONS_DIR = str(Path(__file__).resolve().parent.parent / "migrations")


def _register_cors(app: Flask, origins: tuple[str, ...]) -> None:
    if not origins:
        return  # CORS disabled: same-origin via gateway / Vite proxy

    @app.before_request
    def _preflight():
        if request.method == "OPTIONS" and request.headers.get("Origin") in origins:
            return "", 204
        return None

    @app.after_request
    def _cors(resp):
        origin = request.headers.get("Origin")
        if origin in origins:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Correlation-Id"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, OPTIONS"
            resp.headers["Access-Control-Expose-Headers"] = "X-Correlation-Id, Location, X-Degraded"
        return resp


def create_app(
    config_name: str | None = None, environ: Mapping[str, str] | None = None, settings: Settings | None = None
) -> Flask:
    app = Flask(__name__)
    cfg = settings or Settings.from_env(
        config_name, environ
    )  # fail-fast: raises ConfigError listing ALL problems
    app.extensions["settings"] = cfg
    app.config.update(cfg.as_flask_config())
    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db, directory=MIGRATIONS_DIR)

    app.extensions["verifier"] = build_verifier(cfg)
    app.extensions["integrations"] = build_integrations(cfg)

    register_correlation_id(app)
    register_security_headers(app)
    register_gateway_hmac(app)
    _register_cors(app, cfg.cors_origins)

    from app.routes import actas, attendance, courses, exams, grades, health, results
    from app.services.event_service import register_inline_dispatch

    for module in (health, courses, exams, grades, attendance, actas, results):
        app.register_blueprint(module.bp, url_prefix="/api/v1")
    register_error_handlers(app)
    register_inline_dispatch(app)
    spec.register(app)  # SpecTree -> /apidocs/swagger, /apidocs/openapi.json
    app.add_url_rule("/apidocs", "apidocs_index", lambda: redirect("/apidocs/swagger/"))

    from app.cli import register_cli

    register_cli(app)
    if cfg.gateway_hmac_enabled:
        logging.getLogger("app").warning("gateway_hmac_enabled_but_verify_not_implemented")
    return app
