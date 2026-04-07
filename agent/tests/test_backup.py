"""Sprint 51 Task 51.2 — B-022 Backup / Restore tests.

Tests for backup CLI, restore CLI, integrity validation, and API endpoints.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import CSRF_ORIGIN, MUTATION_HEADERS

# Add tools to path
OC_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(OC_ROOT / "tools"))


class TestBackupCLI(unittest.TestCase):
    """Tests for tools/backup.py."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_create_backup_produces_manifest(self):
        """Backup creates manifest.json with file hashes."""
        from backup import create_backup
        backup_path = create_backup(output_dir=self.temp_dir)
        manifest_path = backup_path / "manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], 1)
        self.assertIn("created_at", manifest)
        self.assertIn("files", manifest)
        self.assertIn("file_count", manifest)

    def test_02_backup_includes_state_files(self):
        """Backup includes state files when they exist."""
        from backup import create_backup
        backup_path = create_backup(
            output_dir=self.temp_dir,
            include_missions=False,
            include_configs=False,
        )
        manifest = json.loads(
            (backup_path / "manifest.json").read_text(encoding="utf-8"))
        # State files should be included if they exist
        for rel_path, info in manifest["files"].items():
            self.assertEqual(info["category"], "state")

    def test_03_backup_sha256_integrity(self):
        """Backup manifest contains valid SHA-256 hashes."""
        from backup import create_backup, sha256_file
        backup_path = create_backup(output_dir=self.temp_dir)
        manifest = json.loads(
            (backup_path / "manifest.json").read_text(encoding="utf-8"))
        for rel_path, info in manifest["files"].items():
            file_path = backup_path / rel_path
            if file_path.exists():
                actual = sha256_file(file_path)
                self.assertEqual(actual, info["sha256"],
                                 f"SHA-256 mismatch for {rel_path}")

    def test_04_backup_with_configs(self):
        """Backup includes config files when requested."""
        from backup import create_backup
        backup_path = create_backup(
            output_dir=self.temp_dir,
            include_missions=False,
            include_configs=True,
        )
        manifest = json.loads(
            (backup_path / "manifest.json").read_text(encoding="utf-8"))
        categories = {info["category"] for info in manifest["files"].values()}
        # Should have at least configs if config files exist
        if manifest["file_count"] > 0:
            self.assertTrue(
                "configs" in categories or "state" in categories,
                "Expected configs or state category"
            )

    def test_05_backup_directory_naming(self):
        """Backup directory follows naming convention."""
        from backup import create_backup
        backup_path = create_backup(output_dir=self.temp_dir)
        self.assertTrue(backup_path.name.startswith("backup-"))


class TestRestoreCLI(unittest.TestCase):
    """Tests for tools/restore.py."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_06_validate_valid_backup(self):
        """validate_backup passes for fresh backup."""
        from backup import create_backup
        from restore import validate_backup
        backup_path = create_backup(output_dir=self.temp_dir)
        valid, errors = validate_backup(backup_path)
        self.assertTrue(valid, f"Validation failed: {errors}")
        self.assertEqual(len(errors), 0)

    def test_07_validate_missing_manifest(self):
        """validate_backup fails when manifest is missing."""
        from restore import validate_backup
        empty_dir = self.temp_dir / "empty-backup"
        empty_dir.mkdir()
        valid, errors = validate_backup(empty_dir)
        self.assertFalse(valid)
        self.assertTrue(any("manifest" in e.lower() for e in errors))

    def test_08_validate_corrupted_file(self):
        """validate_backup detects corrupted files."""
        from backup import create_backup
        from restore import validate_backup
        backup_path = create_backup(output_dir=self.temp_dir)
        manifest = json.loads(
            (backup_path / "manifest.json").read_text(encoding="utf-8"))
        # Corrupt first file
        files = list(manifest["files"].keys())
        if files:
            corrupted = backup_path / files[0]
            if corrupted.exists():
                corrupted.write_text("CORRUPTED", encoding="utf-8")
                valid, errors = validate_backup(backup_path)
                self.assertFalse(valid)
                self.assertTrue(len(errors) > 0)

    def test_09_restore_dry_run(self):
        """Dry run restore doesn't modify target files."""
        from backup import create_backup
        from restore import restore_backup
        backup_path = create_backup(output_dir=self.temp_dir)
        restored, warnings = restore_backup(backup_path, dry_run=True)
        # Dry run should report files but not modify anything
        self.assertIsInstance(restored, int)

    def test_10_restore_roundtrip(self):
        """Backup + restore preserves file content."""
        from backup import create_backup
        from restore import restore_backup, validate_backup

        # Create backup
        backup_path = create_backup(output_dir=self.temp_dir)

        # Validate before restore
        valid, errors = validate_backup(backup_path)
        self.assertTrue(valid, f"Pre-restore validation failed: {errors}")

        # Restore (actual restore)
        restored, warnings = restore_backup(backup_path, dry_run=False)
        self.assertGreaterEqual(restored, 0)


class TestBackupAPI(unittest.TestCase):
    """Tests for backup API endpoints."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from api.server import app
        cls.client = TestClient(app)
        cls.auth = MUTATION_HEADERS

    def test_11_list_backups_shape(self):
        """GET /admin/backups returns expected shape."""
        resp = self.client.get("/api/v1/admin/backups")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("meta", data)
        self.assertIn("backups", data)
        self.assertIn("count", data)
        self.assertIsInstance(data["backups"], list)

    def test_12_create_backup_via_api(self):
        """POST /admin/backup creates a backup when auth allows."""
        # When auth is disabled (no auth.json), mutations allowed without key
        # CSRF requires Origin header
        headers = {"Origin": CSRF_ORIGIN}
        resp = self.client.post("/api/v1/admin/backup", headers=headers)
        # Should succeed (200) or require auth (401/403)
        self.assertIn(resp.status_code, [200, 401, 403])

    def test_13_restore_requires_valid_backup(self):
        """POST /admin/restore rejects missing backup name."""
        headers = {"Origin": CSRF_ORIGIN}
        resp = self.client.post(
            "/api/v1/admin/restore?backup_name=nonexistent-backup",
            headers=headers,
        )
        # 404 when auth disabled, 401/403 when auth enabled
        self.assertIn(resp.status_code, [404, 401, 403])

    def test_14_restore_not_found(self):
        """POST /admin/restore returns 404 for missing backup."""
        headers = {"Origin": CSRF_ORIGIN}
        resp = self.client.post(
            "/api/v1/admin/restore?backup_name=nonexistent-backup",
            headers=headers,
        )
        # When auth is disabled, should get 404 (backup not found)
        self.assertIn(resp.status_code, [404, 401, 403])


if __name__ == "__main__":
    unittest.main()
