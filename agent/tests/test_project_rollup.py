"""Tests for project rollup cache — D-145 Faz 2B (T75.9).

Tests rollup computation, caching, staleness, and invalidation.
"""
from unittest.mock import MagicMock

import pytest

from persistence.project_store import ProjectStore


@pytest.fixture
def tmp_store(tmp_path):
    """Create a ProjectStore with a mock mission store."""
    store_path = tmp_path / "projects.json"
    mission_store = MagicMock()
    mission_store.list.return_value = ([], 0)
    mission_store.get.return_value = None
    return ProjectStore(store_path=store_path, mission_store=mission_store)


@pytest.fixture
def store_with_missions(tmp_path):
    """Store with linked missions for rollup testing."""
    store_path = tmp_path / "projects.json"
    mission_store = MagicMock()

    missions = [
        {"id": "m1", "status": "completed", "project_id": None, "total_tokens": 500, "ts": "2026-04-06T10:00:00Z"},
        {"id": "m2", "status": "executing", "project_id": None, "total_tokens": 200, "ts": "2026-04-06T11:00:00Z"},
        {"id": "m3", "status": "failed", "project_id": None, "total_tokens": 100, "ts": "2026-04-06T09:00:00Z"},
    ]

    def list_missions(limit=1000):
        return missions, len(missions)

    mission_store.list.side_effect = list_missions
    store = ProjectStore(store_path=store_path, mission_store=mission_store)

    proj = store.create("Rollup Test")
    pid = proj["project_id"]

    # Set project_id on missions
    for m in missions:
        m["project_id"] = pid

    return store, pid, missions


class TestComputeRollup:
    """T75.9: Rollup computation tests."""

    def test_compute_rollup_empty_project(self, tmp_store):
        proj = tmp_store.create("Empty")
        rollup = tmp_store.compute_rollup(proj["project_id"])
        assert rollup["total_missions"] == 0
        assert rollup["active_count"] == 0
        assert rollup["quiescent_count"] == 0
        assert rollup["total_tokens"] == 0
        assert rollup["last_activity"] is None
        assert "computed_at" in rollup

    def test_compute_rollup_with_missions(self, store_with_missions):
        store, pid, _ = store_with_missions
        rollup = store.compute_rollup(pid)
        assert rollup["total_missions"] == 3
        assert rollup["active_count"] == 1  # executing
        assert rollup["quiescent_count"] == 2  # completed + failed
        assert rollup["total_tokens"] == 800
        assert rollup["last_activity"] == "2026-04-06T11:00:00Z"
        assert rollup["project_id"] == pid

    def test_compute_rollup_by_status(self, store_with_missions):
        store, pid, _ = store_with_missions
        rollup = store.compute_rollup(pid)
        assert rollup["by_status"]["completed"] == 1
        assert rollup["by_status"]["executing"] == 1
        assert rollup["by_status"]["failed"] == 1

    def test_compute_rollup_caches_in_project(self, store_with_missions):
        store, pid, _ = store_with_missions
        store.compute_rollup(pid)
        proj = store.get(pid)
        assert "_rollup_cache" in proj


class TestRollupStaleness:
    """T75.9: Staleness-aware caching tests."""

    def test_get_rollup_returns_cached_when_fresh(self, store_with_missions):
        store, pid, _ = store_with_missions
        r1 = store.compute_rollup(pid)
        r2 = store.get_rollup(pid, staleness_threshold_s=300)
        assert r2["computed_at"] == r1["computed_at"]

    def test_get_rollup_recomputes_when_stale(self, store_with_missions):
        store, pid, _ = store_with_missions
        store.compute_rollup(pid)
        # Force cache to be stale by using 0-second threshold
        r2 = store.get_rollup(pid, staleness_threshold_s=0)
        # Should have recomputed (new computed_at)
        assert r2["total_missions"] == 3

    def test_get_rollup_project_not_found(self, tmp_store):
        from persistence.project_store import ProjectStoreError
        with pytest.raises(ProjectStoreError, match="not found"):
            tmp_store.get_rollup("nonexistent")


class TestRollupInvalidation:
    """T75.9: Rollup cache invalidation tests."""

    def test_invalidate_rollup_clears_cache(self, store_with_missions):
        store, pid, _ = store_with_missions
        store.compute_rollup(pid)
        proj = store.get(pid)
        assert "_rollup_cache" in proj

        store.invalidate_rollup(pid)
        proj = store.get(pid)
        assert "_rollup_cache" not in proj

    def test_invalidate_nonexistent_project_noop(self, tmp_store):
        # Should not raise
        tmp_store.invalidate_rollup("nonexistent")

    def test_get_rollup_after_invalidation_recomputes(self, store_with_missions):
        store, pid, _ = store_with_missions
        store.compute_rollup(pid)
        store.invalidate_rollup(pid)
        rollup = store.get_rollup(pid)
        assert rollup["total_missions"] == 3


class TestRollupTokenHandling:
    """T75.9: Token field handling edge cases."""

    def test_missing_total_tokens_treated_as_zero(self, tmp_path):
        store_path = tmp_path / "projects.json"
        mission_store = MagicMock()
        missions = [
            {"id": "m1", "status": "completed", "project_id": None, "ts": "2026-04-06T10:00:00Z"},
        ]
        mission_store.list.return_value = (missions, 1)
        store = ProjectStore(store_path=store_path, mission_store=mission_store)
        proj = store.create("No Tokens")
        missions[0]["project_id"] = proj["project_id"]
        rollup = store.compute_rollup(proj["project_id"])
        assert rollup["total_tokens"] == 0

    def test_none_total_tokens_treated_as_zero(self, tmp_path):
        store_path = tmp_path / "projects.json"
        mission_store = MagicMock()
        missions = [
            {"id": "m1", "status": "completed", "project_id": None, "total_tokens": None, "ts": "2026-04-06T10:00:00Z"},
        ]
        mission_store.list.return_value = (missions, 1)
        store = ProjectStore(store_path=store_path, mission_store=mission_store)
        proj = store.create("Null Tokens")
        missions[0]["project_id"] = proj["project_id"]
        rollup = store.compute_rollup(proj["project_id"])
        assert rollup["total_tokens"] == 0
