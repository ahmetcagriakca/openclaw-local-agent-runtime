"""Source User Identity Resolver — D-134 (Sprint 55).

3-tier precedence for mission sourceUserId:
  1. Authenticated session/token identity (highest)
  2. X-Source-User request header (trusted origins only, D-070)
  3. config.default_user fallback (lowest)

Fail-closed: if no source resolves → None (caller must reject with 401).
"""
import logging
import os

from fastapi import Request

logger = logging.getLogger("mcc.auth.source_user")

# Trusted origins per D-070 (localhost/internal only)
TRUSTED_ORIGINS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

# Header name for explicit source user
SOURCE_USER_HEADER = "X-Source-User"

# Config fallback
DEFAULT_USER_ENV = "VEZIR_DEFAULT_USER"


def _is_trusted_origin(request: Request) -> bool:
    """Check if request comes from a trusted origin per D-070."""
    if not request.client:
        return False
    host = request.client.host or ""
    return host in TRUSTED_ORIGINS


def resolve_source_user(
    request: Request,
    operator: dict | str | None = None,
) -> str | None:
    """Resolve source user identity per D-134 precedence.

    Args:
        request: FastAPI request object
        operator: Authenticated operator (from require_operator dependency)

    Returns:
        Resolved user ID, or None if fail-closed (no source resolved
        and no config fallback).
    """
    # Tier 1: Authenticated session/token identity
    if operator:
        if isinstance(operator, dict):
            user = operator.get("operator") or operator.get("user_id")
            if user:
                logger.debug("Source user from auth context: %s", user)
                return user
        elif isinstance(operator, str) and operator:
            logger.debug("Source user from auth string: %s", operator)
            return operator

    # Tier 2: X-Source-User header (trusted origins only)
    header_value = request.headers.get(SOURCE_USER_HEADER)
    if header_value:
        if _is_trusted_origin(request):
            logger.debug("Source user from header: %s", header_value)
            return header_value
        else:
            logger.warning(
                "X-Source-User header rejected: untrusted origin %s",
                request.client.host if request.client else "unknown",
            )
            # Fall through to tier 3, don't use untrusted header

    # Tier 3: Config fallback
    default_user = os.environ.get(DEFAULT_USER_ENV)
    if default_user:
        logger.debug("Source user from config fallback: %s", default_user)
        return default_user

    # Fail-closed: no source resolved
    logger.warning("Source user resolution failed: no source available")
    return None
