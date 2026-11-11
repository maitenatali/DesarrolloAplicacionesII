"""RS256 signing key of the CORE simulator, persisted in the DB so every gunicorn worker shares it."""

from __future__ import annotations

import json
import threading
import uuid
from typing import Any

import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import MockCoreSigningKey

_lock = threading.Lock()
_cache: dict[str, Any] = {}


def _load_or_create() -> tuple[str, Any]:
    row = db.session.scalar(select(MockCoreSigningKey).order_by(MockCoreSigningKey.created_at).limit(1))
    if row is None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        ).decode()
        db.session.add(MockCoreSigningKey(kid=f"mock-core-{uuid.uuid4().hex[:8]}", private_pem=pem))
        try:
            db.session.commit()
        except IntegrityError:  # another worker won the race
            db.session.rollback()
        row = db.session.scalar(select(MockCoreSigningKey).order_by(MockCoreSigningKey.created_at).limit(1))
    assert row is not None
    return row.kid, serialization.load_pem_private_key(row.private_pem.encode(), password=None)


def signing_key() -> tuple[str, Any]:
    with _lock:
        if "kid" not in _cache:
            _cache["kid"], _cache["key"] = _load_or_create()
        return _cache["kid"], _cache["key"]


def reset_cache() -> None:
    with _lock:
        _cache.clear()


def jwks() -> dict[str, Any]:
    kid, key = signing_key()
    jwk = json.loads(pyjwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return {"keys": [jwk]}


def public_key_for(kid: str | None) -> Any | None:
    current_kid, key = signing_key()
    return key.public_key() if kid in (None, current_kid) else None
