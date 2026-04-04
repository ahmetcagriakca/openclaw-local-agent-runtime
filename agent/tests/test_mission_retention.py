"""Tests for mission retention policy (B-027, Sprint 56)."""
import json
import os
import time
from pathlib import Path

import pytest

from persistence.mission_retention import MissionRetentionPolicy


@pytest.fixture
def mission_dir(tmp_path):
    """Create a temporary mission directory with test files."""
    d = tmp_path / "missions"
    d.mkdir()
    return d


def _create_mission_file(mission_dir: Path, name: str, age_days: float = 0, size: int = 100):
    """Helper: create a mission JSON file with specific age."""
    fpath = mission_dir / name
    fpath.write_text(json.dumps({"mission_id": name, "goal": "test"}))
    if age_days > 0:
        old_time = time.time() - (age_days * 86400)
        os.utime(str(fpath), (old_time, old_time))
    return fpath


class TestMissionRetentionScan:
    def test_scan_empty_dir(self, mission_dir):
        policy = MissionRetentionPolicy(mission_dir=mission_dir)
        assert policy.scan() == []

    def test_scan_returns_files(self, mission_dir):
        _create_mission_file(mission_dir, "m1.json")
        _create_mission_file(mission_dir, "m2.json")
        policy = MissionRetentionPolicy(mission_dir=mission_dir)
        files = policy.scan()
        assert len(files) == 2

    def test_scan_sorted_oldest_first(self, mission_dir):
        _create_mission_file(mission_dir, "old.json", age_days=10)
        _create_mission_file(mission_dir, "new.json", age_days=0)
        policy = MissionRetentionPolicy(mission_dir=mission_dir)
        files = policy.scan()
        assert files[0]["name"] == "old.json"
        assert files[1]["name"] == "new.json"

    def test_scan_only_json_files(self, mission_dir):
        _create_mission_file(mission_dir, "m1.json")
        (mission_dir / "readme.txt").write_text("not json")
        policy = MissionRetentionPolicy(mission_dir=mission_dir)
        files = policy.scan()
        assert len(files) == 1

    def test_scan_nonexistent_dir(self, tmp_path):
        policy = MissionRetentionPolicy(mission_dir=tmp_path / "nope")
        assert policy.scan() == []


class TestMissionRetentionExpired:
    def test_no_expired_files(self, mission_dir):
        _create_mission_file(mission_dir, "m1.json", age_days=5)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30)
        assert policy.identify_expired() == []

    def test_expired_files_detected(self, mission_dir):
        _create_mission_file(mission_dir, "old.json", age_days=100)
        _create_mission_file(mission_dir, "new.json", age_days=5)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30)
        expired = policy.identify_expired()
        assert len(expired) == 1
        assert expired[0]["name"] == "old.json"

    def test_all_expired(self, mission_dir):
        _create_mission_file(mission_dir, "a.json", age_days=50)
        _create_mission_file(mission_dir, "b.json", age_days=60)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30)
        expired = policy.identify_expired()
        assert len(expired) == 2


class TestMissionRetentionOverflow:
    def test_no_overflow(self, mission_dir):
        _create_mission_file(mission_dir, "m1.json")
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_files=10)
        assert policy.identify_overflow() == []

    def test_overflow_detected(self, mission_dir):
        for i in range(5):
            _create_mission_file(mission_dir, f"m{i}.json", age_days=5 - i)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_files=3)
        overflow = policy.identify_overflow()
        assert len(overflow) == 2
        # Oldest files should be overflow candidates
        assert overflow[0]["name"] == "m0.json"

    def test_exact_limit_no_overflow(self, mission_dir):
        for i in range(3):
            _create_mission_file(mission_dir, f"m{i}.json")
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_files=3)
        assert policy.identify_overflow() == []


class TestMissionRetentionCandidates:
    def test_combined_candidates_deduplicated(self, mission_dir):
        # File is both expired AND overflow
        _create_mission_file(mission_dir, "old.json", age_days=100)
        _create_mission_file(mission_dir, "new1.json", age_days=1)
        _create_mission_file(mission_dir, "new2.json", age_days=0)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30, max_files=2)
        candidates = policy.identify_candidates()
        names = [c["name"] for c in candidates]
        assert "old.json" in names
        assert len(names) == len(set(names))  # no duplicates


class TestMissionRetentionCleanup:
    def test_dry_run_no_deletion(self, mission_dir):
        _create_mission_file(mission_dir, "old.json", age_days=100)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30)
        result = policy.cleanup(dry_run=True)
        assert result["dry_run"] is True
        assert result["removed"] == 1
        assert (mission_dir / "old.json").exists()

    def test_actual_cleanup_removes_files(self, mission_dir):
        _create_mission_file(mission_dir, "old.json", age_days=100)
        _create_mission_file(mission_dir, "keep.json", age_days=1)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30)
        result = policy.cleanup(dry_run=False)
        assert result["removed"] == 1
        assert not (mission_dir / "old.json").exists()
        assert (mission_dir / "keep.json").exists()

    def test_cleanup_bounded_batch(self, mission_dir):
        for i in range(10):
            _create_mission_file(mission_dir, f"old{i}.json", age_days=100)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30)
        result = policy.cleanup(dry_run=False, max_batch=3)
        assert result["removed"] == 3
        # 7 remaining
        remaining = list(mission_dir.glob("*.json"))
        assert len(remaining) == 7

    def test_cleanup_returns_bytes_freed(self, mission_dir):
        _create_mission_file(mission_dir, "old.json", age_days=100)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30)
        result = policy.cleanup(dry_run=True)
        assert result["bytes_freed"] > 0

    def test_cleanup_empty_dir(self, mission_dir):
        policy = MissionRetentionPolicy(mission_dir=mission_dir)
        result = policy.cleanup()
        assert result["removed"] == 0
        assert result["total_files"] == 0


class TestMissionRetentionStatus:
    def test_status_empty(self, mission_dir):
        policy = MissionRetentionPolicy(mission_dir=mission_dir)
        s = policy.status()
        assert s["total_files"] == 0
        assert s["oldest_file"] is None

    def test_status_with_files(self, mission_dir):
        _create_mission_file(mission_dir, "old.json", age_days=100)
        _create_mission_file(mission_dir, "new.json", age_days=1)
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=30)
        s = policy.status()
        assert s["total_files"] == 2
        assert s["expired_count"] == 1
        assert s["oldest_file"] == "old.json"
        assert s["newest_file"] == "new.json"
        assert s["policy"]["max_age_days"] == 30

    def test_status_total_size(self, mission_dir):
        _create_mission_file(mission_dir, "m1.json")
        _create_mission_file(mission_dir, "m2.json")
        policy = MissionRetentionPolicy(mission_dir=mission_dir)
        s = policy.status()
        assert s["total_size_bytes"] > 0


class TestMissionRetentionPolicy:
    def test_default_policy_values(self, mission_dir):
        policy = MissionRetentionPolicy(mission_dir=mission_dir)
        assert policy.max_age_days == 90
        assert policy.max_files == 5000

    def test_custom_policy_values(self, mission_dir):
        policy = MissionRetentionPolicy(mission_dir=mission_dir, max_age_days=7, max_files=100)
        assert policy.max_age_days == 7
        assert policy.max_files == 100
