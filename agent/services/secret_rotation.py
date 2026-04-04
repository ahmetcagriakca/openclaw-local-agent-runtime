"""Secret rotation — B-007.

Automatic rotation scheduler for encrypted secrets (D-129 extension).
Tracks rotation metadata, enforces age-based policies, audit logging.
"""
import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mcc.secret_rotation")

# Root path
_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
META_PATH = str(_ROOT / "config" / "secret-rotation-meta.json")


@dataclass
class RotationPolicy:
    """Rotation policy configuration."""
    max_age_days: int = 90
    warning_threshold_days: int = 14
    auto_rotate: bool = False


@dataclass
class RotationMeta:
    """Secret rotation metadata — persisted to JSON."""
    key_hash: str = ""
    created_at: str = ""
    rotated_at: str = ""
    rotation_count: int = 0
    previous_key_hash: str = ""
    policy: dict = None

    def __post_init__(self):
        if self.policy is None:
            self.policy = asdict(RotationPolicy())


class RotationStatus:
    OK = "ok"
    WARNING = "warning"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class SecretRotationService:
    """Manages secret key rotation lifecycle.

    - Tracks rotation metadata in JSON sidecar
    - Enforces age-based rotation policies
    - Provides status checks (ok/warning/expired)
    - Audit trail for all rotation events
    """

    def __init__(self, meta_path: str = None, policy: RotationPolicy = None):
        self._meta_path = meta_path or META_PATH
        self._policy = policy or RotationPolicy()
        self._meta: Optional[RotationMeta] = None

    def _load_meta(self) -> RotationMeta:
        """Load rotation metadata from disk."""
        if os.path.exists(self._meta_path):
            try:
                with open(self._meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return RotationMeta(**data)
            except (json.JSONDecodeError, TypeError, OSError) as e:
                logger.error("Failed to load rotation meta: %s", e)
        return RotationMeta()

    def _save_meta(self, meta: RotationMeta) -> None:
        """Persist rotation metadata atomically (D-071)."""
        from utils.atomic_write import atomic_write_json
        atomic_write_json(self._meta_path, asdict(meta))

    @staticmethod
    def _hash_key(key: bytes) -> str:
        """SHA-256 hash of key for tracking (never store raw key)."""
        return hashlib.sha256(key).hexdigest()[:16]

    def initialize(self, current_key: bytes) -> RotationMeta:
        """Initialize rotation tracking for current key.

        Called when no metadata exists yet. Sets created_at to now.
        """
        now = datetime.now(timezone.utc).isoformat()
        meta = RotationMeta(
            key_hash=self._hash_key(current_key),
            created_at=now,
            rotated_at=now,
            rotation_count=0,
            previous_key_hash="",
            policy=asdict(self._policy),
        )
        self._save_meta(meta)
        self._meta = meta
        logger.info("Secret rotation initialized — key_hash=%s", meta.key_hash)
        return meta

    def status(self, current_key: bytes = None) -> dict:
        """Get current rotation status.

        Returns dict with:
        - status: ok/warning/expired/unknown
        - days_since_rotation: int
        - days_until_expiry: int (negative if overdue)
        - rotation_count: int
        - meta: full metadata
        """
        meta = self._load_meta()
        if not meta.rotated_at:
            return {
                "status": RotationStatus.UNKNOWN,
                "days_since_rotation": -1,
                "days_until_expiry": -1,
                "rotation_count": 0,
                "meta": asdict(meta),
            }

        policy = RotationPolicy(**meta.policy) if meta.policy else self._policy

        try:
            last_rotation = datetime.fromisoformat(meta.rotated_at)
        except (ValueError, TypeError):
            return {
                "status": RotationStatus.UNKNOWN,
                "days_since_rotation": -1,
                "days_until_expiry": -1,
                "rotation_count": meta.rotation_count,
                "meta": asdict(meta),
            }

        now = datetime.now(timezone.utc)
        age = now - last_rotation
        days_since = age.days
        days_until = policy.max_age_days - days_since

        if days_since >= policy.max_age_days:
            status = RotationStatus.EXPIRED
        elif days_until <= policy.warning_threshold_days:
            status = RotationStatus.WARNING
        else:
            status = RotationStatus.OK

        # Verify key hash if key provided
        key_match = True
        if current_key is not None:
            key_match = self._hash_key(current_key) == meta.key_hash

        return {
            "status": status,
            "days_since_rotation": days_since,
            "days_until_expiry": days_until,
            "rotation_count": meta.rotation_count,
            "key_hash_match": key_match,
            "meta": asdict(meta),
        }

    def check_due(self) -> bool:
        """Check if rotation is due based on policy."""
        result = self.status()
        return result["status"] in (RotationStatus.EXPIRED, RotationStatus.WARNING)

    def rotate(self, old_key: bytes, new_key: bytes, secret_store=None) -> dict:
        """Execute secret rotation.

        Steps:
        1. Read secrets with old key
        2. Re-encrypt with new key
        3. Update rotation metadata
        4. Log audit event

        Args:
            old_key: Current encryption key (32 bytes)
            new_key: New encryption key (32 bytes)
            secret_store: Optional SecretStore instance for re-encryption

        Returns:
            dict with rotation result
        """
        if len(old_key) != 32:
            raise SecretRotationError("old_key must be 32 bytes")
        if len(new_key) != 32:
            raise SecretRotationError("new_key must be 32 bytes")
        if old_key == new_key:
            raise SecretRotationError("new_key must differ from old_key")

        meta = self._load_meta()
        old_hash = self._hash_key(old_key)
        new_hash = self._hash_key(new_key)
        now = datetime.now(timezone.utc).isoformat()

        # Re-encrypt secrets if store provided
        secrets_rotated = False
        if secret_store is not None:
            try:
                secrets = secret_store.read()
                # Update store key and re-write
                secret_store._key = new_key
                secret_store.write(secrets)
                secrets_rotated = True
                logger.info("Secrets re-encrypted with new key")
            except Exception as e:
                # Rollback key on failure
                secret_store._key = old_key
                raise SecretRotationError(f"Re-encryption failed: {e}")

        # Update metadata
        meta.previous_key_hash = old_hash
        meta.key_hash = new_hash
        meta.rotated_at = now
        meta.rotation_count += 1
        meta.policy = asdict(self._policy)

        if not meta.created_at:
            meta.created_at = now

        self._save_meta(meta)
        self._meta = meta

        result = {
            "success": True,
            "rotated_at": now,
            "rotation_count": meta.rotation_count,
            "old_key_hash": old_hash,
            "new_key_hash": new_hash,
            "secrets_re_encrypted": secrets_rotated,
        }
        logger.info("Secret rotation completed — count=%d, hash=%s→%s",
                     meta.rotation_count, old_hash, new_hash)
        return result

    def get_schedule(self) -> dict:
        """Get rotation schedule based on policy."""
        meta = self._load_meta()
        policy = RotationPolicy(**meta.policy) if meta.policy else self._policy

        if not meta.rotated_at:
            return {
                "policy": asdict(policy),
                "next_rotation": None,
                "status": RotationStatus.UNKNOWN,
            }

        try:
            last = datetime.fromisoformat(meta.rotated_at)
            next_rotation = last + timedelta(days=policy.max_age_days)
        except (ValueError, TypeError):
            return {
                "policy": asdict(policy),
                "next_rotation": None,
                "status": RotationStatus.UNKNOWN,
            }

        return {
            "policy": asdict(policy),
            "last_rotation": meta.rotated_at,
            "next_rotation": next_rotation.isoformat(),
            "rotation_count": meta.rotation_count,
            "status": self.status()["status"],
        }

    def update_policy(self, max_age_days: int = None,
                      warning_threshold_days: int = None,
                      auto_rotate: bool = None) -> RotationPolicy:
        """Update rotation policy. Persists immediately."""
        if max_age_days is not None:
            if max_age_days < 1:
                raise SecretRotationError("max_age_days must be >= 1")
            self._policy.max_age_days = max_age_days
        if warning_threshold_days is not None:
            if warning_threshold_days < 0:
                raise SecretRotationError("warning_threshold_days must be >= 0")
            self._policy.warning_threshold_days = warning_threshold_days
        if auto_rotate is not None:
            self._policy.auto_rotate = auto_rotate

        # Update in metadata if exists
        meta = self._load_meta()
        if meta.rotated_at:
            meta.policy = asdict(self._policy)
            self._save_meta(meta)

        return self._policy


class SecretRotationError(Exception):
    """Secret rotation operation error."""
    pass
