"""JWT token management — S84 SSO/RBAC.

Issues and validates JWT session tokens after OAuth login.
Uses HS256 with a server-side secret.
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import jwt

logger = logging.getLogger("mcc.auth.jwt")

# ── Secret management ──────────────────────────────────────────────

_jwt_secret: str | None = None
_SECRET_FILE = Path(__file__).resolve().parent.parent.parent / "config" / ".jwt_secret"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 7


def _get_secret() -> str:
    """Get or generate JWT signing secret."""
    global _jwt_secret
    if _jwt_secret is not None:
        return _jwt_secret

    # Check environment first
    env_secret = os.environ.get("VEZIR_JWT_SECRET")
    if env_secret:
        _jwt_secret = env_secret
        return _jwt_secret

    # Check file
    if _SECRET_FILE.exists():
        _jwt_secret = _SECRET_FILE.read_text(encoding="utf-8").strip()
        return _jwt_secret

    # Generate and persist
    _jwt_secret = secrets.token_urlsafe(64)
    _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_FILE.write_text(_jwt_secret, encoding="utf-8")
    logger.info("Generated new JWT secret at %s", _SECRET_FILE)
    return _jwt_secret


# ── Token dataclass ────────────────────────────────────────────────

class TokenPayload:
    """Parsed JWT token payload."""

    def __init__(self, claims: dict[str, Any]) -> None:
        self.sub: str = claims.get("sub", "")
        self.username: str = claims.get("username", "")
        self.email: str = claims.get("email", "")
        self.role: str = claims.get("role", "viewer")
        self.provider: str = claims.get("provider", "")
        self.display_name: str = claims.get("display_name", "")
        self.token_type: str = claims.get("type", "access")
        self.exp: float = claims.get("exp", 0)
        self.iat: float = claims.get("iat", 0)
        self.jti: str = claims.get("jti", "")


# ── Revocation store (in-memory, survives process lifetime) ────────

_revoked_jtis: set[str] = set()


def revoke_token(jti: str) -> None:
    """Revoke a token by its JTI."""
    _revoked_jtis.add(jti)


def is_revoked(jti: str) -> bool:
    """Check if a token JTI is revoked."""
    return jti in _revoked_jtis


# ── Token creation ─────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    username: str,
    email: str,
    role: str,
    provider: str = "",
    display_name: str = "",
    expires_minutes: int | None = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    exp_minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    jti = secrets.token_urlsafe(16)

    payload = {
        "sub": user_id,
        "username": username,
        "email": email,
        "role": role,
        "provider": provider,
        "display_name": display_name,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=exp_minutes),
        "jti": jti,
    }
    return jwt.encode(payload, _get_secret(), algorithm=ALGORITHM)


def create_refresh_token(
    user_id: str,
    username: str,
    role: str,
    provider: str = "",
    expires_days: int | None = None,
) -> str:
    """Create a signed JWT refresh token."""
    now = datetime.now(timezone.utc)
    exp_days = expires_days or REFRESH_TOKEN_EXPIRE_DAYS
    jti = secrets.token_urlsafe(16)

    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "provider": provider,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=exp_days),
        "jti": jti,
    }
    return jwt.encode(payload, _get_secret(), algorithm=ALGORITHM)


# ── Token validation ───────────────────────────────────────────────

def decode_token(token: str) -> TokenPayload | None:
    """Decode and validate a JWT token.

    Returns TokenPayload if valid, None if invalid/expired/revoked.
    """
    try:
        claims = jwt.decode(token, _get_secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug("Invalid token: %s", e)
        return None

    payload = TokenPayload(claims)

    # Check revocation
    if payload.jti and is_revoked(payload.jti):
        logger.debug("Token revoked: %s", payload.jti)
        return None

    return payload


def refresh_access_token(refresh_token_str: str) -> tuple[str, str] | None:
    """Use a refresh token to get a new access + refresh token pair.

    Returns (new_access_token, new_refresh_token) or None if invalid.
    """
    payload = decode_token(refresh_token_str)
    if payload is None:
        return None
    if payload.token_type != "refresh":
        return None

    # Revoke the old refresh token (rotation)
    if payload.jti:
        revoke_token(payload.jti)

    # Issue new pair
    access = create_access_token(
        user_id=payload.sub,
        username=payload.username,
        email=payload.email,
        role=payload.role,
        provider=payload.provider,
        display_name=payload.display_name,
    )
    refresh = create_refresh_token(
        user_id=payload.sub,
        username=payload.username,
        role=payload.role,
        provider=payload.provider,
    )
    return access, refresh
