"""Encrypted secret storage — B-006 / D-129.

AES-256-GCM encryption at rest. Single owner for all secret reads/writes.
Key from VEZIR_SECRET_KEY env var (base64-encoded 32-byte).
Missing/invalid key: read-only mode.
"""
import base64
import json
import logging
import os
import tempfile

logger = logging.getLogger("mcc.secret_store")

LEGACY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config", "secrets.json"
)
ENCRYPTED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config", "secrets.enc.json"
)


class SecretStore:
    """Encrypted secret storage per D-129.

    - AES-256-GCM encryption
    - Key from VEZIR_SECRET_KEY env var (base64, 32 bytes)
    - Missing/invalid key: read-only mode
    - Read precedence: encrypted authoritative, legacy fallback only when encrypted absent
    - Atomic writes: temp + fsync + os.replace()
    """

    def __init__(self, key_env: str = "VEZIR_SECRET_KEY",
                 encrypted_path: str = None, legacy_path: str = None):
        self._encrypted_path = encrypted_path or ENCRYPTED_PATH
        self._legacy_path = legacy_path or LEGACY_PATH
        self._key: bytes | None = None
        self._read_only = False

        raw = os.environ.get(key_env, "")
        if not raw:
            logger.warning("VEZIR_SECRET_KEY not set — secret store in read-only mode")
            self._read_only = True
            return

        try:
            decoded = base64.b64decode(raw)
        except Exception:
            logger.warning("VEZIR_SECRET_KEY invalid base64 — secret store in read-only mode")
            self._read_only = True
            return

        if len(decoded) != 32:
            logger.warning("VEZIR_SECRET_KEY decoded length %d != 32 — read-only mode", len(decoded))
            self._read_only = True
            return

        self._key = decoded

    @property
    def read_only(self) -> bool:
        return self._read_only

    def read(self) -> dict:
        """Read secrets. Encrypted file is authoritative when present.

        D-129 precedence:
        - encrypted exists + key valid: decrypt and return
        - encrypted exists + key invalid/missing: raise (no silent fallback)
        - encrypted absent + legacy exists: read plaintext (fallback)
        - neither exists: return empty dict
        """
        if os.path.exists(self._encrypted_path):
            if self._key is None:
                raise SecretStoreError(
                    "Encrypted secrets exist but key is missing/invalid — cannot decrypt, no fallback"
                )
            return self._decrypt_file(self._encrypted_path)

        if os.path.exists(self._legacy_path):
            try:
                with open(self._legacy_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                raise SecretStoreError(f"Failed to read legacy secrets: {e}")

        return {}

    def write(self, secrets: dict) -> None:
        """Write secrets encrypted. Denied in read-only mode.

        D-129: atomic write (temp + fsync + os.replace), encrypted only.
        """
        if self._read_only:
            raise SecretStoreError("Secret store is in read-only mode — writes denied")

        if self._key is None:
            raise SecretStoreError("No encryption key available — writes denied")

        self._encrypt_file(self._encrypted_path, secrets)

    def _encrypt_file(self, path: str, data: dict) -> None:
        """Encrypt and write atomically per D-071."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        plaintext = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        envelope = {
            "version": 1,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(envelope, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _decrypt_file(self, path: str) -> dict:
        """Decrypt encrypted secrets file."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        with open(path, "r", encoding="utf-8") as f:
            envelope = json.load(f)

        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ciphertext"])

        aesgcm = AESGCM(self._key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise SecretStoreError(f"Decryption failed (wrong key or tampered data): {e}")

        return json.loads(plaintext.decode("utf-8"))


class SecretStoreError(Exception):
    """Secret store operation error."""
    pass
