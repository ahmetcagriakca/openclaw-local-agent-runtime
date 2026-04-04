"""Sprint 52 Task 52.1 — B-023 Corrupted Runtime Recovery tests.

Tests for corruption scanner, repair, quarantine, and recovery API.
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


class TestCorruptionScanner(unittest.TestCase):
    """Tests for tools/recovery.py scan functions."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write(self, name: str, content: str):
        path = self.temp_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def _write_json(self, name: str, data: dict):
        path = self.temp_dir / name
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def test_01_clean_dir_no_issues(self):
        """No issues in a directory with valid mission files."""
        from recovery import scan_missions
        self._write_json("mission-001.json", {
            "missionId": "m-001", "status": "completed", "stages": []
        })
        issues = scan_missions(self.temp_dir)
        self.assertEqual(len(issues), 0)

    def test_02_empty_file_detected(self):
        """Empty file is detected as corruption."""
        from recovery import scan_missions
        self._write("mission-002.json", "")
        issues = scan_missions(self.temp_dir)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "empty_file")

    def test_03_invalid_json_detected(self):
        """Invalid JSON is detected."""
        from recovery import scan_missions
        self._write("mission-003.json", '{"missionId": "m-003", "status": ')
        issues = scan_missions(self.temp_dir)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "invalid_json")

    def test_04_truncated_json_repairable(self):
        """Truncated JSON is flagged as repairable."""
        from recovery import scan_missions
        self._write("mission-004.json",
                     '{"missionId": "m-004", "status": "completed"')
        issues = scan_missions(self.temp_dir)
        self.assertEqual(len(issues), 1)
        self.assertTrue(issues[0].repairable)

    def test_05_missing_fields_detected(self):
        """Missing required fields detected."""
        from recovery import scan_missions
        self._write_json("mission-005.json", {"stages": []})
        issues = scan_missions(self.temp_dir)
        self.assertTrue(any(i.issue_type == "missing_fields" for i in issues))

    def test_06_invalid_status_detected(self):
        """Invalid status value detected."""
        from recovery import scan_missions
        self._write_json("mission-006.json", {
            "missionId": "m-006", "status": "bogus_status", "stages": []
        })
        issues = scan_missions(self.temp_dir)
        self.assertTrue(any(i.issue_type == "invalid_status" for i in issues))

    def test_07_orphaned_aux_detected(self):
        """Orphaned auxiliary file without parent is detected."""
        from recovery import scan_missions
        self._write_json("mission-007-state.json", {"state": "data"})
        issues = scan_missions(self.temp_dir)
        self.assertTrue(any(i.issue_type == "orphaned_aux" for i in issues))

    def test_08_valid_aux_not_flagged(self):
        """Auxiliary file with parent is not flagged."""
        from recovery import scan_missions
        self._write_json("mission-008.json", {
            "missionId": "m-008", "status": "completed", "stages": []
        })
        self._write_json("mission-008-state.json", {"state": "data"})
        issues = scan_missions(self.temp_dir)
        self.assertEqual(len(issues), 0)

    def test_09_not_object_detected(self):
        """Root value that's not an object is detected."""
        from recovery import scan_missions
        self._write("mission-009.json", '["array", "not", "object"]')
        issues = scan_missions(self.temp_dir)
        self.assertTrue(any(i.issue_type == "not_object" for i in issues))


class TestRepairTruncated(unittest.TestCase):
    """Tests for truncated JSON repair."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_repair_missing_closing_brace(self):
        """Repair JSON with missing closing brace."""
        from recovery import repair_truncated
        path = self.temp_dir / "mission-r1.json"
        path.write_text('{"missionId": "m-r1", "status": "completed"',
                        encoding="utf-8")
        result = repair_truncated(path)
        self.assertTrue(result)
        # Verify repaired file is valid JSON
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["missionId"], "m-r1")

    def test_02_repair_nested_missing_braces(self):
        """Repair nested JSON with multiple missing closers."""
        from recovery import repair_truncated
        path = self.temp_dir / "mission-r2.json"
        path.write_text('{"missionId": "m-r2", "stages": [{"id": "s1"',
                        encoding="utf-8")
        result = repair_truncated(path)
        self.assertTrue(result)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["missionId"], "m-r2")

    def test_03_already_valid_no_repair(self):
        """Valid JSON returns False (no repair needed)."""
        from recovery import repair_truncated
        path = self.temp_dir / "mission-r3.json"
        path.write_text('{"missionId": "m-r3"}', encoding="utf-8")
        result = repair_truncated(path)
        self.assertFalse(result)


class TestQuarantine(unittest.TestCase):
    """Tests for quarantine functionality."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.quarantine_dir = self.temp_dir / "quarantine"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_quarantine_moves_file(self):
        """Quarantine moves file to quarantine directory."""
        from recovery import quarantine_file
        path = self.temp_dir / "bad.json"
        path.write_text("invalid", encoding="utf-8")
        dest = quarantine_file(path, self.quarantine_dir)
        self.assertFalse(path.exists())
        self.assertTrue(dest.exists())
        self.assertTrue(dest.parent == self.quarantine_dir)

    def test_02_quarantine_creates_dir(self):
        """Quarantine creates quarantine directory if missing."""
        from recovery import quarantine_file
        path = self.temp_dir / "bad2.json"
        path.write_text("invalid", encoding="utf-8")
        quarantine_file(path, self.quarantine_dir)
        self.assertTrue(self.quarantine_dir.exists())


class TestRecoveryAPI(unittest.TestCase):
    """Tests for recovery API endpoints."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from api.server import app
        cls.client = TestClient(app)

    def test_01_scan_endpoint(self):
        """GET /api/v1/admin/recovery/scan returns issue list."""
        resp = self.client.get("/api/v1/admin/recovery/scan")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("issues", data)
        self.assertIn("count", data)
        self.assertIn("repairable", data)
        self.assertIn("meta", data)


if __name__ == "__main__":
    unittest.main()
