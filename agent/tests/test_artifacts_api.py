"""Sprint 51 Task 51.3 — B-016 Task Result Artifact Access tests.

Tests for artifact listing and access API endpoints.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from api.server import app

# Sample mission data for testing
SAMPLE_MISSION = {
    "missionId": "test-mission-artifact-001",
    "goal": "Test artifact access",
    "status": "completed",
    "startedAt": "2026-04-04T10:00:00Z",
    "finishedAt": "2026-04-04T10:05:00Z",
    "stages": [
        {
            "stage_id": "stage-0",
            "specialist": "researcher",
            "status": "completed",
            "result": "Research findings: the system is working correctly.",
            "artifacts": [
                {"type": "analysis", "content": "detailed analysis data"},
            ],
            "finished_at": "2026-04-04T10:02:00Z",
        },
        {
            "stage_id": "stage-1",
            "specialist": "developer",
            "status": "completed",
            "result": "Code implementation complete.",
            "artifacts": [],
            "finished_at": "2026-04-04T10:04:00Z",
        },
    ],
    "artifacts": [
        {"type": "summary", "content": "Mission completed successfully"},
    ],
    "completedArtifactIds": ["art-1", "art-2"],
}


class TestArtifactsExtraction(unittest.TestCase):
    """Tests for artifact extraction logic."""

    def test_01_extract_stage_results(self):
        """_extract_artifacts extracts stage results."""
        from api.artifacts_api import _extract_artifacts
        artifacts = _extract_artifacts(SAMPLE_MISSION)
        stage_results = [a for a in artifacts if a["type"] == "stage_result"]
        self.assertEqual(len(stage_results), 2)

    def test_02_extract_raw_artifacts(self):
        """_extract_artifacts extracts raw stage artifacts."""
        from api.artifacts_api import _extract_artifacts
        artifacts = _extract_artifacts(SAMPLE_MISSION)
        raw = [a for a in artifacts if a["type"] == "raw_artifact"]
        self.assertEqual(len(raw), 1)

    def test_03_extract_mission_artifacts(self):
        """_extract_artifacts extracts top-level mission artifacts."""
        from api.artifacts_api import _extract_artifacts
        artifacts = _extract_artifacts(SAMPLE_MISSION)
        mission = [a for a in artifacts if a["type"] == "mission_artifact"]
        self.assertEqual(len(mission), 1)

    def test_04_artifact_ids_are_unique(self):
        """All extracted artifact IDs are unique."""
        from api.artifacts_api import _extract_artifacts
        artifacts = _extract_artifacts(SAMPLE_MISSION)
        ids = [a["id"] for a in artifacts]
        self.assertEqual(len(ids), len(set(ids)))

    def test_05_artifact_has_required_fields(self):
        """Each artifact has required fields."""
        from api.artifacts_api import _extract_artifacts
        artifacts = _extract_artifacts(SAMPLE_MISSION)
        required = {"id", "type", "stage_id", "role", "size", "created_at"}
        for a in artifacts:
            for field in required:
                self.assertIn(field, a, f"Missing field '{field}' in artifact {a['id']}")

    def test_06_stage_result_has_preview(self):
        """Stage result artifacts include preview."""
        from api.artifacts_api import _extract_artifacts
        artifacts = _extract_artifacts(SAMPLE_MISSION)
        stage_results = [a for a in artifacts if a["type"] == "stage_result"]
        for sr in stage_results:
            self.assertIn("preview", sr)
            self.assertTrue(len(sr["preview"]) <= 200)

    def test_07_empty_mission_returns_empty(self):
        """Empty mission returns no artifacts."""
        from api.artifacts_api import _extract_artifacts
        empty = {"stages": [], "artifacts": []}
        artifacts = _extract_artifacts(empty)
        self.assertEqual(len(artifacts), 0)

    def test_08_size_is_positive(self):
        """Artifact size is non-negative."""
        from api.artifacts_api import _extract_artifacts
        artifacts = _extract_artifacts(SAMPLE_MISSION)
        for a in artifacts:
            self.assertGreaterEqual(a["size"], 0)


class TestArtifactsAPI(unittest.TestCase):
    """Tests for artifact API endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Write sample mission to temp file for API to find
        cls.temp_dir = tempfile.mkdtemp()
        cls.mission_file = Path(cls.temp_dir) / "test-mission.json"
        cls.mission_file.write_text(
            json.dumps(SAMPLE_MISSION, indent=2),
            encoding="utf-8",
        )

    def test_09_list_artifacts_not_found(self):
        """GET /missions/{id}/artifacts returns 404 for unknown mission."""
        resp = self.client.get(
            "/api/v1/missions/nonexistent-mission-xyz/artifacts")
        self.assertEqual(resp.status_code, 404)

    def test_10_get_artifact_not_found(self):
        """GET /missions/{id}/artifacts/{aid} returns 404 for unknown mission."""
        resp = self.client.get(
            "/api/v1/missions/nonexistent-mission-xyz/artifacts/fake-art")
        self.assertEqual(resp.status_code, 404)

    def test_11_list_artifacts_shape(self):
        """GET /missions/{id}/artifacts returns expected shape when mission exists."""
        with patch("api.artifacts_api._load_mission", return_value=SAMPLE_MISSION):
            resp = self.client.get(
                "/api/v1/missions/test-mission-artifact-001/artifacts")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("meta", data)
            self.assertIn("artifacts", data)
            self.assertIn("count", data)
            self.assertIn("mission_id", data)
            self.assertIsInstance(data["artifacts"], list)
            self.assertGreater(data["count"], 0)

    def test_12_get_artifact_detail(self):
        """GET /missions/{id}/artifacts/{aid} returns full artifact."""
        with patch("api.artifacts_api._load_mission", return_value=SAMPLE_MISSION):
            resp = self.client.get(
                "/api/v1/missions/test-mission-artifact-001/artifacts/stage-0-result")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("meta", data)
            self.assertIn("artifact", data)
            self.assertEqual(data["artifact"]["id"], "stage-0-result")
            self.assertEqual(data["artifact"]["type"], "stage_result")

    def test_13_get_artifact_not_found_in_mission(self):
        """GET returns 404 when artifact ID doesn't exist in mission."""
        with patch("api.artifacts_api._load_mission", return_value=SAMPLE_MISSION):
            resp = self.client.get(
                "/api/v1/missions/test-mission-artifact-001/artifacts/nonexistent-art")
            self.assertEqual(resp.status_code, 404)

    def test_14_list_artifacts_no_preview_leaks(self):
        """List endpoint doesn't include full data, only preview."""
        with patch("api.artifacts_api._load_mission", return_value=SAMPLE_MISSION):
            resp = self.client.get(
                "/api/v1/missions/test-mission-artifact-001/artifacts")
            data = resp.json()
            for a in data["artifacts"]:
                self.assertNotIn("data", a,
                                 "List endpoint should not include full data")


if __name__ == "__main__":
    unittest.main()
