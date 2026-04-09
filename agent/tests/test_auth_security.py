"""Security-focused auth tests — Session 62 auth audit.

Covers gaps not addressed by existing auth test files:
- JWT token expiry enforcement
- Wrong-secret / wrong-algorithm token rejection
- Revoked access token rejection
- Token type confusion attacks (refresh used as access)
- RBAC permission matrix validation
- Role resolution with org matching
- Double-refresh replay attack prevention
- /me endpoint with revoked token
- require_admin denial for non-admin roles
- Logout idempotency
- API key expiration enforcement
"""
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("VEZIR_AUTH_BYPASS", "1")

from conftest import CSRF_ORIGIN

import api.server as srv
import auth.jwt_tokens as jwt_mod
import auth.keys as keys_mod
from auth.rbac import (
    ROLE_ADMIN,
    ROLE_HIERARCHY,
    ROLE_OPERATOR,
    ROLE_PERMISSIONS,
    ROLE_VIEWER,
    Permission,
    has_minimum_role,
    has_permission,
    resolve_role,
)

client = TestClient(srv.app)
ORIGIN = {"Origin": CSRF_ORIGIN}


@pytest.fixture(autouse=True)
def _reset():
    jwt_mod._jwt_secret = "test-security-secret-key-32b!"
    jwt_mod._revoked_jtis.clear()
    yield
    jwt_mod._jwt_secret = None
    jwt_mod._revoked_jtis.clear()


# ── JWT Token Security ───────────────────────────────────────────────


class TestJWTExpiry:
    """Verify expired tokens are rejected."""

    def test_expired_access_token_rejected(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="a@x.com",
            role="operator", expires_minutes=-1,
        )
        # decode_token should return None for expired tokens
        assert jwt_mod.decode_token(token) is None

    def test_expired_refresh_token_rejected(self):
        token = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
            expires_days=-1,
        )
        assert jwt_mod.decode_token(token) is None

    def test_expired_token_cannot_access_me(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="",
            role="operator", expires_minutes=-1,
        )
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401


class TestJWTSecretValidation:
    """Verify tokens signed with wrong secret are rejected."""

    def test_wrong_secret_rejected(self):
        # Craft a token with a different secret
        payload = {
            "sub": "u1", "username": "attacker", "email": "",
            "role": "admin", "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "jti": "fake-jti",
        }
        forged = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")
        assert jwt_mod.decode_token(forged) is None

    def test_wrong_algorithm_rejected(self):
        """Token signed with HS384 should be rejected (only HS256 accepted)."""
        payload = {
            "sub": "u1", "username": "attacker", "email": "",
            "role": "admin", "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "jti": "fake-jti",
        }
        forged = pyjwt.encode(
            payload, jwt_mod._get_secret(), algorithm="HS384",
        )
        assert jwt_mod.decode_token(forged) is None

    def test_unsigned_token_rejected(self):
        """Unsigned (alg=none) tokens must be rejected."""
        # PyJWT won't decode alg=none by default, but verify explicitly
        payload = {
            "sub": "u1", "username": "attacker", "email": "",
            "role": "admin", "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        # Manually craft an unsigned JWT
        import base64
        import json as json_mod
        header = base64.urlsafe_b64encode(
            json_mod.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(
            json_mod.dumps(payload, default=str).encode()
        ).rstrip(b"=").decode()
        unsigned = f"{header}.{body}."
        assert jwt_mod.decode_token(unsigned) is None


class TestJWTRevocation:
    """Verify token revocation works correctly."""

    def test_revoked_access_token_rejected(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="",
            role="operator",
        )
        payload = jwt_mod.decode_token(token)
        assert payload is not None

        # Revoke the token
        jwt_mod.revoke_token(payload.jti)
        assert jwt_mod.decode_token(token) is None

    def test_revoked_token_cannot_access_me(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="a@x.com",
            role="operator",
        )
        # Decode to get JTI, then revoke
        payload = jwt_mod.decode_token(token)
        jwt_mod.revoke_token(payload.jti)

        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 401

    def test_is_revoked_false_for_unknown_jti(self):
        assert jwt_mod.is_revoked("nonexistent-jti") is False

    def test_is_revoked_true_after_revoke(self):
        jwt_mod.revoke_token("test-jti-123")
        assert jwt_mod.is_revoked("test-jti-123") is True


class TestTokenTypeConfusion:
    """Verify refresh tokens cannot be used as access tokens."""

    def test_refresh_token_rejected_as_access(self):
        """Refresh token should not work for /me endpoint."""
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {refresh}",
        })
        assert resp.status_code == 401

    def test_access_token_rejected_for_refresh(self):
        """Access token should not work for token refresh."""
        access = jwt_mod.create_access_token(
            user_id="u1", username="alice", email="",
            role="operator",
        )
        result = jwt_mod.refresh_access_token(access)
        assert result is None

    def test_middleware_rejects_refresh_token(self):
        """get_current_user should reject refresh tokens (type != access)."""
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        with patch("auth.keys.is_auth_enabled", return_value=True):
            with patch("auth.keys.validate_key", return_value=None):
                resp = client.get("/api/v1/auth/me", headers={
                    "Authorization": f"Bearer {refresh}",
                })
                assert resp.status_code == 401


# ── Replay Attack Prevention ────────────────────────────────────────


class TestReplayAttack:
    """Verify refresh token rotation prevents replay attacks."""

    def test_double_refresh_blocked(self):
        """After refresh, old refresh token should be revoked."""
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        # First refresh should succeed
        result = jwt_mod.refresh_access_token(refresh)
        assert result is not None
        new_access, new_refresh = result

        # Second refresh with same token should fail (revoked)
        result2 = jwt_mod.refresh_access_token(refresh)
        assert result2 is None

    def test_refresh_chain_works(self):
        """New refresh token from rotation should work."""
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        result = jwt_mod.refresh_access_token(refresh)
        assert result is not None
        _, new_refresh = result

        # New refresh token should work
        result2 = jwt_mod.refresh_access_token(new_refresh)
        assert result2 is not None

    def test_double_refresh_via_api_blocked(self):
        """API-level double refresh prevention."""
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        resp1 = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh,
        }, headers=ORIGIN)
        assert resp1.status_code == 200

        resp2 = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh,
        }, headers=ORIGIN)
        assert resp2.status_code == 401


# ── RBAC Permission Matrix ──────────────────────────────────────────


class TestRBACPermissions:
    """Validate the full permission matrix."""

    def test_viewer_has_only_read_permissions(self):
        for perm in ROLE_PERMISSIONS[ROLE_VIEWER]:
            assert has_permission(ROLE_VIEWER, perm)
        # Viewer should NOT have mutation permissions
        assert not has_permission(ROLE_VIEWER, Permission.CREATE_MISSION)
        assert not has_permission(ROLE_VIEWER, Permission.MANAGE_PROJECTS)
        assert not has_permission(ROLE_VIEWER, Permission.MANAGE_USERS)

    def test_operator_has_mutation_but_not_admin(self):
        assert has_permission(ROLE_OPERATOR, Permission.CREATE_MISSION)
        assert has_permission(ROLE_OPERATOR, Permission.MANAGE_PROJECTS)
        assert has_permission(ROLE_OPERATOR, Permission.READ_MISSIONS)
        # Operator should NOT have admin permissions
        assert not has_permission(ROLE_OPERATOR, Permission.MANAGE_USERS)
        assert not has_permission(ROLE_OPERATOR, Permission.MANAGE_ROLES)
        assert not has_permission(ROLE_OPERATOR, Permission.MANAGE_SYSTEM)

    def test_admin_has_all_permissions(self):
        for perm in ROLE_PERMISSIONS[ROLE_ADMIN]:
            assert has_permission(ROLE_ADMIN, perm)
        assert has_permission(ROLE_ADMIN, Permission.MANAGE_USERS)
        assert has_permission(ROLE_ADMIN, Permission.MANAGE_BACKUP)

    def test_invalid_role_has_no_permissions(self):
        assert not has_permission("hacker", Permission.READ_MISSIONS)
        assert not has_permission("", Permission.READ_MISSIONS)

    def test_invalid_role_level_is_zero(self):
        assert ROLE_HIERARCHY.get("unknown", 0) == 0


class TestRoleHierarchy:
    """Validate role hierarchy comparisons."""

    def test_admin_meets_all(self):
        assert has_minimum_role(ROLE_ADMIN, ROLE_ADMIN)
        assert has_minimum_role(ROLE_ADMIN, ROLE_OPERATOR)
        assert has_minimum_role(ROLE_ADMIN, ROLE_VIEWER)

    def test_operator_meets_operator_and_viewer(self):
        assert has_minimum_role(ROLE_OPERATOR, ROLE_OPERATOR)
        assert has_minimum_role(ROLE_OPERATOR, ROLE_VIEWER)
        assert not has_minimum_role(ROLE_OPERATOR, ROLE_ADMIN)

    def test_viewer_meets_only_viewer(self):
        assert has_minimum_role(ROLE_VIEWER, ROLE_VIEWER)
        assert not has_minimum_role(ROLE_VIEWER, ROLE_OPERATOR)
        assert not has_minimum_role(ROLE_VIEWER, ROLE_ADMIN)

    def test_unknown_role_meets_nothing(self):
        assert not has_minimum_role("unknown", ROLE_VIEWER)
        assert not has_minimum_role("", ROLE_VIEWER)


class TestRoleResolution:
    """Validate resolve_role with various inputs."""

    def test_default_role_is_viewer(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VEZIR_DEFAULT_ROLE", None)
            from auth import rbac
            rbac._mappings_loaded = False
            rbac._role_mappings = []
            role = resolve_role("github", "unknown_user", "unknown@x.com")
            assert role == ROLE_VIEWER

    def test_default_role_from_env(self):
        with patch.dict(os.environ, {"VEZIR_DEFAULT_ROLE": "operator"}, clear=False):
            from auth import rbac
            rbac._mappings_loaded = False
            rbac._role_mappings = []
            role = resolve_role("github", "unknown_user", "unknown@x.com")
            assert role == "operator"

    def test_invalid_default_role_falls_to_viewer(self):
        with patch.dict(os.environ, {"VEZIR_DEFAULT_ROLE": "superadmin"}, clear=False):
            from auth import rbac
            rbac._mappings_loaded = False
            rbac._role_mappings = []
            role = resolve_role("github", "unknown_user", "unknown@x.com")
            assert role == ROLE_VIEWER

    def test_org_matching(self):
        from auth import rbac
        from auth.rbac import RoleMapping
        rbac._role_mappings = [
            RoleMapping(provider="github", match_field="org", match_value="acme-corp", role="admin"),
        ]
        rbac._mappings_loaded = True
        role = resolve_role("github", "user", "user@x.com", orgs=["acme-corp"])
        assert role == "admin"

    def test_org_no_match_falls_through(self):
        from auth import rbac
        from auth.rbac import RoleMapping
        rbac._role_mappings = [
            RoleMapping(provider="github", match_field="org", match_value="acme-corp", role="admin"),
        ]
        rbac._mappings_loaded = True
        os.environ.pop("VEZIR_DEFAULT_ROLE", None)
        role = resolve_role("github", "user", "user@x.com", orgs=["other-corp"])
        assert role == ROLE_VIEWER

    def test_wildcard_provider_matching(self):
        from auth import rbac
        from auth.rbac import RoleMapping
        rbac._role_mappings = [
            RoleMapping(provider="*", match_field="email", match_value="admin@x.com", role="admin"),
        ]
        rbac._mappings_loaded = True
        role = resolve_role("generic", "user", "admin@x.com")
        assert role == "admin"

    def test_provider_mismatch_skips_mapping(self):
        from auth import rbac
        from auth.rbac import RoleMapping
        rbac._role_mappings = [
            RoleMapping(provider="github", match_field="username", match_value="alice", role="admin"),
        ]
        rbac._mappings_loaded = True
        os.environ.pop("VEZIR_DEFAULT_ROLE", None)
        role = resolve_role("generic", "alice", "alice@x.com")
        assert role == ROLE_VIEWER


# ── Middleware Enforcement ──────────────────────────────────────────


class TestRequireAdmin:
    """Verify require_admin denies non-admin roles."""

    def test_viewer_denied_admin_endpoint(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="viewer", email="",
            role="viewer",
        )
        env = {k: v for k, v in os.environ.items() if k != "VEZIR_AUTH_BYPASS"}
        with patch.dict(os.environ, env, clear=True):
            with patch("auth.keys.validate_key", return_value=None):
                from fastapi import Depends, FastAPI
                from fastapi.testclient import TestClient as TC

                from auth.middleware import require_admin

                app = FastAPI()

                @app.get("/admin-test")
                async def admin_ep(user=Depends(require_admin)):
                    return {"ok": True}

                tc = TC(app)
                resp = tc.get("/admin-test", headers={
                    "Authorization": f"Bearer {token}",
                })
                assert resp.status_code == 403

    def test_operator_denied_admin_endpoint(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="operator", email="",
            role="operator",
        )
        env = {k: v for k, v in os.environ.items() if k != "VEZIR_AUTH_BYPASS"}
        with patch.dict(os.environ, env, clear=True):
            with patch("auth.keys.validate_key", return_value=None):
                from fastapi import Depends, FastAPI
                from fastapi.testclient import TestClient as TC

                from auth.middleware import require_admin

                app = FastAPI()

                @app.get("/admin-test")
                async def admin_ep(user=Depends(require_admin)):
                    return {"ok": True}

                tc = TC(app)
                resp = tc.get("/admin-test", headers={
                    "Authorization": f"Bearer {token}",
                })
                assert resp.status_code == 403

    def test_admin_passes_admin_endpoint(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="admin", email="",
            role="admin",
        )
        env = {k: v for k, v in os.environ.items() if k != "VEZIR_AUTH_BYPASS"}
        with patch.dict(os.environ, env, clear=True):
            with patch("auth.keys.validate_key", return_value=None):
                from fastapi import Depends, FastAPI
                from fastapi.testclient import TestClient as TC

                from auth.middleware import require_admin

                app = FastAPI()

                @app.get("/admin-test")
                async def admin_ep(user=Depends(require_admin)):
                    return {"ok": True}

                tc = TC(app)
                resp = tc.get("/admin-test", headers={
                    "Authorization": f"Bearer {token}",
                })
                assert resp.status_code == 200


class TestRequireOperator:
    """Verify require_operator enforcement edge cases."""

    def test_no_auth_header_returns_401(self):
        env = {k: v for k, v in os.environ.items() if k != "VEZIR_AUTH_BYPASS"}
        with patch.dict(os.environ, env, clear=True):
            from fastapi import Depends, FastAPI
            from fastapi.testclient import TestClient as TC

            from auth.middleware import require_operator

            app = FastAPI()

            @app.post("/mutate")
            async def mutate_ep(user=Depends(require_operator)):
                return {"ok": True}

            tc = TC(app)
            resp = tc.post("/mutate")
            assert resp.status_code == 401

    def test_viewer_returns_403(self):
        token = jwt_mod.create_access_token(
            user_id="u1", username="viewer", email="",
            role="viewer",
        )
        env = {k: v for k, v in os.environ.items() if k != "VEZIR_AUTH_BYPASS"}
        with patch.dict(os.environ, env, clear=True):
            with patch("auth.keys.validate_key", return_value=None):
                from fastapi import Depends, FastAPI
                from fastapi.testclient import TestClient as TC

                from auth.middleware import require_operator

                app = FastAPI()

                @app.post("/mutate")
                async def mutate_ep(user=Depends(require_operator)):
                    return {"ok": True}

                tc = TC(app)
                resp = tc.post("/mutate", headers={
                    "Authorization": f"Bearer {token}",
                })
                assert resp.status_code == 403


# ── Logout Idempotency ─────────────────────────────────────────────


class TestLogoutIdempotency:
    """Verify logout is safe to call multiple times."""

    def test_double_logout_succeeds(self):
        refresh = jwt_mod.create_refresh_token(
            user_id="u1", username="alice", role="operator",
        )
        # First logout
        resp1 = client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh,
        }, headers=ORIGIN)
        assert resp1.status_code == 200

        # Second logout with same token (already revoked, but should not error)
        resp2 = client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh,
        }, headers=ORIGIN)
        assert resp2.status_code == 200

    def test_logout_empty_body_succeeds(self):
        resp = client.post("/api/v1/auth/logout", json={}, headers=ORIGIN)
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged_out"


# ── API Key Expiration ──────────────────────────────────────────────


class TestApiKeyExpiration:
    """Verify expired API keys are rejected."""

    def test_expired_key_rejected(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        key = keys_mod.ApiKey(
            key="vz_expired", name="old", role="operator",
            created="2025-01-01", expires_at=past, user_id="old",
        )
        keys_mod._keys = {"vz_expired": key}
        keys_mod._loaded = True
        try:
            result = keys_mod.validate_key("vz_expired")
            assert result is None
        finally:
            keys_mod._keys = {}
            keys_mod._loaded = False

    def test_valid_key_accepted(self):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        key = keys_mod.ApiKey(
            key="vz_valid", name="current", role="operator",
            created="2025-01-01", expires_at=future, user_id="current",
        )
        keys_mod._keys = {"vz_valid": key}
        keys_mod._loaded = True
        try:
            result = keys_mod.validate_key("vz_valid")
            assert result is not None
            assert result.name == "current"
        finally:
            keys_mod._keys = {}
            keys_mod._loaded = False

    def test_no_expiry_key_accepted(self):
        key = keys_mod.ApiKey(
            key="vz_noexp", name="forever", role="operator",
            created="2025-01-01", user_id="forever",
        )
        keys_mod._keys = {"vz_noexp": key}
        keys_mod._loaded = True
        try:
            result = keys_mod.validate_key("vz_noexp")
            assert result is not None
        finally:
            keys_mod._keys = {}
            keys_mod._loaded = False

    def test_invalid_expiry_format_treated_as_no_expiry(self):
        key = keys_mod.ApiKey(
            key="vz_bad", name="bad_date", role="operator",
            created="2025-01-01", expires_at="not-a-date", user_id="bad",
        )
        keys_mod._keys = {"vz_bad": key}
        keys_mod._loaded = True
        try:
            result = keys_mod.validate_key("vz_bad")
            assert result is not None
        finally:
            keys_mod._keys = {}
            keys_mod._loaded = False


# ── Token Payload Integrity ─────────────────────────────────────────


class TestTokenPayload:
    """Verify token payload parsing and defaults."""

    def test_missing_claims_use_defaults(self):
        payload = jwt_mod.TokenPayload({})
        assert payload.sub == ""
        assert payload.username == ""
        assert payload.email == ""
        assert payload.role == "viewer"  # default role
        assert payload.token_type == "access"

    def test_all_claims_parsed(self):
        payload = jwt_mod.TokenPayload({
            "sub": "u1", "username": "alice", "email": "a@x.com",
            "role": "admin", "provider": "github", "display_name": "Alice",
            "type": "refresh", "exp": 9999999999, "iat": 1000000000,
            "jti": "jti-123",
        })
        assert payload.sub == "u1"
        assert payload.username == "alice"
        assert payload.role == "admin"
        assert payload.token_type == "refresh"
        assert payload.jti == "jti-123"
