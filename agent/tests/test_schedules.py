"""Tests for mission scheduling — D-120 / B-101 (Sprint 38)."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schedules.schema import (
    MissionSchedule,
    _parse_cron_field,
    _weekday_convert,
    cron_matches,
    next_cron_time,
    parse_cron,
)
from schedules.store import ScheduleStore


class TestCronParser(unittest.TestCase):
    """Test cron expression parsing."""

    def test_parse_wildcard(self):
        """Wildcard should expand to all values."""
        result = _parse_cron_field("*", 0, 59)
        self.assertEqual(result, set(range(0, 60)))

    def test_parse_single_value(self):
        """Single value should return single-element set."""
        result = _parse_cron_field("5", 0, 59)
        self.assertEqual(result, {5})

    def test_parse_range(self):
        """Range should expand to inclusive set."""
        result = _parse_cron_field("1-5", 0, 59)
        self.assertEqual(result, {1, 2, 3, 4, 5})

    def test_parse_list(self):
        """Comma-separated list should expand to set."""
        result = _parse_cron_field("1,3,5", 0, 59)
        self.assertEqual(result, {1, 3, 5})

    def test_parse_step(self):
        """Step expression should produce correct sequence."""
        result = _parse_cron_field("*/15", 0, 59)
        self.assertEqual(result, {0, 15, 30, 45})

    def test_parse_step_with_base(self):
        """Step with explicit base should start from base."""
        result = _parse_cron_field("5/10", 0, 59)
        self.assertEqual(result, {5, 15, 25, 35, 45, 55})

    def test_parse_full_expression(self):
        """Full 5-field cron expression should parse correctly."""
        result = parse_cron("0 9 * * 1-5")
        self.assertEqual(result["minute"], {0})
        self.assertEqual(result["hour"], {9})
        self.assertEqual(result["day_of_month"], set(range(1, 32)))
        self.assertEqual(result["month"], set(range(1, 13)))
        self.assertEqual(result["day_of_week"], {1, 2, 3, 4, 5})

    def test_parse_invalid_fields(self):
        """Wrong number of fields should raise ValueError."""
        with self.assertRaises(ValueError):
            parse_cron("0 9 *")

    def test_out_of_range_filtered(self):
        """Values outside valid range should be filtered."""
        result = _parse_cron_field("70", 0, 59)
        self.assertEqual(result, set())


class TestCronMatches(unittest.TestCase):
    """Test cron matching against datetime."""

    def test_every_minute(self):
        """* * * * * should match any time."""
        dt = datetime(2026, 3, 29, 10, 30, tzinfo=timezone.utc)
        self.assertTrue(cron_matches("* * * * *", dt))

    def test_specific_time(self):
        """Specific time should match correctly."""
        # 2026-03-29 is a Sunday
        dt = datetime(2026, 3, 29, 9, 0, tzinfo=timezone.utc)
        self.assertTrue(cron_matches("0 9 29 3 0", dt))  # 0=Sunday

    def test_weekday_only(self):
        """Monday-Friday cron should not match Sunday."""
        dt = datetime(2026, 3, 29, 9, 0, tzinfo=timezone.utc)  # Sunday
        self.assertFalse(cron_matches("0 9 * * 1-5", dt))

    def test_weekday_match(self):
        """Monday-Friday cron should match Monday."""
        dt = datetime(2026, 3, 30, 9, 0, tzinfo=timezone.utc)  # Monday
        self.assertTrue(cron_matches("0 9 * * 1-5", dt))

    def test_wrong_minute(self):
        """Wrong minute should not match."""
        dt = datetime(2026, 3, 30, 9, 15, tzinfo=timezone.utc)
        self.assertFalse(cron_matches("0 9 * * *", dt))


class TestWeekdayConvert(unittest.TestCase):
    """Test cron-to-Python weekday conversion."""

    def test_sunday(self):
        """Cron Sunday (0) = Python Sunday (6)."""
        self.assertEqual(_weekday_convert({0}), {6})

    def test_monday(self):
        """Cron Monday (1) = Python Monday (0)."""
        self.assertEqual(_weekday_convert({1}), {0})

    def test_weekdays(self):
        """Cron 1-5 = Python 0-4."""
        self.assertEqual(_weekday_convert({1, 2, 3, 4, 5}), {0, 1, 2, 3, 4})


class TestNextCronTime(unittest.TestCase):
    """Test next cron execution time calculation."""

    def test_next_hour(self):
        """Next hourly cron should be within 60 minutes."""
        now = datetime(2026, 3, 29, 10, 30, tzinfo=timezone.utc)
        result = next_cron_time("0 * * * *", now)
        self.assertEqual(result.hour, 11)
        self.assertEqual(result.minute, 0)

    def test_next_day(self):
        """If past today's time, next run should be tomorrow."""
        now = datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc)
        result = next_cron_time("0 9 * * *", now)
        self.assertEqual(result.day, 30)
        self.assertEqual(result.hour, 9)


class TestMissionSchedule(unittest.TestCase):
    """Test MissionSchedule dataclass."""

    def test_default_creation(self):
        """Schedule should have auto-generated ID and timestamps."""
        sched = MissionSchedule(name="Test", cron="0 9 * * *")
        self.assertTrue(sched.id.startswith("sched_"))
        self.assertTrue(sched.created_at)
        self.assertTrue(sched.enabled)

    def test_to_dict(self):
        """to_dict should include all fields."""
        sched = MissionSchedule(name="Test", cron="0 9 * * *", template_id="tmpl_abc")
        d = sched.to_dict()
        self.assertEqual(d["name"], "Test")
        self.assertEqual(d["cron"], "0 9 * * *")
        self.assertEqual(d["template_id"], "tmpl_abc")
        self.assertIn("id", d)
        self.assertIn("created_at", d)


class TestScheduleStore(unittest.TestCase):
    """Test schedule CRUD store."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = ScheduleStore(Path(self.tmpdir))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_and_get(self):
        """Create should persist and get should retrieve."""
        sched = self.store.create({
            "name": "Daily Report",
            "template_id": "tmpl_test",
            "cron": "0 9 * * 1-5",
        })
        self.assertTrue(sched.id.startswith("sched_"))
        retrieved = self.store.get(sched.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Daily Report")
        self.assertEqual(retrieved.cron, "0 9 * * 1-5")

    def test_list(self):
        """List should return all schedules."""
        self.store.create({"name": "A", "template_id": "t1", "cron": "0 9 * * *"})
        self.store.create({"name": "B", "template_id": "t2", "cron": "0 18 * * *"})
        result = self.store.list()
        self.assertEqual(len(result), 2)

    def test_list_enabled_only(self):
        """enabled_only filter should exclude disabled schedules."""
        self.store.create({"name": "Enabled", "template_id": "t1", "cron": "0 9 * * *", "enabled": True})
        self.store.create({"name": "Disabled", "template_id": "t2", "cron": "0 18 * * *", "enabled": False})
        result = self.store.list(enabled_only=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Enabled")

    def test_update(self):
        """Update should modify fields."""
        sched = self.store.create({"name": "Old", "template_id": "t1", "cron": "0 9 * * *"})
        updated = self.store.update(sched.id, {"name": "New", "cron": "30 10 * * *"})
        self.assertEqual(updated.name, "New")
        self.assertEqual(updated.cron, "30 10 * * *")

    def test_update_nonexistent(self):
        """Update on missing schedule should return None."""
        result = self.store.update("nonexistent", {"name": "X"})
        self.assertIsNone(result)

    def test_delete(self):
        """Delete should remove schedule file."""
        sched = self.store.create({"name": "To Delete", "template_id": "t1", "cron": "0 9 * * *"})
        self.assertTrue(self.store.delete(sched.id))
        self.assertIsNone(self.store.get(sched.id))

    def test_delete_nonexistent(self):
        """Delete on missing schedule should return False."""
        self.assertFalse(self.store.delete("nonexistent"))

    def test_record_run(self):
        """record_run should update last_run and increment count."""
        sched = self.store.create({"name": "Test", "template_id": "t1", "cron": "0 9 * * *"})
        self.assertEqual(sched.run_count, 0)
        updated = self.store.record_run(sched.id, "mission-123")
        self.assertEqual(updated.run_count, 1)
        self.assertEqual(updated.last_mission_id, "mission-123")
        self.assertIsNotNone(updated.last_run)

    def test_next_run_calculated_on_create(self):
        """next_run should be calculated on creation for enabled schedules."""
        sched = self.store.create({
            "name": "Test", "template_id": "t1",
            "cron": "0 9 * * *", "enabled": True,
        })
        self.assertIsNotNone(sched.next_run)

    def test_corrupt_file_handled(self):
        """Corrupt JSON files should be handled gracefully."""
        bad_path = Path(self.tmpdir) / "bad.json"
        bad_path.write_text("not json", encoding="utf-8")
        result = self.store.list()
        self.assertEqual(len(result), 0)


class TestScheduleAPI(unittest.TestCase):
    """Test schedule API endpoints via FastAPI TestClient."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("TESTING", "1")

    def _get_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.schedules_api import router
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api/v1")
        return TestClient(test_app)

    @patch("api.schedules_api._get_store")
    def test_list_schedules(self, mock_store_fn):
        mock_store = MagicMock()
        mock_store.list.return_value = [{"id": "sched_1", "name": "Test"}]
        mock_store_fn.return_value = mock_store

        client = self._get_client()
        resp = client.get("/api/v1/schedules")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("schedules", data)

    @patch("api.schedules_api._get_store")
    def test_get_schedule_not_found(self, mock_store_fn):
        mock_store = MagicMock()
        mock_store.get.return_value = None
        mock_store_fn.return_value = mock_store

        client = self._get_client()
        resp = client.get("/api/v1/schedules/nonexistent")
        self.assertEqual(resp.status_code, 404)

    @patch("api.schedules_api._get_store")
    def test_delete_schedule(self, mock_store_fn):
        mock_store = MagicMock()
        mock_store.delete.return_value = True
        mock_store_fn.return_value = mock_store

        client = self._get_client()
        resp = client.delete("/api/v1/schedules/sched_123")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["deleted"])


if __name__ == "__main__":
    unittest.main()
