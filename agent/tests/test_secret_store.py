"""D-129 / B-006: Encrypted secret storage tests."""
import base64
import json
import os
import pytest
from services.secret_store import SecretStore, SecretStoreError


def _make_key() -> str:
    """Generate a valid base64-encoded 32-byte key."""
    return base64.b64encode(os.urandom(32)).decode("ascii")


@pytest.fixture
def store_env(tmp_path, monkeypatch):
    """Set up a SecretStore with valid key and temp paths."""
    key = _make_key()
    monkeypatch.setenv("VEZIR_SECRET_KEY", key)
    encrypted = tmp_path / "secrets.enc.json"
    legacy = tmp_path / "secrets.json"
    return {
        "key": key,
        "encrypted_path": str(encrypted),
        "legacy_path": str(legacy),
    }


def _make_store(env):
    return SecretStore(
        encrypted_path=env["encrypted_path"],
        legacy_path=env["legacy_path"],
    )


class TestSecretStoreWrite:
    """D-129: Encrypted write tests."""

    def test_secret_store_write_creates_encrypted_file(self, store_env):
        store = _make_store(store_env)
        store.write({"api_key": "test123"})
        assert os.path.exists(store_env["encrypted_path"])
        # Must NOT write to legacy path
        assert not os.path.exists(store_env["legacy_path"])

    def test_secret_store_write_encrypted_format(self, store_env):
        store = _make_store(store_env)
        store.write({"api_key": "test123"})
        with open(store_env["encrypted_path"]) as f:
            envelope = json.load(f)
        assert envelope["version"] == 1
        assert "nonce" in envelope
        assert "ciphertext" in envelope

    def test_secret_store_roundtrip(self, store_env):
        store = _make_store(store_env)
        secrets = {"api_key": "abc", "token": "xyz"}
        store.write(secrets)
        result = store.read()
        assert result == secrets


class TestSecretStoreRead:
    """D-129: Read precedence tests."""

    def test_secret_store_read_encrypted_authoritative(self, store_env):
        store = _make_store(store_env)
        store.write({"source": "encrypted"})
        # Also create legacy with different data
        with open(store_env["legacy_path"], "w") as f:
            json.dump({"source": "legacy"}, f)
        result = store.read()
        assert result["source"] == "encrypted"

    def test_secret_store_read_legacy_fallback_when_no_encrypted(self, store_env):
        store = _make_store(store_env)
        with open(store_env["legacy_path"], "w") as f:
            json.dump({"source": "legacy"}, f)
        result = store.read()
        assert result["source"] == "legacy"

    def test_secret_store_read_empty_when_no_files(self, store_env):
        store = _make_store(store_env)
        result = store.read()
        assert result == {}


class TestSecretStoreMissingKey:
    """D-129: Missing VEZIR_SECRET_KEY behavior."""

    def test_secret_store_missing_key_is_read_only(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VEZIR_SECRET_KEY", raising=False)
        store = SecretStore(
            encrypted_path=str(tmp_path / "enc.json"),
            legacy_path=str(tmp_path / "legacy.json"),
        )
        assert store.read_only is True

    def test_secret_store_missing_key_write_denied(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VEZIR_SECRET_KEY", raising=False)
        store = SecretStore(
            encrypted_path=str(tmp_path / "enc.json"),
            legacy_path=str(tmp_path / "legacy.json"),
        )
        with pytest.raises(SecretStoreError, match="read-only"):
            store.write({"test": "value"})

    def test_secret_store_missing_key_can_read_legacy(self, tmp_path, monkeypatch):
        monkeypatch.delenv("VEZIR_SECRET_KEY", raising=False)
        legacy = tmp_path / "legacy.json"
        legacy.write_text(json.dumps({"key": "legacy_value"}))
        store = SecretStore(
            encrypted_path=str(tmp_path / "enc.json"),
            legacy_path=str(legacy),
        )
        result = store.read()
        assert result["key"] == "legacy_value"

    def test_secret_store_missing_key_encrypted_exists_no_fallback(self, tmp_path, monkeypatch):
        """D-129: If encrypted file exists but key missing, do NOT fall back to plaintext."""
        monkeypatch.delenv("VEZIR_SECRET_KEY", raising=False)
        enc = tmp_path / "enc.json"
        enc.write_text('{"version":1,"nonce":"x","ciphertext":"y"}')
        legacy = tmp_path / "legacy.json"
        legacy.write_text(json.dumps({"key": "should_not_read"}))
        store = SecretStore(
            encrypted_path=str(enc),
            legacy_path=str(legacy),
        )
        with pytest.raises(SecretStoreError, match="missing/invalid"):
            store.read()


class TestSecretStoreInvalidKey:
    """D-129: Invalid key behavior."""

    def test_secret_store_invalid_base64_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VEZIR_SECRET_KEY", "not-valid-base64!!!")
        store = SecretStore(
            encrypted_path=str(tmp_path / "enc.json"),
            legacy_path=str(tmp_path / "legacy.json"),
        )
        assert store.read_only is True

    def test_secret_store_wrong_length_key(self, tmp_path, monkeypatch):
        short_key = base64.b64encode(b"tooshort").decode("ascii")
        monkeypatch.setenv("VEZIR_SECRET_KEY", short_key)
        store = SecretStore(
            encrypted_path=str(tmp_path / "enc.json"),
            legacy_path=str(tmp_path / "legacy.json"),
        )
        assert store.read_only is True

    def test_secret_store_invalid_key_write_denied(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VEZIR_SECRET_KEY", "not-valid-base64!!!")
        store = SecretStore(
            encrypted_path=str(tmp_path / "enc.json"),
            legacy_path=str(tmp_path / "legacy.json"),
        )
        with pytest.raises(SecretStoreError, match="read-only"):
            store.write({"test": "value"})
