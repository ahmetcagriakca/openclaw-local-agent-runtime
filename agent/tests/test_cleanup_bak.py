"""Tests for stale .bak file cleanup (B-028, Sprint 56)."""
import os

# Add tools dir to path for imports
import sys
import time
from pathlib import Path

TOOLS_DIR = str(Path(__file__).resolve().parent.parent.parent / "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from cleanup_bak import cleanup_bak_files, is_bak_file, scan_bak_files, status


def _create_file(directory: Path, name: str, age_days: float = 0, content: str = "backup"):
    """Helper: create a file with specific age."""
    fpath = directory / name
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_text(content)
    if age_days > 0:
        old_time = time.time() - (age_days * 86400)
        os.utime(str(fpath), (old_time, old_time))
    return fpath


class TestIsBakFile:
    def test_bak_extension(self):
        assert is_bak_file(Path("file.bak")) is True

    def test_bak_json_extension(self):
        assert is_bak_file(Path("data.bak.json")) is True

    def test_backup_extension(self):
        assert is_bak_file(Path("config.backup")) is True

    def test_old_extension(self):
        assert is_bak_file(Path("settings.old")) is True

    def test_normal_file(self):
        assert is_bak_file(Path("app.py")) is False

    def test_json_file(self):
        assert is_bak_file(Path("data.json")) is False

    def test_bak_in_middle(self):
        assert is_bak_file(Path("file.bak.2024")) is True


class TestScanBakFiles:
    def test_scan_empty_dir(self, tmp_path):
        result = scan_bak_files(root=tmp_path, scan_dirs=["."])
        assert result == []

    def test_scan_finds_bak_files(self, tmp_path):
        _create_file(tmp_path, "a.bak")
        _create_file(tmp_path, "b.backup")
        _create_file(tmp_path, "c.json")  # not a bak file
        result = scan_bak_files(root=tmp_path, scan_dirs=["."])
        assert len(result) == 2

    def test_scan_sorted_oldest_first(self, tmp_path):
        _create_file(tmp_path, "old.bak", age_days=10)
        _create_file(tmp_path, "new.bak", age_days=0)
        result = scan_bak_files(root=tmp_path, scan_dirs=["."])
        assert result[0]["name"] == "old.bak"

    def test_scan_skips_git_dir(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        _create_file(git_dir, "index.bak")
        _create_file(tmp_path, "real.bak")
        result = scan_bak_files(root=tmp_path, scan_dirs=["."])
        assert len(result) == 1
        assert result[0]["name"] == "real.bak"

    def test_scan_skips_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        _create_file(nm, "cache.bak")
        result = scan_bak_files(root=tmp_path, scan_dirs=["."])
        assert len(result) == 0

    def test_scan_subdirectories(self, tmp_path):
        sub = tmp_path / "config"
        sub.mkdir()
        _create_file(sub, "settings.bak")
        result = scan_bak_files(root=tmp_path, scan_dirs=["config"])
        assert len(result) == 1

    def test_scan_nonexistent_dir(self, tmp_path):
        result = scan_bak_files(root=tmp_path, scan_dirs=["nonexistent"])
        assert result == []


class TestCleanupBakFiles:
    def test_cleanup_removes_stale(self, tmp_path):
        _create_file(tmp_path, "old.bak", age_days=60)
        _create_file(tmp_path, "new.bak", age_days=1)
        result = cleanup_bak_files(root=tmp_path, max_age_days=30, scan_dirs=["."])
        assert result["removed"] == 1
        assert not (tmp_path / "old.bak").exists()
        assert (tmp_path / "new.bak").exists()

    def test_cleanup_dry_run(self, tmp_path):
        _create_file(tmp_path, "old.bak", age_days=60)
        result = cleanup_bak_files(root=tmp_path, max_age_days=30, dry_run=True, scan_dirs=["."])
        assert result["removed"] == 1
        assert result["dry_run"] is True
        assert (tmp_path / "old.bak").exists()

    def test_cleanup_nothing_stale(self, tmp_path):
        _create_file(tmp_path, "new.bak", age_days=1)
        result = cleanup_bak_files(root=tmp_path, max_age_days=30, scan_dirs=["."])
        assert result["removed"] == 0

    def test_cleanup_empty_dir(self, tmp_path):
        result = cleanup_bak_files(root=tmp_path, max_age_days=30, scan_dirs=["."])
        assert result["total_bak_files"] == 0
        assert result["removed"] == 0

    def test_cleanup_bytes_freed(self, tmp_path):
        _create_file(tmp_path, "old.bak", age_days=60, content="x" * 1000)
        result = cleanup_bak_files(root=tmp_path, max_age_days=30, dry_run=True, scan_dirs=["."])
        assert result["bytes_freed"] >= 1000

    def test_cleanup_policy_in_result(self, tmp_path):
        result = cleanup_bak_files(root=tmp_path, max_age_days=45, scan_dirs=["."])
        assert result["policy"]["max_age_days"] == 45


class TestBakStatus:
    def test_status_empty(self, tmp_path):
        result = status(root=tmp_path)
        assert result["total_bak_files"] == 0
        assert result["files"] == []

    def test_status_with_files(self, tmp_path):
        _create_file(tmp_path, "a.bak")
        _create_file(tmp_path, "b.backup")
        result = status(root=tmp_path)
        assert result["total_bak_files"] == 2
        assert len(result["files"]) == 2
        assert result["total_size_bytes"] > 0
