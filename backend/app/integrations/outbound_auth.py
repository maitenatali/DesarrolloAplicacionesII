"""How WE authenticate to other modules (design §9.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .token_provider import TokenProvider


class OutboundAuth(ABC):
    @abstractmethod
    def headers(self) -> dict[str, str]: ...

    def on_unauthorized(self) -> None:  # pragma: no cover - default no-op
        return None


class StaticBearer(OutboundAuth):
    def __init__(self, token: str):
        self._token = token

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}


class ServiceTokenAuth(OutboundAuth):
    def __init__(self, provider: TokenProvider):
        self._provider = provider

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._provider.get_token()}"}

    def on_unauthorized(self) -> None:
        self._provider.invalidate()


class NoAuth(OutboundAuth):
    def headers(self) -> dict[str, str]:
        return {}
