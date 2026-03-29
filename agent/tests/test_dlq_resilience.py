"""Tests for DLQ, exponential backoff, circuit breaker, and auto-resume — B-106."""
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mission.resilience import (
    CircuitBreaker,
    _error_hash,
    backoff_delay,
    is_poison_pill,
)
from persistence.dlq_store import DLQEntry, DLQStore

# ── DLQ Store Tests ──────────────────────────────────────────────

class TestDLQEntry(unittest.TestCase):
    """Test DLQEntry serialization."""

    def test_round_trip(self):
        entry = DLQEntry(
            dlq_id="dlq-mission-1",
            mission_id="mission-1",
            goal="test mission",
            error="stage failed",
            failed_stage_id="stage-2",
            failed_at="2026-03-29T10:00:00+00:00",
        )
        d = entry.to_dict()
        restored = DLQEntry.from_dict(d)
        self.assertEqual(restored.dlq_id, "dlq-mission-1")
        self.assertEqual(restored.mission_id, "mission-1")
        self.assertEqual(restored.status, "pending")
        self.assertEqual(restored.retry_count, 0)

    def test_defaults(self):
        entry = DLQEntry(
            dlq_id="dlq-1", mission_id="m-1",
            goal="", error="", failed_stage_id="",
            failed_at="2026-01-01T00:00:00Z")
        self.assertEqual(entry.status, "pending")
        self.assertEqual(entry.retry_count, 0)
        self.assertIsNone(entry.last_retry_at)
        self.assertEqual(entry.mission_snapshot, {})


class TestDLQStore(unittest.TestCase):
    """Test DLQStore CRUD operations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store_path = Path(self.tmpdir) / "dlq.json"
        self.store = DLQStore(store_path=self.store_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_mission(self, mid="mission-1", goal="test", error="failed"):
        return {
            "missionId": mid,
            "goal": goal,
            "error": error,
            "stages": [
                {"id": "stage-1", "status": "completed"},
                {"id": "stage-2", "status": "failed"},
            ],
        }

    def test_enqueue_and_get(self):
        mission = self._make_mission()
        dlq_id = self.store.enqueue(mission, failed_stage_id="stage-2",
                                     error="stage failed")
        self.assertEqual(dlq_id, "dlq-mission-1")
        entry = self.store.get(dlq_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["mission_id"], "mission-1")
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["failed_stage_id"], "stage-2")

    def test_list_empty(self):
        entries, total = self.store.list()
        self.assertEqual(entries, [])
        self.assertEqual(total, 0)

    def test_list_with_filter(self):
        self.store.enqueue(self._make_mission("m-1"), error="err1")
        self.store.enqueue(self._make_mission("m-2"), error="err2")
        self.store.mark_resolved("dlq-m-1")

        pending, total_p = self.store.list(status="pending")
        self.assertEqual(total_p, 1)
        self.assertEqual(pending[0]["mission_id"], "m-2")

        resolved, total_r = self.store.list(status="resolved")
        self.assertEqual(total_r, 1)

    def test_mark_retrying(self):
        self.store.enqueue(self._make_mission(), error="err")
        self.assertTrue(self.store.mark_retrying("dlq-mission-1"))
        entry = self.store.get("dlq-mission-1")
        self.assertEqual(entry["status"], "retrying")
        self.assertEqual(entry["retry_count"], 1)
        self.assertIsNotNone(entry["last_retry_at"])

    def test_mark_retrying_not_found(self):
        self.assertFalse(self.store.mark_retrying("nonexistent"))

    def test_mark_resolved(self):
        self.store.enqueue(self._make_mission(), error="err")
        self.assertTrue(self.store.mark_resolved("dlq-mission-1"))
        entry = self.store.get("dlq-mission-1")
        self.assertEqual(entry["status"], "resolved")

    def test_mark_pending(self):
        self.store.enqueue(self._make_mission(), error="err")
        self.store.mark_retrying("dlq-mission-1")
        self.assertTrue(self.store.mark_pending("dlq-mission-1"))
        entry = self.store.get("dlq-mission-1")
        self.assertEqual(entry["status"], "pending")

    def test_purge(self):
        self.store.enqueue(self._make_mission(), error="err")
        self.assertTrue(self.store.purge("dlq-mission-1"))
        self.assertIsNone(self.store.get("dlq-mission-1"))
        self.assertEqual(self.store.count, 0)

    def test_purge_not_found(self):
        self.assertFalse(self.store.purge("nonexistent"))

    def test_purge_resolved(self):
        self.store.enqueue(self._make_mission("m-1"), error="err1")
        self.store.enqueue(self._make_mission("m-2"), error="err2")
        self.store.mark_resolved("dlq-m-1")
        count = self.store.purge_resolved()
        self.assertEqual(count, 1)
        self.assertEqual(self.store.count, 1)
        self.assertIsNone(self.store.get("dlq-m-1"))
        self.assertIsNotNone(self.store.get("dlq-m-2"))

    def test_summary(self):
        self.store.enqueue(self._make_mission("m-1"), error="err1")
        self.store.enqueue(self._make_mission("m-2"), error="err2")
        self.store.mark_retrying("dlq-m-1")
        summary = self.store.summary()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["pending"], 1)
        self.assertEqual(summary["retrying"], 1)
        self.assertEqual(summary["resolved"], 0)

    def test_persistence_across_loads(self):
        """Store should survive reload from disk."""
        self.store.enqueue(self._make_mission(), error="err")
        # Create new store instance from same file
        store2 = DLQStore(store_path=self.store_path)
        entry = store2.get("dlq-mission-1")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["mission_id"], "mission-1")

    def test_count(self):
        self.assertEqual(self.store.count, 0)
        self.store.enqueue(self._make_mission("m-1"), error="err")
        self.assertEqual(self.store.count, 1)
        self.store.enqueue(self._make_mission("m-2"), error="err")
        self.assertEqual(self.store.count, 2)

    def test_list_pagination(self):
        for i in range(5):
            self.store.enqueue(self._make_mission(f"m-{i}"), error=f"err{i}")
        entries, total = self.store.list(limit=2, offset=0)
        self.assertEqual(total, 5)
        self.assertEqual(len(entries), 2)


# ── Backoff Tests ────────────────────────────────────────────────

class TestBackoffDelay(unittest.TestCase):
    """Test exponential backoff calculation."""

    def test_attempt_zero(self):
        self.assertEqual(backoff_delay(0), 0.0)

    def test_attempt_one(self):
        self.assertAlmostEqual(backoff_delay(1), 0.5)

    def test_attempt_two(self):
        self.assertAlmostEqual(backoff_delay(2), 1.0)

    def test_attempt_three(self):
        self.assertAlmostEqual(backoff_delay(3), 2.0)

    def test_max_cap(self):
        """Should not exceed BACKOFF_MAX_S."""
        delay = backoff_delay(100)
        self.assertLessEqual(delay, 30.0)

    def test_increasing(self):
        """Delays should be monotonically increasing up to cap."""
        delays = [backoff_delay(i) for i in range(1, 8)]
        for i in range(len(delays) - 1):
            self.assertLessEqual(delays[i], delays[i + 1])


# ── Circuit Breaker Tests ────────────────────────────────────────

class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker logic."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        self.assertFalse(cb.is_open("analyst"))

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("analyst", "error 1")
        self.assertFalse(cb.is_open("analyst"))
        cb.record_failure("analyst", "error 2")
        self.assertFalse(cb.is_open("analyst"))
        opened = cb.record_failure("analyst", "error 3")
        self.assertTrue(opened)
        self.assertTrue(cb.is_open("analyst"))

    def test_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("developer", "err")
        cb.record_failure("developer", "err")
        self.assertTrue(cb.is_open("developer"))
        cb.record_success("developer")
        self.assertFalse(cb.is_open("developer"))

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout_s=0.1)
        cb.record_failure("tester", "err")
        self.assertTrue(cb.is_open("tester"))
        time.sleep(0.15)
        self.assertFalse(cb.is_open("tester"))  # Half-open

    def test_independent_circuits(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("analyst", "err")
        cb.record_failure("analyst", "err")
        self.assertTrue(cb.is_open("analyst"))
        self.assertFalse(cb.is_open("developer"))

    def test_get_state(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("analyst", "err")
        state = cb.get_state("analyst")
        self.assertEqual(state["failure_count"], 1)
        self.assertFalse(state["open"])

    def test_all_states(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("analyst", "err")
        cb.record_failure("developer", "err")
        states = cb.all_states()
        self.assertEqual(len(states), 2)

    def test_manual_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure("analyst", "err")
        self.assertTrue(cb.is_open("analyst"))
        cb.reset("analyst")
        self.assertFalse(cb.is_open("analyst"))

    def test_reset_all(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure("analyst", "err")
        cb.record_failure("developer", "err")
        cb.reset_all()
        self.assertFalse(cb.is_open("analyst"))
        self.assertFalse(cb.is_open("developer"))


# ── Poison Pill Tests ────────────────────────────────────────────

class TestPoisonPill(unittest.TestCase):
    """Test poison pill detection."""

    def test_no_poison_on_first_failure(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure("analyst", "connection refused")
        self.assertFalse(is_poison_pill("analyst", "connection refused", cb))

    def test_poison_detected_on_repeated_same_error(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure("analyst", "connection refused")
        cb.record_failure("analyst", "connection refused")
        self.assertTrue(is_poison_pill("analyst", "connection refused", cb))

    def test_no_poison_on_different_errors(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure("analyst", "connection refused")
        cb.record_failure("analyst", "timeout error")
        self.assertFalse(is_poison_pill("analyst", "new error type", cb))

    def test_error_hash_deterministic(self):
        h1 = _error_hash("connection refused")
        h2 = _error_hash("connection refused")
        self.assertEqual(h1, h2)

    def test_error_hash_different_errors(self):
        h1 = _error_hash("connection refused")
        h2 = _error_hash("timeout error")
        self.assertNotEqual(h1, h2)


# ── Auto-Resume Tests ───────────────────────────────────────────

class TestAutoResume(unittest.TestCase):
    """Test auto-resume scanning."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.missions_dir = Path(self.tmpdir) / "missions"
        self.missions_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_mission(self, mid, status, stages=None):
        full_id = f"mission-{mid}"
        data = {
            "missionId": full_id,
            "goal": f"test {mid}",
            "status": status,
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "stages": stages or [{"id": "stage-1", "status": "completed"}],
        }
        path = self.missions_dir / f"{full_id}.json"
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_find_incomplete(self):
        import mission.auto_resume as ar
        original_dir = ar.MISSIONS_DIR
        ar.MISSIONS_DIR = self.missions_dir

        try:
            self._write_mission("m-1", "completed")
            self._write_mission("m-2", "failed")
            self._write_mission("m-3", "running")

            result = ar.find_incomplete_missions()
            ids = [m["missionId"] for m in result]
            self.assertIn("mission-m-2", ids)
            self.assertIn("mission-m-3", ids)
            self.assertNotIn("mission-m-1", ids)
        finally:
            ar.MISSIONS_DIR = original_dir

    def test_find_no_stages_excluded(self):
        """Missions without stages should not be resumable."""
        # Use completely fresh temp dir to avoid any leakage
        import shutil
        fresh_dir = Path(tempfile.mkdtemp()) / "missions"
        fresh_dir.mkdir()

        import mission.auto_resume as ar
        original_dir = ar.MISSIONS_DIR
        ar.MISSIONS_DIR = fresh_dir

        try:
            full_id = "mission-nostages"
            data = {
                "missionId": full_id,
                "goal": "test",
                "status": "failed",
                "startedAt": datetime.now(timezone.utc).isoformat(),
                "stages": [],
            }
            (fresh_dir / f"{full_id}.json").write_text(
                json.dumps(data), encoding="utf-8")
            result = ar.find_incomplete_missions()
            self.assertEqual(len(result), 0)
        finally:
            ar.MISSIONS_DIR = original_dir
            shutil.rmtree(fresh_dir.parent, ignore_errors=True)


# ── DLQ API Tests ────────────────────────────────────────────────

class TestDLQAPI(unittest.TestCase):
    """Test DLQ API endpoints."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store_path = Path(self.tmpdir) / "dlq.json"
        self.store = DLQStore(store_path=self.store_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("api.dlq_api.get_dlq_store")
    def test_list_empty(self, mock_get_store):
        from fastapi.testclient import TestClient
        mock_get_store.return_value = self.store
        from fastapi import FastAPI

        from api.dlq_api import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        resp = client.get("/api/v1/dlq")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["entries"], [])
        self.assertEqual(data["total"], 0)

    @patch("api.dlq_api.get_dlq_store")
    def test_summary(self, mock_get_store):
        from fastapi.testclient import TestClient
        mock_get_store.return_value = self.store
        from fastapi import FastAPI

        from api.dlq_api import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        self.store.enqueue({"missionId": "m-1", "goal": "test",
                            "error": "err"}, error="err")

        resp = client.get("/api/v1/dlq/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["pending"], 1)

    @patch("api.dlq_api.get_dlq_store")
    def test_get_entry(self, mock_get_store):
        from fastapi.testclient import TestClient
        mock_get_store.return_value = self.store
        from fastapi import FastAPI

        from api.dlq_api import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        self.store.enqueue({"missionId": "m-1", "goal": "test"}, error="err")

        resp = client.get("/api/v1/dlq/dlq-m-1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["mission_id"], "m-1")

    @patch("api.dlq_api.get_dlq_store")
    def test_get_not_found(self, mock_get_store):
        from fastapi.testclient import TestClient
        mock_get_store.return_value = self.store
        from fastapi import FastAPI

        from api.dlq_api import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        resp = client.get("/api/v1/dlq/nonexistent")
        self.assertEqual(resp.status_code, 404)

    @patch("api.dlq_api.get_dlq_store")
    def test_purge_entry(self, mock_get_store):
        from fastapi.testclient import TestClient
        mock_get_store.return_value = self.store
        from fastapi import FastAPI

        from api.dlq_api import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        self.store.enqueue({"missionId": "m-1", "goal": "test"}, error="err")
        resp = client.delete("/api/v1/dlq/dlq-m-1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.store.count, 0)

    @patch("api.dlq_api.get_dlq_store")
    def test_purge_resolved(self, mock_get_store):
        from fastapi.testclient import TestClient
        mock_get_store.return_value = self.store
        from fastapi import FastAPI

        from api.dlq_api import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        client = TestClient(app)

        self.store.enqueue({"missionId": "m-1"}, error="err")
        self.store.enqueue({"missionId": "m-2"}, error="err")
        self.store.mark_resolved("dlq-m-1")

        resp = client.post("/api/v1/dlq/purge-resolved")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["purged"], 1)
        self.assertEqual(self.store.count, 1)


# ── Controller Integration Tests ─────────────────────────────────

class TestControllerDLQIntegration(unittest.TestCase):
    """Test that MissionController enqueues to DLQ on failure."""

    def test_enqueue_to_dlq_helper(self):
        """Test _enqueue_to_dlq method directly."""
        tmpdir = tempfile.mkdtemp()
        try:
            store = DLQStore(store_path=Path(tmpdir) / "dlq.json")
            # Create a minimal controller mock
            from mission.controller import MissionController
            with patch.object(MissionController, "__init__", lambda self, **kw: None):
                ctrl = MissionController.__new__(MissionController)
                ctrl._dlq_store = store

                mission = {
                    "missionId": "mission-test-1",
                    "goal": "test goal",
                    "error": "stage-2 failed: timeout",
                    "stages": [
                        {"id": "stage-1", "status": "completed"},
                        {"id": "stage-2", "status": "failed"},
                    ],
                }
                dlq_id = ctrl._enqueue_to_dlq(mission)
                self.assertEqual(dlq_id, "dlq-mission-test-1")

                entry = store.get(dlq_id)
                self.assertIsNotNone(entry)
                self.assertEqual(entry["failed_stage_id"], "stage-2")
                self.assertEqual(entry["error"], "stage-2 failed: timeout")
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
