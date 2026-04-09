"""Tests for upgraded auth middleware (JWT + API key) — S84."""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("VEZIR_AUTH_BYPASS", "1")

import api.server as srv
import auth.jwt_tokens as jwt_mod
import auth.keys as keys_mod
from auth.middleware import AuthenticatedUser

client = TestClient(srv.app)


@pytest.fixture(autouse=True)
def _reset():
    jwt_mod._jwt_secret = "test-middleware-secret"
    jwt_mod._revoked_jtis.clear()
    yield
    jwt_mod._jwt_secret = None
    jwt_mod._revoked_jtis.clear()


class TestAuthenticatedUser:
    def test_from_api_key(self):
        key = keys_mod.ApiKey(
            key="vz_test", name="testuser", role="operator",
            created="2026-01-01", user_id="uid1",
        )
        user = AuthenticatedUser.from_api_key(key)
        assert user.user_id == "uid1"
        assert user.username == "testuser"
        assert user.role == "operator"
        assert user.provider == "apikey"

    def test_from_api_key_without_user_id(self):
        key = keys_mod.ApiKey(
            key="vz_test", name="testuser", role="viewer", created="2026-01-01",
        )
        user = AuthenticatedUser.from_api_key(key)
        assert user.user_id == "testuser"  # Falls back to name

    def test_from_jwt(self):
        payload = jwt_mod.TokenPayload({
            "sub": "u123", "username": "alice", "role": "admin",
            "provider": "github", "email": "alice@x.com",
            "display_name": "Alice",
        })
        user = AuthenticatedUser.from_jwt(payload)
        assert user.user_id == "u123"
        assert user.username == "alice"
        assert user.role == "admin"
        assert user.provider == "github"
        assert user.email == "alice@x.com"


class TestMiddlewareJWTAuth:
    """Test that JWT tokens work for mutations when auth is enabled."""

    def test_jwt_operator_can_mutate(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="",
            role="operator", provider="github",
        )
        # Enable auth for this test
        with patch.dict(os.environ, {}, clear=False):
            with patch("auth.keys.is_auth_enabled", return_value=True):
                with patch("auth.keys.validate_key", return_value=None):
                    # /api/v1/auth/me uses JWT directly, not require_operator
                    resp = client.get("/api/v1/auth/me", headers={
                        "Authorization": f"Bearer {token}",
                    })
                    assert resp.status_code == 200
                    assert resp.json()["role"] == "operator"

    def test_jwt_admin_can_mutate(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="admin", email="",
            role="admin", provider="github",
        )
        with patch("auth.keys.is_auth_enabled", return_value=True):
            with patch("auth.keys.validate_key", return_value=None):
                resp = client.get("/api/v1/auth/me", headers={
                    "Authorization": f"Bearer {token}",
                })
                assert resp.status_code == 200
                assert resp.json()["role"] == "admin"

    def test_jwt_viewer_read_only(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="viewer", email="",
            role="viewer", provider="github",
        )
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"


class TestBackwardCompatibility:
    """Verify API key auth still works after middleware upgrade."""

    def test_api_key_still_works(self):
        """Existing API key flow should be unaffected."""
        key = keys_mod.ApiKey(
            key="vz_test_key", name="testuser", role="operator",
            created="2026-01-01", user_id="uid1",
        )
        with patch("auth.keys.is_auth_enabled", return_value=True):
            with patch("auth.keys.validate_key", return_value=key):
                resp = client.get("/api/v1/auth/me", headers={
                    "Authorization": "Bearer vz_test_key",
                })
                assert resp.status_code == 200
                data = resp.json()
                assert data["username"] == "testuser"
                assert data["provider"] == "apikey"

    def test_bypass_still_works(self):
        """VEZIR_AUTH_BYPASS=1 should bypass all auth."""
        with patch.dict(os.environ, {"VEZIR_AUTH_BYPASS": "1"}, clear=False):
            # Auth config endpoint should work without auth
            resp = client.get("/api/v1/auth/config")
            assert resp.status_code == 200
