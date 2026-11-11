"""Tables of the LOCAL CORE simulator (app/mock_core). Not part of the teacher domain.

They exist only so the portal can run end-to-end without the real CORE module (login, wallet,
notifications). With MOCK_CORE_ENABLED=false nothing reads or writes them.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MockCoreSigningKey(Base):
    __tablename__ = "mock_core_signing_key"

    kid: Mapped[str] = mapped_column(String(64), primary_key=True)
    private_pem: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MockCoreUser(Base):
    __tablename__ = "mock_core_user"
    __table_args__ = (
        CheckConstraint(
            "status in ('INVITED','ACTIVE','SUSPENDED','DISABLED')", name="mock_core_user_status_ck"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # Backoffice UUID
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    roles: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    permissions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    career_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, server_default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MockCoreSession(Base):
    """One row per refresh token (rotated on every /auth/refresh, revoked on logout)."""

    __tablename__ = "mock_core_session"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MockCoreWalletTx(Base):
    __tablename__ = "mock_core_wallet_tx"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="mock_core_wallet_tx_idem_uk"),
        CheckConstraint("type in ('CREDIT','DEBIT','REVERSAL')", name="mock_core_wallet_tx_type_ck"),
        Index("mock_core_wallet_tx_user_idx", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    concept: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="ARS")
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    source_module: Mapped[str] = mapped_column(String(30), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MockCoreNotification(Base):
    __tablename__ = "mock_core_notification"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "type", "source_module", "source_reference", name="mock_core_notification_source_uk"
        ),
        Index("mock_core_notification_user_idx", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(300))
    source_module: Mapped[str] = mapped_column(String(30), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
