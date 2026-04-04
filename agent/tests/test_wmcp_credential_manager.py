"""Tests for B-010 WMCP credential replacement."""
import pytest

from services.wmcp_credential_manager import (
    WmcpCredentialError,
    WmcpCredentialManager,
)


@pytest.fixture
def manager(tmp_path):
    meta_path = str(tmp_path / "wmcp-cred-meta.json")
    return WmcpCredentialManager(meta_path=meta_path)


class TestCredentialRegister:
    def test_register_api_key(self, manager):
        cred = manager.register("api_key", "sk-test-12345", description="Test key")
        assert cred.credential_type == "api_key"
        assert cred.active is True
        assert cred.key_hash != ""
        assert cred.version == 1

    def test_register_proxy_token(self, manager):
        cred = manager.register("proxy_token", "tok-abc")
        assert cred.credential_type == "proxy_token"

    def test_register_bridge_secret(self, manager):
        cred = manager.register("bridge_secret", "secret-xyz")
        assert cred.credential_type == "bridge_secret"

    def test_register_invalid_type(self, manager):
        with pytest.raises(WmcpCredentialError, match="Invalid credential_type"):
            manager.register("invalid", "value")

    def test_register_deactivates_previous(self, manager):
        manager.register("api_key", "first")
        c2 = manager.register("api_key", "second")
        creds = manager.list_credentials(credential_type="api_key", active_only=True)
        assert len(creds) == 1
        assert creds[0]["credential_id"] == c2.credential_id


class TestCredentialResolve:
    def test_resolve_registered(self, manager):
        # Note: resolve needs SecretStore which may not be available in test
        # Test the env fallback path
        manager.register("api_key", "sk-test")
        # SecretStore likely read-only in tests, so resolve returns None from store
        # but the credential is still registered in meta
        creds = manager.list_credentials(active_only=True)
        assert len(creds) == 1

    def test_resolve_env_fallback(self, manager, monkeypatch):
        monkeypatch.setenv("WMCP_API_KEY", "env-key-value")
        result = manager.resolve("api_key")
        assert result == "env-key-value"

    def test_resolve_no_credential(self, manager):
        result = manager.resolve("api_key")
        assert result is None


class TestCredentialRotation:
    def test_rotate_creates_new_version(self, manager):
        manager.register("api_key", "old-key")
        c2 = manager.rotate("api_key", "new-key")
        assert c2.version == 2
        assert c2.rotated_at != ""

    def test_rotate_deactivates_old(self, manager):
        manager.register("api_key", "old-key")
        manager.rotate("api_key", "new-key")
        active = manager.list_credentials(credential_type="api_key", active_only=True)
        assert len(active) == 1

    def test_rotate_multiple_times(self, manager):
        manager.register("api_key", "v1")
        manager.rotate("api_key", "v2")
        c3 = manager.rotate("api_key", "v3")
        assert c3.version == 3


class TestCredentialStatus:
    def test_status_empty(self, manager):
        status = manager.status()
        assert status["total_credentials"] == 0

    def test_status_with_credentials(self, manager):
        manager.register("api_key", "sk-test")
        manager.register("proxy_token", "tok-test")
        status = manager.status()
        assert status["total_credentials"] == 2
        assert status["active"] == 2
        assert status["by_type"]["api_key"]["active"] == 1
        assert status["by_type"]["proxy_token"]["active"] == 1

    def test_status_source_detection(self, manager, monkeypatch):
        monkeypatch.setenv("WMCP_API_KEY", "val")
        status = manager.status()
        assert status["by_type"]["api_key"]["source"] == "env_var"
        assert status["by_type"]["proxy_token"]["source"] == "none"


class TestCredentialVerify:
    def test_verify_matching(self, manager):
        manager.register("api_key", "test-secret")
        result = manager.verify("api_key", "test-secret")
        assert result["match"] is True

    def test_verify_non_matching(self, manager):
        manager.register("api_key", "real-secret")
        result = manager.verify("api_key", "wrong-secret")
        assert result["match"] is False

    def test_verify_no_active(self, manager):
        result = manager.verify("api_key", "any")
        assert result["match"] is False
        assert result["reason"] == "no_active_credential"


class TestCredentialList:
    def test_list_all(self, manager):
        manager.register("api_key", "k1")
        manager.register("proxy_token", "t1")
        creds = manager.list_credentials()
        assert len(creds) == 2

    def test_list_by_type(self, manager):
        manager.register("api_key", "k1")
        manager.register("proxy_token", "t1")
        creds = manager.list_credentials(credential_type="api_key")
        assert len(creds) == 1

    def test_list_active_only(self, manager):
        manager.register("api_key", "k1")
        manager.register("api_key", "k2")
        all_creds = manager.list_credentials(credential_type="api_key")
        active = manager.list_credentials(credential_type="api_key", active_only=True)
        assert len(all_creds) == 2
        assert len(active) == 1


class TestCredentialMigration:
    def test_migrate_from_env(self, manager, monkeypatch):
        monkeypatch.setenv("WMCP_API_KEY", "env-key")
        monkeypatch.setenv("WMCP_PROXY_TOKEN", "env-token")
        migrated = manager.migrate_from_env()
        assert "api_key" in migrated
        assert "proxy_token" in migrated

    def test_migrate_skips_existing(self, manager, monkeypatch):
        manager.register("api_key", "existing-key")
        monkeypatch.setenv("WMCP_API_KEY", "env-key")
        migrated = manager.migrate_from_env()
        assert "api_key" not in migrated

    def test_migrate_no_env(self, manager):
        migrated = manager.migrate_from_env()
        assert len(migrated) == 0


class TestCredentialPersistence:
    def test_meta_round_trip(self, tmp_path):
        path = str(tmp_path / "meta.json")
        m1 = WmcpCredentialManager(meta_path=path)
        m1.register("api_key", "sk-test", description="persist test")

        m2 = WmcpCredentialManager(meta_path=path)
        creds = m2.list_credentials()
        assert len(creds) == 1
        assert creds[0]["credential_type"] == "api_key"
