"""Tests for JWT token management — S84."""
import time

import pytest

import auth.jwt_tokens as jwt_mod


@pytest.fixture(autouse=True)
def _reset_jwt_state():
    """Reset JWT state between tests."""
    jwt_mod._jwt_secret = "test-secret-for-jwt-tests"
    jwt_mod._revoked_jtis.clear()
    yield
    jwt_mod._jwt_secret = None
    jwt_mod._revoked_jtis.clear()


class TestCreateAccessToken:
    def test_creates_valid_token(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="a@b.com",
            role="operator", provider="github",
        )
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_roundtrip(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="a@b.com",
            role="operator", provider="github", display_name="Alice",
        )
        payload = jwt_mod.decode_token(token)
        assert payload is not None
        assert payload.sub == "u1"
        assert payload.username == "alice"
        assert payload.email == "a@b.com"
        assert payload.role == "operator"
        assert payload.provider == "github"
        assert payload.display_name == "Alice"
        assert payload.token_type == "access"

    def test_custom_expiry(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="a@b.com",
            role="viewer", expires_minutes=1,
        )
        payload = jwt_mod.decode_token(token)
        assert payload is not None
        assert payload.role == "viewer"


class TestCreateRefreshToken:
    def test_creates_refresh_token(self):
        token = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        payload = jwt_mod.decode_token(token)
        assert payload is not None
        assert payload.token_type == "refresh"
        assert payload.sub == "u1"

    def test_refresh_token_different_from_access(self):
        access = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="", role="operator",
        )
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        assert access != refresh


class TestDecodeToken:
    def test_invalid_token_returns_none(self):
        assert jwt_mod.decode_token("garbage") is None

    def test_wrong_secret_returns_none(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="", role="viewer",
        )
        jwt_mod._jwt_secret = "different-secret"
        assert jwt_mod.decode_token(token) is None

    def test_expired_token_returns_none(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="", role="viewer",
            expires_minutes=-1,  # Already expired
        )
        assert jwt_mod.decode_token(token) is None


class TestTokenRevocation:
    def test_revoke_token(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="", role="operator",
        )
        payload = jwt_mod.decode_token(token)
        assert payload is not None

        jwt_mod.revoke_token(payload.jti)
        assert jwt_mod.decode_token(token) is None

    def test_is_revoked(self):
        assert not jwt_mod.is_revoked("unknown-jti")
        jwt_mod.revoke_token("test-jti")
        assert jwt_mod.is_revoked("test-jti")


class TestRefreshAccessToken:
    def test_refresh_returns_new_pair(self):
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator", provider="github",
        )
        result = jwt_mod.refresh_access_token(refresh)
        assert result is not None
        new_access, new_refresh = result
        assert isinstance(new_access, str)
        assert isinstance(new_refresh, str)

        # Old refresh should be revoked
        assert jwt_mod.refresh_access_token(refresh) is None

    def test_refresh_with_access_token_fails(self):
        access = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="", role="operator",
        )
        assert jwt_mod.refresh_access_token(access) is None

    def test_refresh_preserves_identity(self):
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="admin", provider="github",
        )
        result = jwt_mod.refresh_access_token(refresh)
        assert result is not None
        new_access, _ = result
        payload = jwt_mod.decode_token(new_access)
        assert payload is not None
        assert payload.sub == "u1"
        assert payload.username == "alice"
        assert payload.role == "admin"


class TestTokenPayload:
    def test_defaults(self):
        payload = jwt_mod.TokenPayload({})
        assert payload.sub == ""
        assert payload.username == ""
        assert payload.role == "viewer"
        assert payload.token_type == "access"

    def test_from_claims(self):
        payload = jwt_mod.TokenPayload({
            "sub": "123", "username": "bob", "role": "admin",
            "type": "refresh", "provider": "github",
        })
        assert payload.sub == "123"
        assert payload.username == "bob"
        assert payload.role == "admin"
        assert payload.token_type == "refresh"
        assert payload.provider == "github"
