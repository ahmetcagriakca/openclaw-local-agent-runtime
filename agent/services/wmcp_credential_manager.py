"""WMCP credential manager — B-010.

Manages WMCP (Windows MCP Proxy) credentials through the SecretStore.
Replaces environment-variable-based credential passing with secure
encrypted storage and rotation-compatible lifecycle management.
"""
import hashlib
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.wmcp_cred")

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WMCP_CRED_META_PATH = str(_ROOT / "config" / "wmcp-credentials-meta.json")

# Credential types managed for WMCP
CREDENTIAL_TYPES = ("api_key", "proxy_token", "bridge_secret")


@dataclass
class WmcpCredential:
    """Single WMCP credential entry."""
    credential_id: str
    credential_type: str  # api_key | proxy_token | bridge_secret
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rotated_at: str = ""
    expires_at: str = ""
    version: int = 1
    key_hash: str = ""  # SHA-256 truncated hash for verification
    active: bool = True


class WmcpCredentialManager:
    """Manages WMCP credentials via SecretStore integration.

    Features:
    - Credential CRUD backed by SecretStore (encrypted at rest)
    - Rotation-compatible lifecycle (version tracking, hash verification)
    - Runtime credential resolution without env vars
    - Backward-compatible migration from env-var-based credentials
    """

    STORE_KEY = "wmcp_credentials"

    def __init__(self, meta_path: str = None):
        self._meta_path = meta_path or WMCP_CRED_META_PATH
        self._credentials: dict[str, WmcpCredential] = {}
        self._lock = threading.Lock()
        self._load_meta()

    def _load_meta(self) -> None:
        """Load credential metadata (not secrets — those stay in SecretStore)."""
        if os.path.exists(self._meta_path):
            try:
                import json
                with open(self._meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for raw in data.get("credentials", []):
                    cred = WmcpCredential(**raw)
                    self._credentials[cred.credential_id] = cred
                logger.info("WmcpCredentialManager loaded %d credential entries", len(self._credentials))
            except Exception as e:
                logger.warning("WmcpCredentialManager meta load failed: %s", e)

    def _save_meta(self) -> None:
        """Save credential metadata atomically."""
        try:
            data = {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "credentials": [asdict(c) for c in self._credentials.values()],
            }
            atomic_write_json(self._meta_path, data)
        except Exception as e:
            logger.error("WmcpCredentialManager meta save failed: %s", e)

    def register(self, credential_type: str, secret_value: str,
                 description: str = "", expires_at: str = "") -> WmcpCredential:
        """Register a new WMCP credential.

        Stores the secret value in SecretStore and metadata locally.
        """
        if credential_type not in CREDENTIAL_TYPES:
            raise WmcpCredentialError(
                f"Invalid credential_type: {credential_type}. "
                f"Must be one of: {', '.join(CREDENTIAL_TYPES)}"
            )

        cred_id = f"wmcp_{credential_type}_{hashlib.sha256(secret_value.encode()).hexdigest()[:8]}"
        key_hash = hashlib.sha256(secret_value.encode()).hexdigest()[:16]

        cred = WmcpCredential(
            credential_id=cred_id,
            credential_type=credential_type,
            description=description,
            expires_at=expires_at,
            key_hash=key_hash,
        )

        with self._lock:
            # Deactivate existing credentials of same type
            for existing in self._credentials.values():
                if existing.credential_type == credential_type and existing.active:
                    existing.active = False

            self._credentials[cred_id] = cred
            self._save_meta()

        # Store actual secret value
        self._store_secret(cred_id, secret_value)

        logger.info("WMCP credential registered: %s (type=%s)", cred_id, credential_type)
        return cred

    def resolve(self, credential_type: str) -> Optional[str]:
        """Resolve the active credential value for a given type.

        Priority: SecretStore > environment variable fallback.
        """
        with self._lock:
            active = [
                c for c in self._credentials.values()
                if c.credential_type == credential_type and c.active
            ]

        if active:
            active.sort(key=lambda c: c.version, reverse=True)
            secret = self._read_secret(active[0].credential_id)
            if secret:
                return secret

        # Fallback to env var for backward compatibility
        env_map = {
            "api_key": "WMCP_API_KEY",
            "proxy_token": "WMCP_PROXY_TOKEN",
            "bridge_secret": "OC_BRIDGE_SECRET",
        }
        env_key = env_map.get(credential_type, "")
        env_val = os.environ.get(env_key, "")
        if env_val:
            logger.info("WMCP credential resolved from env var: %s", env_key)
            return env_val

        return None

    def rotate(self, credential_type: str, new_secret: str,
               expires_at: str = "") -> WmcpCredential:
        """Rotate a credential: deactivate old, register new with bumped version.

        Returns the newly created credential.
        """
        with self._lock:
            max_version = max((c.version for c in self._credentials.values()
                               if c.credential_type == credential_type), default=0)

        new_cred = self.register(
            credential_type=credential_type,
            secret_value=new_secret,
            description=f"Rotated from v{max_version}",
            expires_at=expires_at,
        )

        with self._lock:
            new_cred.version = max_version + 1
            new_cred.rotated_at = datetime.now(timezone.utc).isoformat()
            self._save_meta()

        logger.info("WMCP credential rotated: %s → v%d", credential_type, new_cred.version)
        return new_cred

    def status(self) -> dict:
        """Return credential status summary."""
        with self._lock:
            creds = list(self._credentials.values())

        by_type = {}
        for ct in CREDENTIAL_TYPES:
            type_creds = [c for c in creds if c.credential_type == ct]
            active = [c for c in type_creds if c.active]
            by_type[ct] = {
                "total": len(type_creds),
                "active": len(active),
                "latest_version": max((c.version for c in type_creds), default=0),
                "source": "secret_store" if active else self._check_env_source(ct),
            }

        return {
            "total_credentials": len(creds),
            "active": sum(1 for c in creds if c.active),
            "by_type": by_type,
        }

    def list_credentials(self, credential_type: str = None,
                         active_only: bool = False) -> list[dict]:
        """List credentials (metadata only, no secrets)."""
        with self._lock:
            items = list(self._credentials.values())

        if credential_type:
            items = [c for c in items if c.credential_type == credential_type]
        if active_only:
            items = [c for c in items if c.active]

        return [asdict(c) for c in items]

    def verify(self, credential_type: str, test_value: str) -> dict:
        """Verify if a test value matches the active credential hash."""
        test_hash = hashlib.sha256(test_value.encode()).hexdigest()[:16]

        with self._lock:
            active = [
                c for c in self._credentials.values()
                if c.credential_type == credential_type and c.active
            ]

        if not active:
            return {"match": False, "reason": "no_active_credential"}

        current = active[0]
        matches = current.key_hash == test_hash
        return {
            "match": matches,
            "credential_id": current.credential_id,
            "version": current.version,
        }

    def migrate_from_env(self) -> list[str]:
        """Migrate credentials from environment variables to SecretStore.

        Returns list of migrated credential types.
        """
        env_map = {
            "api_key": "WMCP_API_KEY",
            "proxy_token": "WMCP_PROXY_TOKEN",
            "bridge_secret": "OC_BRIDGE_SECRET",
        }

        migrated = []
        for ctype, env_key in env_map.items():
            value = os.environ.get(env_key, "")
            if value:
                # Check if already have an active credential for this type
                with self._lock:
                    active = [
                        c for c in self._credentials.values()
                        if c.credential_type == ctype and c.active
                    ]
                if not active:
                    self.register(
                        credential_type=ctype,
                        secret_value=value,
                        description=f"Migrated from env var {env_key}",
                    )
                    migrated.append(ctype)
                    logger.info("Migrated WMCP credential from %s", env_key)

        return migrated

    def _store_secret(self, cred_id: str, value: str) -> None:
        """Store secret value via SecretStore."""
        try:
            from services.secret_store import SecretStore
            store = SecretStore()
            if store.read_only:
                logger.warning("SecretStore read-only — credential %s stored in meta only", cred_id)
                return
            secrets = store.read()
            wmcp_secrets = secrets.get(self.STORE_KEY, {})
            wmcp_secrets[cred_id] = value
            secrets[self.STORE_KEY] = wmcp_secrets
            store.write(secrets)
        except Exception as e:
            logger.warning("SecretStore write failed for %s: %s (credential in meta only)", cred_id, e)

    def _read_secret(self, cred_id: str) -> Optional[str]:
        """Read secret value from SecretStore."""
        try:
            from services.secret_store import SecretStore
            store = SecretStore()
            secrets = store.read()
            wmcp_secrets = secrets.get(self.STORE_KEY, {})
            return wmcp_secrets.get(cred_id)
        except Exception:
            return None

    @staticmethod
    def _check_env_source(credential_type: str) -> str:
        """Check if a credential is available via env var."""
        env_map = {
            "api_key": "WMCP_API_KEY",
            "proxy_token": "WMCP_PROXY_TOKEN",
            "bridge_secret": "OC_BRIDGE_SECRET",
        }
        env_key = env_map.get(credential_type, "")
        return "env_var" if os.environ.get(env_key) else "none"


class WmcpCredentialError(Exception):
    """WMCP credential operation error."""
    pass
