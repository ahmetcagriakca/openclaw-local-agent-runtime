"""Auth API — S84 OAuth2/OIDC endpoints.

Provides:
- GET  /api/v1/auth/config      — SSO configuration (public)
- GET  /api/v1/auth/login       — Initiate OAuth login (redirect URL)
- POST /api/v1/auth/callback    — OAuth callback (exchange code for JWT)
- POST /api/v1/auth/refresh     — Refresh JWT tokens
- POST /api/v1/auth/logout      — Revoke tokens
- GET  /api/v1/auth/me          — Current user info
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from auth.jwt_tokens import (
    create_access_token,
    create_refresh_token,
    decode_token,
    refresh_access_token,
    revoke_token,
)
from auth.oauth_provider import (
    OAuthError,
    generate_state,
    get_oauth_config,
    get_oauth_provider,
    is_sso_enabled,
    validate_state,
)
from auth.rbac import resolve_role

logger = logging.getLogger("mcc.api.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Request/Response schemas ───────────────────────────────────────

class AuthConfigResponse(BaseModel):
    sso_enabled: bool
    provider: str | None = None
    login_url: str | None = None


class LoginResponse(BaseModel):
    redirect_url: str


class CallbackRequest(BaseModel):
    code: str
    state: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserInfo


class UserInfo(BaseModel):
    user_id: str
    username: str
    email: str
    display_name: str
    role: str
    provider: str
    avatar_url: str = ""


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/config")
async def get_auth_config() -> AuthConfigResponse:
    """Get auth configuration — tells frontend if SSO is available."""
    if not is_sso_enabled():
        return AuthConfigResponse(sso_enabled=False)

    config = get_oauth_config()
    return AuthConfigResponse(
        sso_enabled=True,
        provider=config.provider if config else None,
        login_url="/api/v1/auth/login",
    )


@router.get("/login")
async def initiate_login() -> LoginResponse:
    """Initiate OAuth login — returns redirect URL."""
    provider = get_oauth_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="SSO not configured")

    state = generate_state()
    redirect_url = provider.get_authorize_url(state)
    return LoginResponse(redirect_url=redirect_url)


@router.post("/callback")
async def oauth_callback(body: CallbackRequest) -> TokenResponse:
    """Handle OAuth callback — exchange code for JWT tokens."""
    # Validate CSRF state
    if not validate_state(body.state):
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    provider = get_oauth_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="SSO not configured")

    try:
        # Exchange code for provider access token
        token_data = await provider.exchange_code(body.code)
        access_token_provider = token_data.get("access_token", "")
        if not access_token_provider:
            raise OAuthError("No access token in provider response")

        # Get user info from provider
        oauth_user = await provider.get_user_info(access_token_provider)

        # Resolve role from mappings
        role = resolve_role(
            provider=oauth_user.provider,
            username=oauth_user.username,
            email=oauth_user.email,
        )

        # Create Vezir JWT tokens
        from auth.jwt_tokens import ACCESS_TOKEN_EXPIRE_MINUTES

        vezir_access = create_access_token(
            user_id=oauth_user.provider_user_id,
            username=oauth_user.username,
            email=oauth_user.email,
            role=role,
            provider=oauth_user.provider,
            display_name=oauth_user.display_name,
        )
        vezir_refresh = create_refresh_token(
            user_id=oauth_user.provider_user_id,
            username=oauth_user.username,
            role=role,
            provider=oauth_user.provider,
        )

        user_info = UserInfo(
            user_id=oauth_user.provider_user_id,
            username=oauth_user.username,
            email=oauth_user.email,
            display_name=oauth_user.display_name,
            role=role,
            provider=oauth_user.provider,
            avatar_url=oauth_user.avatar_url,
        )

        logger.info(
            "OAuth login success: user=%s provider=%s role=%s",
            oauth_user.username, oauth_user.provider, role,
        )

        return TokenResponse(
            access_token=vezir_access,
            refresh_token=vezir_refresh,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info,
        )

    except OAuthError as e:
        logger.error("OAuth callback error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("OAuth callback unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/refresh")
async def refresh_tokens(body: RefreshRequest) -> TokenResponse:
    """Refresh JWT tokens using a refresh token."""
    result = refresh_access_token(body.refresh_token)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    new_access, new_refresh = result

    # Decode the new access token to get user info
    payload = decode_token(new_access)
    if payload is None:
        raise HTTPException(status_code=500, detail="Token creation failed")

    from auth.jwt_tokens import ACCESS_TOKEN_EXPIRE_MINUTES

    user_info = UserInfo(
        user_id=payload.sub,
        username=payload.username,
        email=payload.email,
        display_name=payload.display_name,
        role=payload.role,
        provider=payload.provider,
    )

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_info,
    )


@router.post("/logout")
async def logout(body: LogoutRequest) -> dict:
    """Logout — revoke refresh token."""
    if body.refresh_token:
        payload = decode_token(body.refresh_token)
        if payload and payload.jti:
            revoke_token(payload.jti)
            logger.info("Token revoked: user=%s", payload.username)

    return {"status": "logged_out"}


@router.get("/me")
async def get_current_user_info(request: Request) -> UserInfo:
    """Get current authenticated user info from JWT."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header[7:]

    # Try JWT first
    payload = decode_token(token)
    if payload and payload.token_type == "access":
        return UserInfo(
            user_id=payload.sub,
            username=payload.username,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            provider=payload.provider,
        )

    # Fall back to API key
    from auth.keys import validate_key
    api_key = validate_key(token)
    if api_key:
        return UserInfo(
            user_id=api_key.user_id or api_key.name,
            username=api_key.name,
            email="",
            display_name=api_key.name,
            role=api_key.role,
            provider="apikey",
        )

    raise HTTPException(status_code=401, detail="Invalid token")
