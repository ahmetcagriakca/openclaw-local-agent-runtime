"""OAuth2 provider abstraction — S84 SSO/RBAC.

Supports pluggable OAuth2 providers. Ships with GitHub OAuth.
Config from config/oauth.json or environment variables.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

logger = logging.getLogger("mcc.auth.oauth")


@dataclass
class OAuthConfig:
    """OAuth2 provider configuration."""
    provider: str  # "github", "generic"
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str]
    redirect_uri: str  # e.g. http://localhost:4000/auth/callback


@dataclass
class OAuthUser:
    """Normalized user identity from OAuth provider."""
    provider: str
    provider_user_id: str
    username: str
    email: str
    display_name: str
    avatar_url: str
    raw_claims: dict


class OAuthProvider(Protocol):
    """Protocol for OAuth2 providers."""

    def get_authorize_url(self, state: str) -> str: ...
    async def exchange_code(self, code: str) -> dict: ...
    async def get_user_info(self, access_token: str) -> OAuthUser: ...


class GitHubOAuthProvider:
    """GitHub OAuth2 provider."""

    def __init__(self, config: OAuthConfig) -> None:
        self.config = config

    def get_authorize_url(self, state: str) -> str:
        scopes = "+".join(self.config.scopes) if self.config.scopes else "read:user+user:email"
        return (
            f"{self.config.authorize_url}"
            f"?client_id={self.config.client_id}"
            f"&redirect_uri={self.config.redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
        )

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.config.token_url,
                json={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise OAuthError(f"Token exchange failed: {data['error_description']}")
            return data

    async def get_user_info(self, access_token: str) -> OAuthUser:
        """Fetch user profile from GitHub API."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.config.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

            # Fetch primary email if not in profile
            email = data.get("email", "")
            if not email:
                email_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                    timeout=10.0,
                )
                if email_resp.status_code == 200:
                    emails = email_resp.json()
                    primary = next((e for e in emails if e.get("primary")), None)
                    if primary:
                        email = primary["email"]

            return OAuthUser(
                provider="github",
                provider_user_id=str(data["id"]),
                username=data.get("login", ""),
                email=email,
                display_name=data.get("name", data.get("login", "")),
                avatar_url=data.get("avatar_url", ""),
                raw_claims=data,
            )


class GenericOAuthProvider:
    """Generic OAuth2/OIDC provider for custom configurations."""

    def __init__(self, config: OAuthConfig) -> None:
        self.config = config

    def get_authorize_url(self, state: str) -> str:
        scopes = "+".join(self.config.scopes)
        return (
            f"{self.config.authorize_url}"
            f"?client_id={self.config.client_id}"
            f"&redirect_uri={self.config.redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&response_type=code"
        )

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.config.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise OAuthError(f"Token exchange failed: {data.get('error_description', data['error'])}")
            return data

    async def get_user_info(self, access_token: str) -> OAuthUser:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.config.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

            return OAuthUser(
                provider=self.config.provider,
                provider_user_id=str(data.get("sub", data.get("id", ""))),
                username=data.get("preferred_username", data.get("login", "")),
                email=data.get("email", ""),
                display_name=data.get("name", ""),
                avatar_url=data.get("picture", data.get("avatar_url", "")),
                raw_claims=data,
            )


class OAuthError(Exception):
    """OAuth flow error."""


# ── State store for CSRF tokens ────────────────────────────────────

_pending_states: dict[str, float] = {}


def generate_state() -> str:
    """Generate a CSRF state token for OAuth flow."""
    import time
    state = secrets.token_urlsafe(32)
    _pending_states[state] = time.time()
    # Prune states older than 10 minutes
    cutoff = time.time() - 600
    stale = [k for k, v in _pending_states.items() if v < cutoff]
    for k in stale:
        del _pending_states[k]
    return state


def validate_state(state: str) -> bool:
    """Validate and consume a CSRF state token."""
    import time
    ts = _pending_states.pop(state, None)
    if ts is None:
        return False
    return (time.time() - ts) < 600  # 10 minute validity


# ── Config loader ──────────────────────────────────────────────────

_config: OAuthConfig | None = None
_provider: GitHubOAuthProvider | GenericOAuthProvider | None = None


def _load_config() -> OAuthConfig | None:
    """Load OAuth config from config/oauth.json or environment."""
    # Try environment variables first
    client_id = os.environ.get("VEZIR_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("VEZIR_OAUTH_CLIENT_SECRET", "")
    provider = os.environ.get("VEZIR_OAUTH_PROVIDER", "github")

    if client_id and client_secret:
        if provider == "github":
            return OAuthConfig(
                provider="github",
                client_id=client_id,
                client_secret=client_secret,
                authorize_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                userinfo_url="https://api.github.com/user",
                scopes=["read:user", "user:email"],
                redirect_uri=os.environ.get(
                    "VEZIR_OAUTH_REDIRECT_URI",
                    "http://localhost:4000/auth/callback",
                ),
            )
        return OAuthConfig(
            provider=provider,
            client_id=client_id,
            client_secret=client_secret,
            authorize_url=os.environ.get("VEZIR_OAUTH_AUTHORIZE_URL", ""),
            token_url=os.environ.get("VEZIR_OAUTH_TOKEN_URL", ""),
            userinfo_url=os.environ.get("VEZIR_OAUTH_USERINFO_URL", ""),
            scopes=os.environ.get("VEZIR_OAUTH_SCOPES", "openid profile email").split(),
            redirect_uri=os.environ.get(
                "VEZIR_OAUTH_REDIRECT_URI",
                "http://localhost:4000/auth/callback",
            ),
        )

    # Try config file
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "oauth.json"
    if not config_path.exists():
        return None

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return OAuthConfig(
            provider=data.get("provider", "github"),
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            authorize_url=data.get("authorize_url", "https://github.com/login/oauth/authorize"),
            token_url=data.get("token_url", "https://github.com/login/oauth/access_token"),
            userinfo_url=data.get("userinfo_url", "https://api.github.com/user"),
            scopes=data.get("scopes", ["read:user", "user:email"]),
            redirect_uri=data.get("redirect_uri", "http://localhost:4000/auth/callback"),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to load OAuth config: %s", e)
        return None


def get_oauth_config() -> OAuthConfig | None:
    """Get cached OAuth config."""
    global _config
    if _config is None:
        _config = _load_config()
    return _config


def get_oauth_provider() -> GitHubOAuthProvider | GenericOAuthProvider | None:
    """Get the configured OAuth provider instance."""
    global _provider
    if _provider is not None:
        return _provider

    config = get_oauth_config()
    if config is None:
        return None

    if config.provider == "github":
        _provider = GitHubOAuthProvider(config)
    else:
        _provider = GenericOAuthProvider(config)
    return _provider


def is_sso_enabled() -> bool:
    """Check if SSO/OAuth is configured and enabled."""
    if os.environ.get("VEZIR_SSO_ENABLED") == "0":
        return False
    return get_oauth_config() is not None


def reload_oauth_config() -> None:
    """Force reload OAuth config."""
    global _config, _provider
    _config = None
    _provider = None
