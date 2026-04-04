"""Tests for secret rotation — B-007."""
import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from services.secret_rotation import (
    RotationPolicy,
    RotationStatus,
    SecretRotationError,
    SecretRotationService,
)


@pytest.fixture
def tmp_meta(tmp_path):
    """Temporary metadata file path."""
    return str(tmp_path / "secret-rotation-meta.json")


@pytest.fixture
def policy():
    return RotationPolicy(max_age_days=30, warning_threshold_days=7)


@pytest.fixture
def service(tmp_meta, policy):
    return SecretRotationService(meta_path=tmp_meta, policy=policy)


@pytest.fixture
def key_32():
    """Generate a 32-byte key."""
    return os.urandom(32)


@pytest.fixture
def another_key_32():
    """Generate another 32-byte key."""
    return os.urandom(32)


# ── Policy tests ──────────────────────────────────────────────

class TestRotationPolicy:
    def test_default_policy(self):
        p = RotationPolicy()
        assert p.max_age_days == 90
        assert p.warning_threshold_days == 14
        assert p.auto_rotate is False

    def test_custom_policy(self):
        p = RotationPolicy(max_age_days=30, warning_threshold_days=5, auto_rotate=True)
        assert p.max_age_days == 30
        assert p.warning_threshold_days == 5
        assert p.auto_rotate is True


# ── Initialization tests ─────────────────────────────────────

class TestInitialize:
    def test_initialize_creates_meta(self, service, key_32, tmp_meta):
        meta = service.initialize(key_32)
        assert meta.key_hash != ""
        assert meta.rotation_count == 0
        assert meta.created_at != ""
        assert os.path.exists(tmp_meta)

    def test_initialize_persists_to_disk(self, service, key_32, tmp_meta):
        service.initialize(key_32)
        with open(tmp_meta, "r") as f:
            data = json.load(f)
        assert data["key_hash"] != ""
        assert data["rotation_count"] == 0

    def test_initialize_records_key_hash(self, service, key_32):
        meta = service.initialize(key_32)
        assert len(meta.key_hash) == 16  # SHA-256 truncated to 16 hex chars


# ── Status tests ──────────────────────────────────────────────

class TestStatus:
    def test_status_unknown_no_meta(self, service):
        result = service.status()
        assert result["status"] == RotationStatus.UNKNOWN
        assert result["days_since_rotation"] == -1

    def test_status_ok_recent(self, service, key_32):
        service.initialize(key_32)
        result = service.status(key_32)
        assert result["status"] == RotationStatus.OK
        assert result["days_since_rotation"] == 0
        assert result["key_hash_match"] is True

    def test_status_warning_approaching(self, service, key_32, tmp_meta):
        service.initialize(key_32)
        # Backdate rotation to 25 days ago (30 - 7 = 23 day threshold)
        meta = service._load_meta()
        old_date = datetime.now(timezone.utc) - timedelta(days=25)
        meta.rotated_at = old_date.isoformat()
        service._save_meta(meta)
        result = service.status()
        assert result["status"] == RotationStatus.WARNING

    def test_status_expired(self, service, key_32, tmp_meta):
        service.initialize(key_32)
        meta = service._load_meta()
        old_date = datetime.now(timezone.utc) - timedelta(days=35)
        meta.rotated_at = old_date.isoformat()
        service._save_meta(meta)
        result = service.status()
        assert result["status"] == RotationStatus.EXPIRED

    def test_status_key_mismatch(self, service, key_32, another_key_32):
        service.initialize(key_32)
        result = service.status(another_key_32)
        assert result["key_hash_match"] is False


# ── Check due tests ──────────────────────────────────────────

class TestCheckDue:
    def test_not_due_when_recent(self, service, key_32):
        service.initialize(key_32)
        assert service.check_due() is False

    def test_due_when_expired(self, service, key_32, tmp_meta):
        service.initialize(key_32)
        meta = service._load_meta()
        old_date = datetime.now(timezone.utc) - timedelta(days=35)
        meta.rotated_at = old_date.isoformat()
        service._save_meta(meta)
        assert service.check_due() is True

    def test_due_when_warning(self, service, key_32, tmp_meta):
        service.initialize(key_32)
        meta = service._load_meta()
        old_date = datetime.now(timezone.utc) - timedelta(days=25)
        meta.rotated_at = old_date.isoformat()
        service._save_meta(meta)
        assert service.check_due() is True


# ── Rotate tests ─────────────────────────────────────────────

class TestRotate:
    def test_rotate_success(self, service, key_32, another_key_32):
        service.initialize(key_32)
        result = service.rotate(key_32, another_key_32)
        assert result["success"] is True
        assert result["rotation_count"] == 1
        assert result["old_key_hash"] != result["new_key_hash"]

    def test_rotate_updates_meta(self, service, key_32, another_key_32, tmp_meta):
        service.initialize(key_32)
        service.rotate(key_32, another_key_32)
        with open(tmp_meta, "r") as f:
            data = json.load(f)
        assert data["rotation_count"] == 1
        assert data["previous_key_hash"] != ""

    def test_rotate_increments_count(self, service, key_32):
        service.initialize(key_32)
        k2 = os.urandom(32)
        k3 = os.urandom(32)
        service.rotate(key_32, k2)
        service.rotate(k2, k3)
        result = service.status()
        assert result["rotation_count"] == 2

    def test_rotate_rejects_short_key(self, service, key_32):
        service.initialize(key_32)
        with pytest.raises(SecretRotationError, match="32 bytes"):
            service.rotate(key_32, b"short")

    def test_rotate_rejects_same_key(self, service, key_32):
        service.initialize(key_32)
        with pytest.raises(SecretRotationError, match="must differ"):
            service.rotate(key_32, key_32)

    def test_rotate_with_secret_store(self, service, key_32, another_key_32):
        service.initialize(key_32)
        mock_store = MagicMock()
        mock_store.read.return_value = {"api_key": "test123"}
        result = service.rotate(key_32, another_key_32, secret_store=mock_store)
        assert result["secrets_re_encrypted"] is True
        mock_store.read.assert_called_once()
        mock_store.write.assert_called_once_with({"api_key": "test123"})

    def test_rotate_rollback_on_failure(self, service, key_32, another_key_32):
        service.initialize(key_32)
        mock_store = MagicMock()
        mock_store.read.return_value = {"key": "val"}
        mock_store.write.side_effect = Exception("disk full")
        with pytest.raises(SecretRotationError, match="Re-encryption failed"):
            service.rotate(key_32, another_key_32, secret_store=mock_store)
        # Key should be rolled back
        assert mock_store._key == key_32


# ── Schedule tests ────────────────────────────────────────────

class TestSchedule:
    def test_schedule_unknown_no_meta(self, service):
        result = service.get_schedule()
        assert result["status"] == RotationStatus.UNKNOWN
        assert result["next_rotation"] is None

    def test_schedule_with_meta(self, service, key_32):
        service.initialize(key_32)
        result = service.get_schedule()
        assert result["next_rotation"] is not None
        assert result["policy"]["max_age_days"] == 30

    def test_schedule_shows_policy(self, service, key_32):
        service.initialize(key_32)
        result = service.get_schedule()
        assert result["policy"]["warning_threshold_days"] == 7


# ── Policy update tests ──────────────────────────────────────

class TestPolicyUpdate:
    def test_update_max_age(self, service, key_32):
        service.initialize(key_32)
        policy = service.update_policy(max_age_days=60)
        assert policy.max_age_days == 60

    def test_update_warning_threshold(self, service, key_32):
        service.initialize(key_32)
        policy = service.update_policy(warning_threshold_days=3)
        assert policy.warning_threshold_days == 3

    def test_update_rejects_invalid_age(self, service):
        with pytest.raises(SecretRotationError, match="max_age_days"):
            service.update_policy(max_age_days=0)

    def test_update_rejects_negative_threshold(self, service):
        with pytest.raises(SecretRotationError, match="warning_threshold_days"):
            service.update_policy(warning_threshold_days=-1)

    def test_update_persists(self, service, key_32, tmp_meta):
        service.initialize(key_32)
        service.update_policy(max_age_days=45)
        with open(tmp_meta, "r") as f:
            data = json.load(f)
        assert data["policy"]["max_age_days"] == 45


# ── Edge cases ────────────────────────────────────────────────

class TestEdgeCases:
    def test_corrupted_meta_returns_default(self, tmp_meta):
        with open(tmp_meta, "w") as f:
            f.write("not json")
        svc = SecretRotationService(meta_path=tmp_meta)
        result = svc.status()
        assert result["status"] == RotationStatus.UNKNOWN

    def test_hash_key_deterministic(self):
        key = b"x" * 32
        h1 = SecretRotationService._hash_key(key)
        h2 = SecretRotationService._hash_key(key)
        assert h1 == h2

    def test_hash_key_different_for_different_keys(self):
        h1 = SecretRotationService._hash_key(b"a" * 32)
        h2 = SecretRotationService._hash_key(b"b" * 32)
        assert h1 != h2
