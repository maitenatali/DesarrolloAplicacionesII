from __future__ import annotations

import jwt as pyjwt
from jwt import PyJWKClient

from app.errors import ServiceUnavailable, Unauthorized
from app.security.principal import Principal, principal_from_claims

from .base import TokenVerifier


class JwtVerifier(TokenVerifier):
    """Local signature verification via JWKS (AUTH_VERIFIER=jwt, FUTURE). TODO(CORE): alg/iss/aud/claims [OPEN]."""

    def __init__(
        self,
        jwks_url: str,
        algorithms: tuple[str, ...],
        issuer: str = "",
        audience: str = "",
        leeway: int = 30,
    ):
        self._client = PyJWKClient(jwks_url, cache_keys=True)
        self._algorithms = list(algorithms)
        self._issuer = issuer or None
        self._audience = audience or None
        self._leeway = leeway

    def verify(self, token: str) -> Principal:
        try:
            key = self._client.get_signing_key_from_jwt(token).key
        except pyjwt.PyJWKClientConnectionError as e:
            raise ServiceUnavailable("No se pudo validar la sesión.", code="AUTH_UNAVAILABLE") from e
        except pyjwt.PyJWTError as e:
            raise Unauthorized("Token inválido.", code="TOKEN_INVALID") from e
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
        return principal_from_claims(claims)
