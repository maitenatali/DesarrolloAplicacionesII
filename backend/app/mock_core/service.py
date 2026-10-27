"""Business logic of the local CORE simulator (only active with MOCK_CORE_ENABLED=true).

Mirrors the public CORE contract (https://core-api-production-e458.up.railway.app/docs) so the frontend
can switch to the real CORE by changing a base URL. It is NOT a production identity provider.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import jwt as pyjwt
from flask import current_app
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from app.errors import AppError, BadRequest, Conflict, Forbidden, NotFound, Unauthorized
from app.extensions import db
from app.models import MockCoreNotification, MockCoreSession, MockCoreUser, MockCoreWalletTx
from app.security.principal import Principal
from app.time import now_utc

from . import keys
from .schemas import (
    CoreUser,
    LoginResponse,
    NotificationCreateRequest,
    NotificationDto,
    NotificationPage,
    ServiceTokenResponse,
    TopUpRequest,
    UnreadCount,
    WalletDto,
    WalletTxDto,
    WalletTxPage,
)


class Unprocessable(AppError):
    status, title, code = 422, "Unprocessable Entity", "UNPROCESSABLE"


def _cfg():
    return current_app.extensions["settings"]


def _iso(d: datetime | None) -> str | None:
    return d.astimezone(UTC).isoformat().replace("+00:00", "Z") if d else None


def _money(v: Decimal) -> str:
    return f"{v.quantize(Decimal('0.01'))}"


# ── tokens ──────────────────────────────────────────────────────────────────────────────
def _sign(claims: dict[str, Any], ttl: int) -> str:
    kid, key = keys.signing_key()
    now = now_utc()
    cfg = _cfg()
    payload = {
        "iss": cfg.jwt_issuer or "uadenet-core",
        "aud": cfg.jwt_audience or "uadenet",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "jti": str(uuid.uuid4()),
        **claims,
    }
    return pyjwt.encode(payload, key, algorithm="RS256", headers={"kid": kid})


def _decode(token: str) -> dict[str, Any]:
    cfg = _cfg()
    try:
        kid = pyjwt.get_unverified_header(token).get("kid")
        key = keys.public_key_for(kid)
        if key is None:
            raise pyjwt.InvalidKeyError("unknown kid")
        return pyjwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=cfg.jwt_audience or "uadenet",
            issuer=cfg.jwt_issuer or "uadenet-core",
        )
    except pyjwt.ExpiredSignatureError as e:
        raise Unauthorized("La sesión venció.", code="AUTH_TOKEN_EXPIRED") from e
    except pyjwt.PyJWTError as e:
        raise Unauthorized("Token inválido.", code="AUTH_TOKEN_INVALID") from e


def _core_user(u: MockCoreUser) -> CoreUser:
    return CoreUser(
        id=u.id,
        email=u.email,
        careerIds=list(u.career_ids or []),
        roles=list(u.roles or []),
        permissions=list(u.permissions or []),
        status=u.status,  # type: ignore[arg-type]
    )


def _access_token(u: MockCoreUser) -> str:
    return _sign(
        {
            "sub": u.id,
            "kind": "user",
            "email": u.email,
            "name": f"{u.first_name} {u.last_name}",
            "roles": list(u.roles or []),
            "permissions": list(u.permissions or []),
            "careerIds": list(u.career_ids or []),
            "status": u.status,
            "typ": "access",
        },
        _cfg().access_token_ttl,
    )


def _new_session(u: MockCoreUser) -> str:
    jti = str(uuid.uuid4())
    ttl = _cfg().refresh_token_ttl
    db.session.add(MockCoreSession(jti=jti, user_id=u.id, expires_at=now_utc() + timedelta(seconds=ttl)))
    return _sign({"sub": u.id, "typ": "refresh", "sid": jti}, ttl)


def login(email: str, password: str) -> tuple[LoginResponse, str]:
    u = db.session.scalar(select(MockCoreUser).where(func.lower(MockCoreUser.email) == email.strip().lower()))
    if u is None or not check_password_hash(u.password_hash, password):
        raise Unauthorized("Email o contraseña incorrectos.", code="AUTH_INVALID_CREDENTIALS")
    if u.status != "ACTIVE":
        raise Forbidden("La cuenta no está activa.", code="AUTH_ACCOUNT_NOT_ACTIVE", accountStatus=u.status)
    refresh = _new_session(u)
    db.session.commit()
    cfg = _cfg()
    return LoginResponse(
        accessToken=_access_token(u), expiresIn=cfg.access_token_ttl, user=_core_user(u)
    ), refresh


def refresh(refresh_token: str | None) -> tuple[LoginResponse, str]:
    if not refresh_token:
        raise Unauthorized("Falta la sesión.", code="AUTH_REFRESH_INVALID")
    claims = _decode(refresh_token)
    if claims.get("typ") != "refresh":
        raise Unauthorized("Sesión inválida.", code="AUTH_REFRESH_INVALID")
    s = db.session.get(MockCoreSession, claims.get("sid"), with_for_update=True)
    if s is None or s.revoked_at is not None or s.expires_at <= now_utc():
        raise Unauthorized("La sesión fue cerrada o venció.", code="AUTH_REFRESH_INVALID")
    u = db.session.get(MockCoreUser, s.user_id)
    if u is None or u.status != "ACTIVE":
        raise Unauthorized("La cuenta no está activa.", code="AUTH_REFRESH_INVALID")
    s.revoked_at = now_utc()  # rotation: each refresh token works once
    new_refresh = _new_session(u)
    db.session.commit()
    cfg = _cfg()
    return LoginResponse(
        accessToken=_access_token(u), expiresIn=cfg.access_token_ttl, user=_core_user(u)
    ), new_refresh


def logout(refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        claims = _decode(refresh_token)
    except Unauthorized:
        return
    db.session.execute(
        update(MockCoreSession)
        .where(MockCoreSession.jti == claims.get("sid"), MockCoreSession.revoked_at.is_(None))
        .values(revoked_at=now_utc())
    )
    db.session.commit()


def me(principal: Principal) -> CoreUser:
    u = db.session.get(MockCoreUser, principal.user_id)
    if u is None:
        raise Unauthorized("Usuario inexistente.", code="AUTH_TOKEN_INVALID")
    return _core_user(u)


def service_token(client_id: str, client_secret: str) -> ServiceTokenResponse:
    allowed = dict(p.split(":", 1) for p in _cfg().mock_core_service_clients if ":" in p)
    expected = allowed.get(client_id)
    if expected is None or not hmac.compare_digest(expected.encode(), client_secret.encode()):
        raise Unauthorized("Credenciales de servicio inválidas.", code="AUTH_INVALID_CLIENT")
    module = client_id.removesuffix("-service")
    ttl = _cfg().access_token_ttl
    token = _sign(
        {
            "sub": client_id,
            "kind": "service",
            "service": module,
            "roles": [],
            "permissions": ["notifications:write", "events:publish"],
            "typ": "access",
        },
        ttl,
    )
    return ServiceTokenResponse(accessToken=token, expiresIn=ttl)


# ── wallet ──────────────────────────────────────────────────────────────────────────────
def _require_perm(principal: Principal, perm: str) -> None:
    if perm not in principal.permissions:
        raise Forbidden(f"Falta el permiso {perm}.", code="AUTH_FORBIDDEN")


def _balance(user_id: str) -> tuple[Decimal, datetime | None]:
    last = db.session.scalar(
        select(MockCoreWalletTx)
        .where(MockCoreWalletTx.user_id == user_id, MockCoreWalletTx.status == "POSTED")
        .order_by(MockCoreWalletTx.created_at.desc(), MockCoreWalletTx.id.desc())
        .limit(1)
    )
    return (last.balance_after, last.created_at) if last else (Decimal("0.00"), None)


def _tx_dto(t: MockCoreWalletTx) -> WalletTxDto:
    return WalletTxDto(
        transactionId=t.id,
        status=t.status,  # type: ignore[arg-type]
        type=t.type,  # type: ignore[arg-type]
        concept=t.concept,
        amount=_money(t.amount),
        currency=t.currency,
        balanceAfter=_money(t.balance_after),
        externalReference=t.external_reference,
        createdAt=_iso(t.created_at) or "",
    )


def _wallet_user(principal: Principal) -> MockCoreUser:
    u = db.session.get(MockCoreUser, principal.user_id)
    if u is None:
        raise NotFound("El usuario no tiene billetera.", code="WALLET_NOT_FOUND")
    return u


def wallet(principal: Principal) -> WalletDto:
    _require_perm(principal, "wallet:read:self")
    u = _wallet_user(principal)
    bal, updated = _balance(u.id)
    return WalletDto(
        walletId=str(uuid.uuid5(uuid.NAMESPACE_URL, f"wallet/{u.id}")),
        userId=u.id,
        balance=_money(bal),
        currency="ARS",
        updatedAt=_iso(updated or u.created_at) or "",
    )


def transactions(principal: Principal, limit: int) -> WalletTxPage:
    _require_perm(principal, "wallet:read:self")
    u = _wallet_user(principal)
    rows = db.session.scalars(
        select(MockCoreWalletTx)
        .where(MockCoreWalletTx.user_id == u.id)
        .order_by(MockCoreWalletTx.created_at.desc(), MockCoreWalletTx.id.desc())
        .limit(limit)
    ).all()
    return WalletTxPage(items=[_tx_dto(t) for t in rows], nextCursor=None)


def post_tx(
    user_id: str,
    *,
    type_: str,
    concept: str,
    amount: Decimal,
    source_module: str,
    external_reference: str,
    idempotency_key: str | None = None,
    request_hash: str | None = None,
    status: str = "POSTED",
) -> MockCoreWalletTx:
    """Append a movement. Serialised per user with a row lock on the user (no lost updates)."""
    db.session.execute(select(MockCoreUser.id).where(MockCoreUser.id == user_id).with_for_update())
    bal, _ = _balance(user_id)
    delta = amount if type_ == "CREDIT" else -amount
    new_bal = bal + delta if status == "POSTED" else bal
    if new_bal < 0:
        raise Unprocessable("Saldo insuficiente.", code="WALLET_INSUFFICIENT_FUNDS")
    t = MockCoreWalletTx(
        id=str(uuid.uuid4()),
        user_id=user_id,
        status=status,
        type=type_,
        concept=concept,
        amount=amount,
        currency="ARS",
        balance_after=new_bal,
        source_module=source_module,
        external_reference=external_reference,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        created_at=now_utc(),
    )
    db.session.add(t)
    return t


def top_up(principal: Principal, body: TopUpRequest, idempotency_key: str | None) -> tuple[WalletTxDto, int]:
    _require_perm(principal, "wallet:credit:self")
    try:
        key = str(uuid.UUID(idempotency_key or ""))
    except ValueError:
        raise BadRequest("Falta el header Idempotency-Key (UUID).", code="IDEMPOTENCY_KEY_REQUIRED") from None
    amount = Decimal(body.amount)
    if amount <= 0 or amount > Decimal("1000000"):
        raise BadRequest("El monto debe ser mayor a 0 y menor a 1.000.000.", code="WALLET_INVALID_AMOUNT")
    u = _wallet_user(principal)
    req_hash = hashlib.sha256(json.dumps(body.model_dump(), sort_keys=True).encode()).hexdigest()
    prev = db.session.scalar(
        select(MockCoreWalletTx).where(
            MockCoreWalletTx.user_id == u.id, MockCoreWalletTx.idempotency_key == key
        )
    )
    if prev is not None:
        if prev.request_hash != req_hash:
            raise Conflict("La Idempotency-Key ya se usó con otro contenido.", code="IDEMPOTENCY_CONFLICT")
        return _tx_dto(prev), 201
    if body.paymentMethodToken == "mock-rejected":
        raise Unprocessable("El medio de pago rechazó la carga.", code="WALLET_TOPUP_REJECTED")
    status = "PENDING" if body.paymentMethodToken == "mock-pending" else "POSTED"
    t = post_tx(
        u.id,
        type_="CREDIT",
        concept="TOP_UP",
        amount=amount,
        source_module="core",
        external_reference=f"top-up/{key}",
        idempotency_key=key,
        request_hash=req_hash,
        status=status,
    )
    try:
        db.session.commit()
    except IntegrityError:  # concurrent replay of the same key
        db.session.rollback()
        raise Conflict("La Idempotency-Key ya se usó.", code="IDEMPOTENCY_CONFLICT") from None
    return _tx_dto(t), 201


# ── notifications ───────────────────────────────────────────────────────────────────────
def _notif_dto(n: MockCoreNotification) -> NotificationDto:
    return NotificationDto(
        id=n.id,
        userId=n.user_id,
        type=n.type,
        title=n.title,
        message=n.message,
        actionUrl=n.action_url,
        sourceModule=n.source_module,
        sourceReference=n.source_reference,
        readAt=_iso(n.read_at),
        expiresAt=_iso(n.expires_at),
        createdAt=_iso(n.created_at) or "",
    )


def list_notifications(principal: Principal, read: bool | None, limit: int) -> NotificationPage:
    stmt = select(MockCoreNotification).where(MockCoreNotification.user_id == principal.user_id)
    if read is not None:
        stmt = stmt.where(MockCoreNotification.read.is_(read))
    rows = db.session.scalars(
        stmt.order_by(MockCoreNotification.created_at.desc(), MockCoreNotification.id).limit(limit)
    ).all()
    return NotificationPage(items=[_notif_dto(n) for n in rows], nextCursor=None)


def unread_count(principal: Principal) -> UnreadCount:
    n = db.session.scalar(
        select(func.count())
        .select_from(MockCoreNotification)
        .where(MockCoreNotification.user_id == principal.user_id, MockCoreNotification.read.is_(False))
    )
    return UnreadCount(count=int(n or 0))


def mark(principal: Principal, notification_id: str, read: bool) -> NotificationDto:
    n = db.session.get(MockCoreNotification, notification_id)
    if n is None or n.user_id != principal.user_id:
        raise NotFound("La notificación no existe.", code="NOTIFICATION_NOT_FOUND")
    n.read, n.read_at = read, (now_utc() if read else None)
    db.session.commit()
    return _notif_dto(n)


def read_all(principal: Principal) -> None:
    db.session.execute(
        update(MockCoreNotification)
        .where(MockCoreNotification.user_id == principal.user_id, MockCoreNotification.read.is_(False))
        .values(read=True, read_at=now_utc())
    )
    db.session.commit()


def create_notification(body: NotificationCreateRequest, *, commit: bool = True) -> NotificationDto:
    """POST /internal/v1/notifications. The tuple (user, type, sourceModule, sourceReference) is unique."""
    if db.session.get(MockCoreUser, body.userId) is None:
        raise NotFound("La identidad destino no existe.", code="IDENTITY_NOT_FOUND")
    dup = db.session.scalar(
        select(MockCoreNotification).where(
            MockCoreNotification.user_id == body.userId,
            MockCoreNotification.type == body.type,
            MockCoreNotification.source_module == body.sourceModule,
            MockCoreNotification.source_reference == body.sourceReference,
        )
    )
    if dup is not None:
        raise Conflict("La notificación ya existe.", code="NOTIFICATION_ALREADY_EXISTS")
    n = MockCoreNotification(
        id=str(uuid.uuid4()),
        user_id=body.userId,
        type=body.type,
        title=body.title,
        message=body.message,
        action_url=body.actionUrl,
        source_module=body.sourceModule,
        source_reference=body.sourceReference,
        expires_at=datetime.fromisoformat(body.expiresAt.replace("Z", "+00:00")) if body.expiresAt else None,
        created_at=now_utc(),
    )
    db.session.add(n)
    if commit:
        db.session.commit()
    return _notif_dto(n)
