"""Routes of the local CORE simulator. Same paths and payloads as the real CORE (see core-api /docs)."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, g, request

from app.extensions import spec
from app.routes._common import resp, validated
from app.schemas.common import json_response
from app.security.decorators import require_auth, require_service_token

from . import keys, service
from .schemas import (
    CoreUser,
    ForgotPasswordRequest,
    Jwks,
    LimitQuery,
    LoginRequest,
    LoginResponse,
    MarkReadRequest,
    NotificationCreateRequest,
    NotificationDto,
    NotificationPage,
    NotificationQuery,
    ServiceTokenRequest,
    ServiceTokenResponse,
    TopUpRequest,
    UnreadCount,
    WalletDto,
    WalletTxDto,
    WalletTxPage,
)

bp = Blueprint("mock_core", __name__)
TAGS = ["Mock CORE"]
REFRESH_COOKIE = "refreshToken"


def _with_refresh_cookie(body: LoginResponse, refresh: str) -> Response:
    r = json_response(body)
    cfg = current_app.extensions["settings"]
    r.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=cfg.refresh_token_ttl,
        httponly=True,
        secure=cfg.is_production,
        samesite="Lax",
        path="/api/v1/auth",
    )
    return r


@bp.post("/api/v1/auth/login")
@spec.validate(json=LoginRequest, resp=resp(HTTP_200=LoginResponse), tags=TAGS)
def login():
    body: LoginRequest = validated().json
    data, refresh = service.login(body.email, body.password)
    return _with_refresh_cookie(data, refresh)


@bp.post("/api/v1/auth/refresh")
@spec.validate(resp=resp(HTTP_200=LoginResponse), tags=TAGS)
def refresh():
    data, new_refresh = service.refresh(request.cookies.get(REFRESH_COOKIE))
    return _with_refresh_cookie(data, new_refresh)


@bp.post("/api/v1/auth/logout")
@require_auth
@spec.validate(resp=resp(HTTP_204=None), tags=TAGS)
def logout():
    service.logout(request.cookies.get(REFRESH_COOKIE))
    r = Response(status=204)
    r.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    return r


@bp.post("/api/v1/auth/password/forgot")
@spec.validate(json=ForgotPasswordRequest, resp=resp(HTTP_202=None), tags=TAGS)
def forgot_password():
    # CORE answers 202 whether or not the email exists (no account enumeration). The simulator sends no email.
    return Response(status=202)


@bp.get("/api/v1/auth/me")
@require_auth
@spec.validate(resp=resp(HTTP_200=CoreUser), tags=TAGS)
def me():
    return json_response(service.me(g.principal))


@bp.get("/.well-known/jwks.json")
@spec.validate(resp=resp(HTTP_200=Jwks), tags=TAGS)
def jwks():
    return json_response(Jwks.model_validate(keys.jwks()))


@bp.post("/internal/v1/service-auth/token")
@spec.validate(json=ServiceTokenRequest, resp=resp(HTTP_200=ServiceTokenResponse), tags=TAGS)
def service_token():
    body: ServiceTokenRequest = validated().json
    return json_response(service.service_token(body.clientId, body.clientSecret))


@bp.get("/api/v1/wallets/me")
@require_auth
@spec.validate(resp=resp(HTTP_200=WalletDto), tags=TAGS)
def wallet_me():
    return json_response(service.wallet(g.principal))


@bp.get("/api/v1/wallets/me/transactions")
@require_auth
@spec.validate(query=LimitQuery, resp=resp(HTTP_200=WalletTxPage), tags=TAGS)
def wallet_transactions():
    return json_response(service.transactions(g.principal, validated().query.limit))


@bp.post("/api/v1/wallets/me/top-ups")
@require_auth
@spec.validate(json=TopUpRequest, resp=resp(HTTP_201=WalletTxDto, HTTP_422=None), tags=TAGS)
def wallet_top_up():
    dto, status = service.top_up(g.principal, validated().json, request.headers.get("Idempotency-Key"))
    return json_response(dto, status=status)


@bp.get("/api/v1/notifications")
@require_auth
@spec.validate(query=NotificationQuery, resp=resp(HTTP_200=NotificationPage), tags=TAGS)
def notifications():
    q: NotificationQuery = validated().query
    return json_response(service.list_notifications(g.principal, q.read, q.limit))


@bp.get("/api/v1/notifications/unread-count")
@require_auth
@spec.validate(resp=resp(HTTP_200=UnreadCount), tags=TAGS)
def unread_count():
    return json_response(service.unread_count(g.principal))


@bp.patch("/api/v1/notifications/<string:notification_id>")
@require_auth
@spec.validate(json=MarkReadRequest, resp=resp(HTTP_200=NotificationDto), tags=TAGS)
def mark_notification(notification_id: str):
    return json_response(service.mark(g.principal, notification_id, validated().json.read))


@bp.post("/api/v1/notifications/read-all")
@require_auth
@spec.validate(resp=resp(HTTP_204=None), tags=TAGS)
def read_all():
    service.read_all(g.principal)
    return Response(status=204)


@bp.post("/internal/v1/notifications")
@require_service_token
@spec.validate(json=NotificationCreateRequest, resp=resp(HTTP_201=NotificationDto), tags=TAGS)
def create_notification():
    return json_response(service.create_notification(validated().json), status=201)
