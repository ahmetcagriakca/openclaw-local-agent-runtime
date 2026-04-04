"""Sprint 52 Task 52.2 — B-111 Mission Replay / Fixture Runner tests.

Tests for replay engine, fixture generation, and replay API.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OC_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(OC_ROOT / "tools"))

SAMPLE_MISSION = {
    "missionId": "mission-replay-test-001",
    "goal": "Test mission for replay",
    "userId": "test-user",
    "sessionId": "test-session",
    "status": "completed",
    "complexity": "standard",
    "risk_level": "low",
    "startedAt": "2026-04-04T10:00:00Z",
    "finishedAt": "2026-04-04T10:05:00Z",
    "currentStage": 2,
    "stages": [
        {
            "id": "stage-1",
            "specialist": "analyst",
            "description": "Analyze input",
            "status": "completed",
            "result": "Analysis complete: 3 items found",
            "tool_call_count": 2,
            "token_report": {"total_tokens": 150},
        },
        {
            "id": "stage-2",
            "specialist": "writer",
            "description": "Write report",
            "status": "completed",
            "result": "Report written successfully",
            "tool_call_count": 0,
            "token_report": {"total_tokens": 80},
        },
    ],
    "artifacts": [],
    "error": None,
}

SAMPLE_FAILED_MISSION = {
    "missionId": "mission-replay-test-002",
    "goal": "Failed mission for replay test",
    "userId": "test-user",
    "sessionId": "test-session",
    "status": "failed",
    "complexity": "complex",
    "risk_level": "high",
    "startedAt": "2026-04-04T11:00:00Z",
    "finishedAt": "2026-04-04T11:03:00Z",
    "currentStage": 2,
    "stages": [
        {
            "id": "stage-1",
            "specialist": "planner",
            "description": "Plan task",
            "status": "completed",
            "result": "Plan created",
            "tool_call_count": 1,
        },
        {
            "id": "stage-2",
            "specialist": "executor",
            "description": "Execute plan",
            "status": "failed",
            "result": None,
            "error": "Timeout",
            "tool_call_count": 3,
        },
    ],
    "artifacts": [],
    "error": "Stage 2 failed: Timeout",
}


class TestListMissions(unittest.TestCase):
    """Tests for list_completed_missions."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_empty_dir(self):
        """Empty directory returns empty list."""
        from replay import list_completed_missions
        result = list_completed_missions(self.temp_dir)
        self.assertEqual(result, [])

    def test_02_lists_completed_missions(self):
        """Completed missions are listed."""
        from replay import list_completed_missions
        (self.temp_dir / "mission-001.json").write_text(
            json.dumps(SAMPLE_MISSION), encoding="utf-8")
        result = list_completed_missions(self.temp_dir)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["missionId"], "mission-replay-test-001")

    def test_03_lists_failed_missions(self):
        """Failed missions are listed."""
        from replay import list_completed_missions
        (self.temp_dir / "mission-002.json").write_text(
            json.dumps(SAMPLE_FAILED_MISSION), encoding="utf-8")
        result = list_completed_missions(self.temp_dir)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "failed")

    def test_04_skips_running_missions(self):
        """Running missions are not listed."""
        from replay import list_completed_missions
        running = dict(SAMPLE_MISSION, status="running",
                       missionId="mission-running")
        (self.temp_dir / "mission-003.json").write_text(
            json.dumps(running), encoding="utf-8")
        result = list_completed_missions(self.temp_dir)
        self.assertEqual(len(result), 0)

    def test_05_respects_limit(self):
        """Limit parameter is respected."""
        from replay import list_completed_missions
        for i in range(5):
            m = dict(SAMPLE_MISSION, missionId=f"mission-{i}")
            (self.temp_dir / f"mission-{i:03d}.json").write_text(
                json.dumps(m), encoding="utf-8")
        result = list_completed_missions(self.temp_dir, limit=3)
        self.assertEqual(len(result), 3)


class TestLoadMission(unittest.TestCase):
    """Tests for load_mission."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_load_by_filename(self):
        """Load mission by direct filename."""
        from replay import load_mission
        (self.temp_dir / "mission-replay-test-001.json").write_text(
            json.dumps(SAMPLE_MISSION), encoding="utf-8")
        result = load_mission("mission-replay-test-001", self.temp_dir)
        self.assertIsNotNone(result)
        self.assertEqual(result["goal"], "Test mission for replay")

    def test_02_load_not_found(self):
        """Returns None for missing mission."""
        from replay import load_mission
        result = load_mission("nonexistent", self.temp_dir)
        self.assertIsNone(result)

    def test_03_load_by_mission_id_field(self):
        """Load mission by missionId field search."""
        from replay import load_mission
        (self.temp_dir / "mission-some-file.json").write_text(
            json.dumps(SAMPLE_MISSION), encoding="utf-8")
        result = load_mission("mission-replay-test-001", self.temp_dir)
        self.assertIsNotNone(result)


class TestReplayMission(unittest.TestCase):
    """Tests for replay_mission."""

    def test_01_replay_completed_mission(self):
        """Replay of completed mission returns valid report."""
        from replay import replay_mission
        report = replay_mission(SAMPLE_MISSION)
        self.assertEqual(report["missionId"], "mission-replay-test-001")
        self.assertEqual(report["stageCount"], 2)
        self.assertTrue(report["valid"])
        self.assertEqual(len(report["issues"]), 0)

    def test_02_replay_detects_empty_result(self):
        """Replay flags completed stage with no result."""
        from replay import replay_mission
        mission = json.loads(json.dumps(SAMPLE_MISSION))
        mission["stages"][0]["result"] = ""
        report = replay_mission(mission)
        self.assertFalse(report["valid"])
        self.assertTrue(any(i["issue"] == "completed_without_result"
                            for i in report["issues"]))

    def test_03_replay_detects_missing_specialist(self):
        """Replay flags stage with no specialist."""
        from replay import replay_mission
        mission = json.loads(json.dumps(SAMPLE_MISSION))
        mission["stages"][1]["specialist"] = ""
        report = replay_mission(mission)
        self.assertFalse(report["valid"])

    def test_04_replay_failed_mission(self):
        """Replay of failed mission works correctly."""
        from replay import replay_mission
        report = replay_mission(SAMPLE_FAILED_MISSION)
        self.assertEqual(report["originalStatus"], "failed")
        self.assertEqual(report["stageCount"], 2)


class TestGenerateFixture(unittest.TestCase):
    """Tests for fixture generation."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_fixture_structure(self):
        """Generated fixture has correct structure."""
        from replay import generate_fixture
        fixture = generate_fixture(SAMPLE_MISSION)
        self.assertIn("_fixture", fixture)
        self.assertIn("missionId", fixture)
        self.assertIn("stages", fixture)
        self.assertTrue(fixture["missionId"].startswith("fixture-"))

    def test_02_fixture_strips_sensitive(self):
        """Fixture does not contain userId or sessionId."""
        from replay import generate_fixture
        fixture = generate_fixture(SAMPLE_MISSION)
        self.assertNotIn("userId", fixture)
        self.assertNotIn("sessionId", fixture)

    def test_03_fixture_write_to_file(self):
        """Fixture can be written to file."""
        from replay import generate_fixture
        out = self.temp_dir / "test_fixture.json"
        generate_fixture(SAMPLE_MISSION, output_path=out)
        self.assertTrue(out.exists())
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertIn("_fixture", data)

    def test_04_fixture_preserves_stages(self):
        """Fixture preserves stage count and structure."""
        from replay import generate_fixture
        fixture = generate_fixture(SAMPLE_MISSION)
        self.assertEqual(len(fixture["stages"]), 2)
        self.assertEqual(fixture["stages"][0]["specialist"], "analyst")


class TestReplayAPI(unittest.TestCase):
    """Tests for replay API endpoints."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from api.server import app
        cls.client = TestClient(app)

    def test_01_list_endpoint(self):
        """GET /api/v1/missions/replay/list returns mission list."""
        resp = self.client.get("/api/v1/missions/replay/list")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("missions", data)
        self.assertIn("count", data)

    def test_02_replay_not_found(self):
        """GET /api/v1/missions/replay/<missing> returns 404."""
        resp = self.client.get("/api/v1/missions/replay/nonexistent-id")
        self.assertEqual(resp.status_code, 404)

    def test_03_fixture_not_found(self):
        """GET /api/v1/missions/replay/<missing>/fixture returns 404."""
        resp = self.client.get(
            "/api/v1/missions/replay/nonexistent-id/fixture")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
