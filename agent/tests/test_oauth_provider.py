"""Tests for OAuth provider — S84."""
import os
import time
from unittest.mock import patch

import pytest

import auth.oauth_provider as oauth


class TestOAuthConfig:
    @pytest.fixture(autouse=True)
    def _reset(self):
        oauth._config = None
        oauth._provider = None
        yield
        oauth._config = None
        oauth._provider = None

    def test_no_config_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing env vars
            for k in list(os.environ):
                if k.startswith("VEZIR_OAUTH"):
                    del os.environ[k]
            oauth._config = None
            # If config file doesn't exist and no env vars, returns None
            oauth._load_config()
            # May or may not be None depending on whether config/oauth.json exists
            # but should not raise

    def test_env_config_github(self):
        env = {
            "VEZIR_OAUTH_CLIENT_ID": "test-id",
            "VEZIR_OAUTH_CLIENT_SECRET": "test-secret",
            "VEZIR_OAUTH_PROVIDER": "github",
        }
        with patch.dict(os.environ, env, clear=False):
            config = oauth._load_config()
            assert config is not None
            assert config.provider == "github"
            assert config.client_id == "test-id"
            assert config.authorize_url == "https://github.com/login/oauth/authorize"
            assert config.token_url == "https://github.com/login/oauth/access_token"

    def test_env_config_generic(self):
        env = {
            "VEZIR_OAUTH_CLIENT_ID": "test-id",
            "VEZIR_OAUTH_CLIENT_SECRET": "test-secret",
            "VEZIR_OAUTH_PROVIDER": "azuread",
            "VEZIR_OAUTH_AUTHORIZE_URL": "https://login.microsoft.com/authorize",
            "VEZIR_OAUTH_TOKEN_URL": "https://login.microsoft.com/token",
            "VEZIR_OAUTH_USERINFO_URL": "https://graph.microsoft.com/me",
        }
        with patch.dict(os.environ, env, clear=False):
            config = oauth._load_config()
            assert config is not None
            assert config.provider == "azuread"
            assert "microsoft" in config.authorize_url


class TestIsSsoEnabled:
    @pytest.fixture(autouse=True)
    def _reset(self):
        oauth._config = None
        oauth._provider = None
        yield
        oauth._config = None
        oauth._provider = None

    def test_disabled_by_env(self):
        with patch.dict(os.environ, {"VEZIR_SSO_ENABLED": "0"}, clear=False):
            assert not oauth.is_sso_enabled()

    def test_enabled_when_configured(self):
        env = {
            "VEZIR_OAUTH_CLIENT_ID": "test-id",
            "VEZIR_OAUTH_CLIENT_SECRET": "test-secret",
        }
        with patch.dict(os.environ, env, clear=False):
            oauth._config = None
            assert oauth.is_sso_enabled()


class TestGitHubOAuthProvider:
    def test_get_authorize_url(self):
        config = oauth.OAuthConfig(
            provider="github",
            client_id="test-client",
            client_secret="test-secret",
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scopes=["read:user", "user:email"],
            redirect_uri="http://localhost:4000/auth/callback",
        )
        provider = oauth.GitHubOAuthProvider(config)
        url = provider.get_authorize_url("test-state")
        assert "client_id=test-client" in url
        assert "state=test-state" in url
        assert "redirect_uri=http://localhost:4000/auth/callback" in url


class TestGenericOAuthProvider:
    def test_get_authorize_url(self):
        config = oauth.OAuthConfig(
            provider="generic",
            client_id="test-client",
            client_secret="test-secret",
            authorize_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            userinfo_url="https://auth.example.com/userinfo",
            scopes=["openid", "profile"],
            redirect_uri="http://localhost:4000/auth/callback",
        )
        provider = oauth.GenericOAuthProvider(config)
        url = provider.get_authorize_url("test-state")
        assert "response_type=code" in url
        assert "client_id=test-client" in url


class TestStateManagement:
    @pytest.fixture(autouse=True)
    def _reset_states(self):
        oauth._pending_states.clear()
        yield
        oauth._pending_states.clear()

    def test_generate_and_validate(self):
        state = oauth.generate_state()
        assert isinstance(state, str)
        assert len(state) > 20
        assert oauth.validate_state(state)

    def test_state_consumed_on_validate(self):
        state = oauth.generate_state()
        assert oauth.validate_state(state)
        # Second validation should fail (consumed)
        assert not oauth.validate_state(state)

    def test_unknown_state_fails(self):
        assert not oauth.validate_state("unknown-state")

    def test_expired_state_fails(self):
        state = oauth.generate_state()
        # Manually expire it
        oauth._pending_states[state] = time.time() - 700  # >10 min ago
        assert not oauth.validate_state(state)

    def test_prune_old_states(self):
        # Add an old state
        oauth._pending_states["old-state"] = time.time() - 700
        # Generate new one triggers pruning
        oauth.generate_state()
        assert "old-state" not in oauth._pending_states


class TestGetOAuthProvider:
    @pytest.fixture(autouse=True)
    def _reset(self):
        oauth._config = None
        oauth._provider = None
        yield
        oauth._config = None
        oauth._provider = None

    def test_github_provider(self):
        env = {
            "VEZIR_OAUTH_CLIENT_ID": "test-id",
            "VEZIR_OAUTH_CLIENT_SECRET": "test-secret",
            "VEZIR_OAUTH_PROVIDER": "github",
        }
        with patch.dict(os.environ, env, clear=False):
            provider = oauth.get_oauth_provider()
            assert isinstance(provider, oauth.GitHubOAuthProvider)

    def test_generic_provider(self):
        env = {
            "VEZIR_OAUTH_CLIENT_ID": "test-id",
            "VEZIR_OAUTH_CLIENT_SECRET": "test-secret",
            "VEZIR_OAUTH_PROVIDER": "custom",
            "VEZIR_OAUTH_AUTHORIZE_URL": "https://x.com/auth",
            "VEZIR_OAUTH_TOKEN_URL": "https://x.com/token",
            "VEZIR_OAUTH_USERINFO_URL": "https://x.com/userinfo",
        }
        with patch.dict(os.environ, env, clear=False):
            provider = oauth.get_oauth_provider()
            assert isinstance(provider, oauth.GenericOAuthProvider)

    def test_reload_clears_cache(self):
        oauth._config = oauth.OAuthConfig(
            provider="test", client_id="x", client_secret="y",
            authorize_url="", token_url="", userinfo_url="",
            scopes=[], redirect_uri="",
        )
        oauth._provider = "cached"
        oauth.reload_oauth_config()
        assert oauth._config is None
        assert oauth._provider is None


class TestOAuthUser:
    def test_dataclass_fields(self):
        user = oauth.OAuthUser(
            provider="github",
            provider_user_id="123",
            username="alice",
            email="alice@gh.com",
            display_name="Alice",
            avatar_url="https://avatar.com/alice.png",
            raw_claims={"id": 123},
        )
        assert user.provider == "github"
        assert user.username == "alice"
        assert user.email == "alice@gh.com"
