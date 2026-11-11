from __future__ import annotations

from collections.abc import Callable
from typing import Any

import jwt as pyjwt
from jwt import PyJWKClient

from app.errors import ServiceUnavailable, Unauthorized
from app.security.principal import Principal, principal_from_claims

from .base import TokenVerifier

KeyResolver = Callable[[str | None], Any]  # kid -> public key (None if unknown)


class JwtVerifier(TokenVerifier):
    """CORE access tokens are RS256 JWTs; verify locally against the JWKS (no call to CORE per request).

    `key_resolver` replaces the remote JWKS when the local CORE simulator signs the tokens.
    """

    def __init__(
        self,
        jwks_url: str,
        algorithms: tuple[str, ...],
        issuer: str = "",
        audience: str = "",
        leeway: int = 30,
        key_resolver: KeyResolver | None = None,
    ):
        self._client = (
            PyJWKClient(jwks_url, cache_keys=True, timeout=5) if jwks_url and not key_resolver else None
        )
        self._resolver = key_resolver
        self._algorithms = list(algorithms)
        self._issuer = issuer or None
        self._audience = audience or None
        self._leeway = leeway

    def _key(self, token: str) -> Any:
        try:
            if self._resolver is not None:
                key = self._resolver(pyjwt.get_unverified_header(token).get("kid"))
                if key is None:
                    raise pyjwt.InvalidKeyError("unknown kid")
                return key
            assert self._client is not None
            return self._client.get_signing_key_from_jwt(token).key
        except pyjwt.PyJWKClientConnectionError as e:
            raise ServiceUnavailable("No se pudo validar la sesión.", code="AUTH_UNAVAILABLE") from e
        except pyjwt.PyJWTError as e:
            raise Unauthorized("Token inválido.", code="TOKEN_INVALID") from e

    def verify(self, token: str) -> Principal:
        key = self._key(token)
        try:
            claims = pyjwt.decode(
                token,
                key,
                algorithms=self._algorithms,
                issuer=self._issuer,
                audience=self._audience,
                leeway=self._leeway,
                options={"verify_aud": self._audience is not None, "verify_iss": self._issuer is not None},
            )
        except pyjwt.ExpiredSignatureError as e:
            raise Unauthorized("El token venció.", code="TOKEN_EXPIRED") from e
        except pyjwt.PyJWTError as e:
            raise Unauthorized("Token inválido.", code="TOKEN_INVALID") from e
        if claims.get("typ") == "refresh":
            raise Unauthorized("Token inválido.", code="TOKEN_INVALID")
        principal = principal_from_claims(claims)
        if not principal.user_id or principal.status != "ACTIVE":
            raise Unauthorized("Usuario inactivo.", code="TOKEN_INVALID")
        return principal
