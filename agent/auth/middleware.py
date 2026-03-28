"""Auth middleware — D-117.

Enforces API key authentication on mutation endpoints.
GET requests pass through without auth (read-only public access).
"""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.keys import ApiKey, validate_key, is_auth_enabled

# Optional bearer — doesn't fail on missing header (GET endpoints don't need it)
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> ApiKey | None:
    """Extract and validate API key from Authorization header.

    Returns ApiKey if valid, None if no credentials provided.
    Raises 401 if credentials provided but invalid.
    """
    if credentials is None:
        return None

    key = validate_key(credentials.credentials)
    if key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key


async def require_operator(
    user: ApiKey | None = Depends(get_current_user),
) -> ApiKey | None:
    """Dependency that requires authenticated operator role.

    Use on all mutation endpoints (POST/PUT/DELETE).
    When auth is not configured (no keys in auth.json), allows all mutations.
    """
    if not is_auth_enabled():
        return None  # Auth not configured — allow all mutations

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Authorization: Bearer <api-key>",
        )
    if user.role != "operator":
        raise HTTPException(
            status_code=403,
            detail=f"Operator role required. Current role: {user.role}",
        )
    return user
