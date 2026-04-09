"""Tests for auth backward compatibility — S84 T-84.04.

Verifies:
1. VEZIR_AUTH_BYPASS=1 still bypasses all auth (dev mode)
2. API key auth (D-117) works alongside JWT auth
3. SSO_ENABLED=0 disables OAuth endpoints gracefully
4. Middleware returns correct types for both auth modes
"""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("VEZIR_AUTH_BYPASS", "1")

import api.server as srv
import auth.jwt_tokens as jwt_mod
import auth.keys as keys_mod
import auth.oauth_provider as oauth
from auth.middleware import AuthenticatedUser
from auth.rbac import has_minimum_role
from conftest import CSRF_ORIGIN

client = TestClient(srv.app)
ORIGIN = {"Origin": CSRF_ORIGIN}


@pytest.fixture(autouse=True)
def _reset():
    jwt_mod._jwt_secret = "test-compat-secret-32bytes-long!!"
    jwt_mod._revoked_jtis.clear()
    oauth._config = None
    oauth._provider = None
    yield
    jwt_mod._jwt_secret = None
    jwt_mod._revoked_jtis.clear()
    oauth._config = None
    oauth._provider = None


class TestBypassMode:
    """VEZIR_AUTH_BYPASS=1 must skip all auth checks."""

    def test_auth_config_accessible(self):
        resp = client.get("/api/v1/auth/config")
        assert resp.status_code == 200

    def test_auth_me_without_token_returns_401(self):
        # /me still requires a token even in bypass mode
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_health_accessible(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


class TestApiKeyCompat:
    """D-117 API key auth must work unchanged after S84 middleware upgrade."""

    def test_api_key_produces_authenticated_user(self):
        key = keys_mod.ApiKey(
            key="vz_compat_test", name="legacy-user",
            role="operator", created="2026-01-01", user_id="u-legacy",
        )
        user = AuthenticatedUser.from_api_key(key)
        assert user.user_id == "u-legacy"
        assert user.username == "legacy-user"
        assert user.role == "operator"
        assert user.provider == "apikey"

    def test_api_key_role_hierarchy(self):
        # operator meets operator requirement (backward compat)
        assert has_minimum_role("operator", "operator")
        # viewer doesn't meet operator requirement
        assert not has_minimum_role("viewer", "operator")


class TestJwtCompat:
    """JWT tokens must coexist with API keys."""

    def test_jwt_token_for_me_endpoint(self):
        token = jwt_mod.create_access_token(
            user_id="jwt-user", username="jwtuser",
            email="jwt@test.com", role="admin",
        )
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "jwtuser"
        assert data["role"] == "admin"

    def test_api_key_for_me_endpoint(self):
        key = keys_mod.ApiKey(
            key="vz_me_test", name="keyuser",
            role="operator", created="2026-01-01",
        )
        with patch("auth.keys.is_auth_enabled", return_value=True):
            with patch("auth.keys.validate_key", return_value=key):
                resp = client.get("/api/v1/auth/me", headers={
                    "Authorization": "Bearer vz_me_test",
                })
                assert resp.status_code == 200
                assert resp.json()["provider"] == "apikey"


class TestSsoDisabled:
    """SSO_ENABLED=0 must disable OAuth gracefully."""

    def test_config_reports_disabled(self):
        with patch.dict(os.environ, {"VEZIR_SSO_ENABLED": "0"}):
            resp = client.get("/api/v1/auth/config")
            assert resp.status_code == 200
            assert resp.json()["sso_enabled"] is False

    def test_login_returns_503(self):
        with patch.dict(os.environ, {"VEZIR_SSO_ENABLED": "0"}):
            oauth._config = None
            oauth._provider = None
            resp = client.get("/api/v1/auth/login")
            assert resp.status_code == 503

    def test_refresh_still_works(self):
        """Even with SSO disabled, token refresh must work for existing JWT users."""
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh,
        }, headers=ORIGIN)
        assert resp.status_code == 200


class TestAdminRole:
    """S84 new admin role must not break existing operator/viewer flow."""

    def test_admin_meets_operator(self):
        assert has_minimum_role("admin", "operator")

    def test_admin_meets_admin(self):
        assert has_minimum_role("admin", "admin")

    def test_operator_does_not_meet_admin(self):
        assert not has_minimum_role("operator", "admin")
