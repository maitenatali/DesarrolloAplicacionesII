"""Pydantic models of the CORE simulator. Field names copy CORE's OpenAPI (core-api /docs) exactly."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

DecimalStr = Annotated[str, Field(pattern=r"^\d{1,12}(\.\d{1,2})?$", examples=["5000.00"])]


class CoreModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(CoreModel):
    email: Annotated[str, Field(min_length=3, max_length=150)]
    password: Annotated[str, Field(min_length=1, max_length=200)]


class CoreUser(BaseModel):
    id: str
    email: str
    careerIds: list[str]
    roles: list[str]
    permissions: list[str]
    status: Literal["INVITED", "ACTIVE", "SUSPENDED", "DISABLED"]


class LoginResponse(BaseModel):
    accessToken: str
    expiresIn: int
    user: CoreUser


class Jwk(BaseModel):
    model_config = ConfigDict(extra="allow")
    kty: str
    kid: str
    use: str
    alg: str
    n: str
    e: str


class Jwks(BaseModel):
    keys: list[Jwk]


class ServiceTokenRequest(CoreModel):
    clientId: Annotated[str, Field(min_length=1, max_length=100)]
    clientSecret: Annotated[str, Field(min_length=1, max_length=200)]


class ServiceTokenResponse(BaseModel):
    accessToken: str
    expiresIn: int
    tokenType: str = "Bearer"


class WalletDto(BaseModel):
    walletId: str
    userId: str
    balance: str
    currency: str
    updatedAt: str


class WalletTxDto(BaseModel):
    transactionId: str
    status: Literal["PENDING", "POSTED", "REJECTED", "REVERSED"]
    type: Literal["CREDIT", "DEBIT", "REVERSAL"]
    concept: str
    amount: str
    currency: str
    balanceAfter: str
    externalReference: str
    originalTransactionId: str | None = None
    createdAt: str


class WalletTxPage(BaseModel):
    items: list[WalletTxDto]
    nextCursor: str | None = None


class LimitQuery(CoreModel):
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    cursor: str | None = None


class TopUpRequest(CoreModel):
    amount: DecimalStr
    currency: Literal["ARS"] = "ARS"
    paymentMethodToken: Literal["mock-approved", "mock-rejected", "mock-pending"] = "mock-approved"


class NotificationDto(BaseModel):
    id: str
    userId: str
    type: str
    title: str
    message: str
    actionUrl: str | None = None
    sourceModule: str
    sourceReference: str
    readAt: str | None = None
    expiresAt: str | None = None
    createdAt: str


class NotificationPage(BaseModel):
    items: list[NotificationDto]
    nextCursor: str | None = None


class NotificationQuery(CoreModel):
    read: bool | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50


class UnreadCount(BaseModel):
    count: int


class MarkReadRequest(CoreModel):
    read: bool


class NotificationCreateRequest(CoreModel):
    userId: Annotated[str, Field(min_length=1, max_length=36)]
    type: Annotated[str, Field(min_length=1, max_length=60)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    actionUrl: Annotated[str, Field(max_length=300)] | None = None
    sourceModule: Annotated[str, Field(min_length=1, max_length=30)]
    sourceReference: Annotated[str, Field(min_length=1, max_length=200)]
    expiresAt: str | None = None


class Empty(RootModel[dict]):
    pass
