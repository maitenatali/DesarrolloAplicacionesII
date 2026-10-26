from __future__ import annotations

from abc import ABC, abstractmethod

from app.security.principal import Principal


class TokenVerifier(ABC):
    @abstractmethod
    def verify(self, token: str) -> Principal:
        """Raises Unauthorized (TOKEN_INVALID/TOKEN_EXPIRED) or ServiceUnavailable (AUTH_UNAVAILABLE)."""
