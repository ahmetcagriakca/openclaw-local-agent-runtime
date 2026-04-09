"""Tests for Auth API endpoints — S84."""
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Set auth bypass for test isolation
os.environ.setdefault("VEZIR_AUTH_BYPASS", "1")

from conftest import CSRF_ORIGIN

import api.server as srv
import auth.jwt_tokens as jwt_mod
import auth.oauth_provider as oauth

client = TestClient(srv.app)

ORIGIN = {"Origin": CSRF_ORIGIN}


@pytest.fixture(autouse=True)
def _reset_state():
    jwt_mod._jwt_secret = "test-auth-api-secret"
    jwt_mod._revoked_jtis.clear()
    oauth._config = None
    oauth._provider = None
    oauth._pending_states.clear()
    yield
    jwt_mod._jwt_secret = None
    jwt_mod._revoked_jtis.clear()
    oauth._config = None
    oauth._provider = None
    oauth._pending_states.clear()


class TestAuthConfig:
    def test_sso_disabled(self):
        with patch.dict(os.environ, {"VEZIR_SSO_ENABLED": "0"}, clear=False):
            resp = client.get("/api/v1/auth/config")
            assert resp.status_code == 200
            data = resp.json()
            assert data["sso_enabled"] is False

    def test_sso_enabled(self):
        env = {
            "VEZIR_OAUTH_CLIENT_ID": "test-id",
            "VEZIR_OAUTH_CLIENT_SECRET": "test-secret",
        }
        with patch.dict(os.environ, env, clear=False):
            oauth._config = None
            resp = client.get("/api/v1/auth/config")
            assert resp.status_code == 200
            data = resp.json()
            assert data["sso_enabled"] is True
            assert data["provider"] == "github"


class TestLoginEndpoint:
    def test_login_returns_redirect_url(self):
        env = {
            "VEZIR_OAUTH_CLIENT_ID": "test-id",
            "VEZIR_OAUTH_CLIENT_SECRET": "test-secret",
            "VEZIR_OAUTH_PROVIDER": "github",
        }
        with patch.dict(os.environ, env, clear=False):
            oauth._config = None
            oauth._provider = None
            resp = client.get("/api/v1/auth/login")
            assert resp.status_code == 200
            data = resp.json()
            assert "redirect_url" in data
            assert "github.com" in data["redirect_url"]
            assert "client_id=test-id" in data["redirect_url"]

    def test_login_without_config_returns_503(self):
        with patch.dict(os.environ, {"VEZIR_SSO_ENABLED": "0"}, clear=False):
            oauth._config = None
            oauth._provider = None
            resp = client.get("/api/v1/auth/login")
            assert resp.status_code == 503


class TestCallbackEndpoint:
    def test_invalid_state_returns_400(self):
        resp = client.post("/api/v1/auth/callback", json={
            "code": "test-code",
            "state": "invalid-state",
        }, headers=ORIGIN)
        assert resp.status_code == 400

    def test_callback_success(self):
        env = {
            "VEZIR_OAUTH_CLIENT_ID": "test-id",
            "VEZIR_OAUTH_CLIENT_SECRET": "test-secret",
        }
        with patch.dict(os.environ, env, clear=False):
            oauth._config = None
            oauth._provider = None

            # Generate valid state
            state = oauth.generate_state()

            # Mock provider methods
            mock_provider = AsyncMock()
            mock_provider.exchange_code.return_value = {"access_token": "gh-token"}
            mock_provider.get_user_info.return_value = oauth.OAuthUser(
                provider="github",
                provider_user_id="12345",
                username="testuser",
                email="test@example.com",
                display_name="Test User",
                avatar_url="https://avatar.com/test.png",
                raw_claims={"id": 12345},
            )

            with patch("api.auth_api.get_oauth_provider", return_value=mock_provider):
                resp = client.post("/api/v1/auth/callback", json={
                    "code": "valid-code",
                    "state": state,
                }, headers=ORIGIN)
                assert resp.status_code == 200
                data = resp.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"
                assert data["user"]["username"] == "testuser"
                assert data["user"]["email"] == "test@example.com"
                assert data["user"]["provider"] == "github"


class TestRefreshEndpoint:
    def test_refresh_valid_token(self):
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh,
        }, headers=ORIGIN)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "alice"

    def test_refresh_invalid_token(self):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token",
        }, headers=ORIGIN)
        assert resp.status_code == 401

    def test_refresh_with_access_token_fails(self):
        access = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="", role="operator",
        )
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": access,
        }, headers=ORIGIN)
        assert resp.status_code == 401


class TestLogoutEndpoint:
    def test_logout_revokes_refresh_token(self):
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        resp = client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh,
        }, headers=ORIGIN)
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged_out"

        # Refresh token should now be revoked
        resp2 = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh,
        }, headers=ORIGIN)
        assert resp2.status_code == 401

    def test_logout_without_token(self):
        resp = client.post("/api/v1/auth/logout", json={}, headers=ORIGIN)
        assert resp.status_code == 200


class TestMeEndpoint:
    def test_me_with_jwt(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="alice@x.com",
            role="operator", provider="github", display_name="Alice",
        )
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice"
        assert data["email"] == "alice@x.com"
        assert data["role"] == "operator"
        assert data["provider"] == "github"

    def test_me_without_token(self):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self):
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid-token",
        })
        assert resp.status_code == 401
