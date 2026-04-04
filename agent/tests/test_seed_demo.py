"""Sprint 52 Task 52.3 — B-112 Local Dev Sandbox / Seeded Demo tests.

Tests for seed_demo tool: seeding, cleaning, and status.
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


class TestSeedMissions(unittest.TestCase):
    """Tests for mission seeding."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_seed_creates_files(self):
        """Seed creates mission files in target directory."""
        from seed_demo import seed_missions
        count = seed_missions(self.temp_dir)
        self.assertGreater(count, 0)
        files = list(self.temp_dir.glob("demo-mission-*.json"))
        self.assertEqual(len(files), count)

    def test_02_seeded_files_valid_json(self):
        """All seeded files are valid JSON."""
        from seed_demo import seed_missions
        seed_missions(self.temp_dir)
        for f in self.temp_dir.glob("demo-mission-*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            self.assertIn("missionId", data)
            self.assertIn("status", data)
            self.assertIn("stages", data)

    def test_03_seeded_files_have_marker(self):
        """All seeded files have the demo marker."""
        from seed_demo import SEED_MARKER, seed_missions
        seed_missions(self.temp_dir)
        for f in self.temp_dir.glob("demo-mission-*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            self.assertTrue(data.get(SEED_MARKER))

    def test_04_seeded_missions_diverse_status(self):
        """Seeded missions include both completed and failed."""
        from seed_demo import seed_missions
        seed_missions(self.temp_dir)
        statuses = set()
        for f in self.temp_dir.glob("demo-mission-*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            statuses.add(data["status"])
        self.assertIn("completed", statuses)
        self.assertIn("failed", statuses)

    def test_05_seeded_missions_have_stages(self):
        """Seeded missions have at least one stage."""
        from seed_demo import seed_missions
        seed_missions(self.temp_dir)
        for f in self.temp_dir.glob("demo-mission-*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            self.assertGreater(len(data["stages"]), 0)


class TestCleanSeeded(unittest.TestCase):
    """Tests for cleaning seeded data."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_clean_removes_only_seeded(self):
        """Clean removes seeded files but keeps others."""
        from seed_demo import clean_seeded, seed_missions
        seed_missions(self.temp_dir)
        # Add a non-seeded file
        real = self.temp_dir / "mission-real-001.json"
        real.write_text(json.dumps({"missionId": "real-001", "status": "completed"}),
                        encoding="utf-8")
        removed = clean_seeded(self.temp_dir)
        self.assertGreater(removed, 0)
        self.assertTrue(real.exists())
        self.assertEqual(len(list(self.temp_dir.glob("demo-mission-*.json"))), 0)

    def test_02_clean_empty_dir(self):
        """Clean on empty dir returns 0."""
        from seed_demo import clean_seeded
        removed = clean_seeded(self.temp_dir)
        self.assertEqual(removed, 0)

    def test_03_clean_nonexistent_dir(self):
        """Clean on nonexistent dir returns 0."""
        from seed_demo import clean_seeded
        removed = clean_seeded(self.temp_dir / "nonexistent")
        self.assertEqual(removed, 0)


class TestSeedStatus(unittest.TestCase):
    """Tests for seed status reporting."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_status_empty(self):
        """Status returns 0 seeded for empty dir."""
        from seed_demo import get_seed_status
        status = get_seed_status(self.temp_dir)
        self.assertEqual(status["seeded_missions"], 0)

    def test_02_status_after_seed(self):
        """Status reflects seeded count."""
        from seed_demo import get_seed_status, seed_missions
        count = seed_missions(self.temp_dir)
        status = get_seed_status(self.temp_dir)
        self.assertEqual(status["seeded_missions"], count)


class TestSeedAll(unittest.TestCase):
    """Tests for seed_all orchestrator."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_seed_all_returns_summary(self):
        """seed_all returns summary dict."""
        from seed_demo import seed_all
        policies_dir = self.temp_dir / "policies"
        result = seed_all(self.temp_dir, policies_dir=policies_dir)
        self.assertIn("missions_seeded", result)
        self.assertIn("policies_seeded", result)
        self.assertGreater(result["missions_seeded"], 0)

    def test_02_seed_all_clean_first(self):
        """seed_all with clean_first removes old data."""
        from seed_demo import seed_all
        policies_dir = self.temp_dir / "policies"
        # First seed
        seed_all(self.temp_dir, policies_dir=policies_dir)
        # Second seed with clean
        result = seed_all(self.temp_dir, policies_dir=policies_dir,
                          clean_first=True)
        self.assertGreater(result["cleaned"], 0)
        self.assertGreater(result["missions_seeded"], 0)


if __name__ == "__main__":
    unittest.main()
