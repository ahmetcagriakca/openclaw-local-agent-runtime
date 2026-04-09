"""Auth middleware — D-117 + Sprint 40 user isolation + S84 JWT/OAuth.

Enforces authentication on mutation endpoints.
Supports both API key (D-117) and JWT (S84 SSO) authentication.
GET requests pass through without auth (read-only public access).
Sprint 40: Extracts user_id for data isolation.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.keys import ApiKey, is_auth_enabled, validate_key
from auth.rbac import ROLE_ADMIN, ROLE_OPERATOR, has_minimum_role

# Optional bearer — doesn't fail on missing header (GET endpoints don't need it)
_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    """Unified user identity — works for both API key and JWT auth."""
    user_id: str
    username: str
    role: str  # "admin", "operator", "viewer"
    provider: str  # "apikey", "github", "generic", etc.
    email: str = ""
    display_name: str = ""

    @staticmethod
    def from_api_key(key: ApiKey) -> "AuthenticatedUser":
        return AuthenticatedUser(
            user_id=key.user_id or key.name,
            username=key.name,
            role=key.role,
            provider="apikey",
        )

    @staticmethod
    def from_jwt(payload: object) -> "AuthenticatedUser":
        return AuthenticatedUser(
            user_id=payload.sub,
            username=payload.username,
            role=payload.role,
            provider=payload.provider or "jwt",
            email=payload.email,
            display_name=payload.display_name,
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser | None:
    """Extract and validate credentials from Authorization header.

    Supports both API keys (vz_ prefix) and JWT tokens.
    Returns AuthenticatedUser if valid, None if no credentials provided.
    Raises 401 if credentials provided but invalid.
    When auth is bypassed (VEZIR_AUTH_BYPASS=1), skips validation.
    """
    if not is_auth_enabled():
        return None  # Auth bypassed — skip validation

    if credentials is None:
        return None

    token = credentials.credentials

    # Try API key first (fast path for existing integrations)
    api_key = validate_key(token)
    if api_key is not None:
        return AuthenticatedUser.from_api_key(api_key)

    # Try JWT token
    from auth.jwt_tokens import decode_token
    payload = decode_token(token)
    if payload is not None and payload.token_type == "access":
        return AuthenticatedUser.from_jwt(payload)

    raise HTTPException(status_code=401, detail="Invalid credentials")


async def require_operator(
    user: AuthenticatedUser | None = Depends(get_current_user),
) -> AuthenticatedUser | None:
    """Dependency that requires authenticated operator (or admin) role.

    Use on all mutation endpoints (POST/PUT/DELETE).
    When auth is not configured (no keys in auth.json), allows all mutations.
    """
    if not is_auth_enabled():
        import logging
        logging.getLogger("mcc.auth").warning(
            "Auth bypassed (VEZIR_AUTH_BYPASS=1). All mutations allowed without authentication.")
        return None  # Auth explicitly bypassed

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Authorization: Bearer <token>",
        )
    if not has_minimum_role(user.role, ROLE_OPERATOR):
        raise HTTPException(
            status_code=403,
            detail=f"Operator role required. Current role: {user.role}",
        )
    return user


async def require_admin(
    user: AuthenticatedUser | None = Depends(get_current_user),
) -> AuthenticatedUser | None:
    """Dependency that requires admin role.

    Use on admin-only endpoints (user management, system config).
    """
    if not is_auth_enabled():
        return None

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )
    if not has_minimum_role(user.role, ROLE_ADMIN):
        raise HTTPException(
            status_code=403,
            detail=f"Admin role required. Current role: {user.role}",
        )
    return user
