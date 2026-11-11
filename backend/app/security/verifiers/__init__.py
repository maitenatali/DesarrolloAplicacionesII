from __future__ import annotations

from app.config import Settings

from .base import TokenVerifier
from .dev import DevVerifier
from .introspect import CoreIntrospectionVerifier
from .jwt import JwtVerifier


def build_verifier(cfg: Settings) -> TokenVerifier:
    if cfg.auth_verifier == "dev":
        return DevVerifier()
    if cfg.auth_verifier == "jwt":
        resolver = None
        if cfg.mock_core_enabled and not cfg.core_jwks_url:
            from app.mock_core.keys import public_key_for  # tokens signed by the local CORE simulator

            resolver = public_key_for
        return JwtVerifier(
            cfg.core_jwks_url,
            cfg.jwt_algorithms,
            cfg.jwt_issuer,
            cfg.jwt_audience,
            cfg.jwt_leeway_seconds,
            key_resolver=resolver,
        )
    return CoreIntrospectionVerifier(
        cfg.core_base_url,
        cfg.core_me_path,
        cache_ttl=cfg.token_cache_ttl,
        cache_max=cfg.token_cache_max_entries,
    )


__all__ = ["TokenVerifier", "DevVerifier", "CoreIntrospectionVerifier", "JwtVerifier", "build_verifier"]
