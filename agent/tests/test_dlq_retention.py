"""Tests for B-026 DLQ Retention Policy (Sprint 49).

Covers: TTL expiry, max entries cap, batch limits,
age-first ordering, observability output, auto-cleanup on enqueue.
"""

import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from persistence.dlq_store import DLQStore


@pytest.fixture
def tmp_store():
    """Create DLQStore with temp file and short retention."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    store = DLQStore(store_path=path, max_age_days=7, max_entries=5)
    yield store


def _make_mission(mission_id: str) -> dict:
    return {"missionId": mission_id, "goal": f"goal-{mission_id}", "stages": []}


class TestRetentionCleanup:
    def test_cleanup_empty_store(self, tmp_store):
        result = tmp_store.cleanup()
        assert result["removed_age"] == 0
        assert result["removed_count"] == 0

    def test_age_purge(self, tmp_store):
        # Manually insert old entries
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        with tmp_store._lock:
            tmp_store._entries["dlq-old1"] = {
                "dlq_id": "dlq-old1", "mission_id": "old1",
                "goal": "old", "error": "", "failed_stage_id": "",
                "failed_at": old_time, "status": "pending",
                "retry_count": 0, "mission_snapshot": {},
            }
            tmp_store._entries["dlq-new1"] = {
                "dlq_id": "dlq-new1", "mission_id": "new1",
                "goal": "new", "error": "", "failed_stage_id": "",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending", "retry_count": 0, "mission_snapshot": {},
            }

        result = tmp_store.cleanup()
        assert result["removed_age"] == 1
        assert tmp_store.count == 1

    def test_count_trim(self, tmp_store):
        # Insert 8 entries (max_entries=5)
        now = datetime.now(timezone.utc)
        with tmp_store._lock:
            for i in range(8):
                t = (now - timedelta(hours=i)).isoformat()
                tmp_store._entries[f"dlq-e{i}"] = {
                    "dlq_id": f"dlq-e{i}", "mission_id": f"e{i}",
                    "goal": "", "error": "", "failed_stage_id": "",
                    "failed_at": t, "status": "pending",
                    "retry_count": 0, "mission_snapshot": {},
                }

        result = tmp_store.cleanup()
        assert result["removed_count"] == 3  # 8 - 5 = 3
        assert tmp_store.count == 5

    def test_age_first_then_count(self, tmp_store):
        """Age purge runs before count trim."""
        now = datetime.now(timezone.utc)
        old_time = (now - timedelta(days=10)).isoformat()
        with tmp_store._lock:
            # 2 old + 6 new = 8 total, max_entries=5
            for i in range(2):
                tmp_store._entries[f"dlq-old{i}"] = {
                    "dlq_id": f"dlq-old{i}", "mission_id": f"old{i}",
                    "goal": "", "error": "", "failed_stage_id": "",
                    "failed_at": old_time, "status": "pending",
                    "retry_count": 0, "mission_snapshot": {},
                }
            for i in range(6):
                t = (now - timedelta(hours=i)).isoformat()
                tmp_store._entries[f"dlq-new{i}"] = {
                    "dlq_id": f"dlq-new{i}", "mission_id": f"new{i}",
                    "goal": "", "error": "", "failed_stage_id": "",
                    "failed_at": t, "status": "pending",
                    "retry_count": 0, "mission_snapshot": {},
                }

        result = tmp_store.cleanup()
        assert result["removed_age"] == 2   # old entries removed first
        assert result["removed_count"] == 1  # 6 remaining, trim to 5
        assert tmp_store.count == 5

    def test_batch_limit(self, tmp_store):
        """Cleanup respects max_batch limit."""
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        with tmp_store._lock:
            for i in range(100):
                tmp_store._entries[f"dlq-b{i}"] = {
                    "dlq_id": f"dlq-b{i}", "mission_id": f"b{i}",
                    "goal": "", "error": "", "failed_stage_id": "",
                    "failed_at": old_time, "status": "pending",
                    "retry_count": 0, "mission_snapshot": {},
                }

        result = tmp_store.cleanup(max_batch=10)
        assert result["removed_age"] == 10  # capped at batch limit
        assert tmp_store.count == 90

    def test_fifo_eviction_order(self, tmp_store):
        """Oldest entries are evicted first (FIFO)."""
        now = datetime.now(timezone.utc)
        with tmp_store._lock:
            for i in range(8):
                t = (now - timedelta(hours=8 - i)).isoformat()
                tmp_store._entries[f"dlq-f{i}"] = {
                    "dlq_id": f"dlq-f{i}", "mission_id": f"f{i}",
                    "goal": "", "error": "", "failed_stage_id": "",
                    "failed_at": t, "status": "pending",
                    "retry_count": 0, "mission_snapshot": {},
                }

        tmp_store.cleanup()
        # 3 oldest should be removed (f0, f1, f2)
        assert "dlq-f0" not in tmp_store._entries
        assert "dlq-f1" not in tmp_store._entries
        assert "dlq-f2" not in tmp_store._entries
        assert "dlq-f7" in tmp_store._entries  # newest survives

    def test_cleanup_on_enqueue(self, tmp_store):
        """Enqueue triggers bounded cleanup."""
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        with tmp_store._lock:
            for i in range(3):
                tmp_store._entries[f"dlq-old{i}"] = {
                    "dlq_id": f"dlq-old{i}", "mission_id": f"old{i}",
                    "goal": "", "error": "", "failed_stage_id": "",
                    "failed_at": old_time, "status": "pending",
                    "retry_count": 0, "mission_snapshot": {},
                }

        # Enqueue triggers cleanup
        tmp_store.enqueue(_make_mission("new-mission"))
        # Old entries should be cleaned up
        assert "dlq-old0" not in tmp_store._entries
        assert "dlq-new-mission" in tmp_store._entries

    def test_observability_output(self, tmp_store):
        """Cleanup returns timing and counters."""
        result = tmp_store.cleanup()
        assert "removed_age" in result
        assert "removed_count" in result
        assert "duration_ms" in result
        assert result["duration_ms"] >= 0
