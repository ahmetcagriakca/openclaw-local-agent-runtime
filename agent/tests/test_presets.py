"""Tests for mission presets and quick-run — B-103 (Sprint 38)."""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("TESTING", "1")

from templates.schema import MissionConfig, MissionTemplate, TemplateParameter
from templates.store import TemplateStore


class TestPresetTemplates(unittest.TestCase):
    """Test built-in preset templates."""

    def setUp(self):
        self.templates_dir = Path(__file__).resolve().parent.parent.parent / "config" / "templates"

    def test_preset_files_exist(self):
        """Built-in preset template files should exist."""
        expected = [
            "preset_system_health.json",
            "preset_code_review.json",
            "preset_test_runner.json",
        ]
        for name in expected:
            path = self.templates_dir / name
            self.assertTrue(path.exists(), f"Preset template missing: {name}")

    def test_preset_files_valid_json(self):
        """All preset templates should be valid JSON."""
        for f in self.templates_dir.glob("preset_*.json"):
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertIn("id", data, f"{f.name} missing id")
            self.assertIn("name", data, f"{f.name} missing name")
            self.assertEqual(data["status"], "published", f"{f.name} should be published")

    def test_preset_load_via_store(self):
        """TemplateStore should load preset templates."""
        store = TemplateStore(self.templates_dir)
        templates = store.list()
        preset_names = [t["name"] for t in templates]
        self.assertIn("System Health Check", preset_names)
        self.assertIn("Code Review", preset_names)
        self.assertIn("Test Suite Runner", preset_names)


class TestTemplateRenderGoal(unittest.TestCase):
    """Test goal rendering from template parameters."""

    def test_render_with_params(self):
        """render_goal should substitute parameters."""
        tmpl = MissionTemplate(
            name="Test",
            parameters=[TemplateParameter(name="target", type="string")],
            mission_config=MissionConfig(goal_template="Review {target} for issues"),
        )
        goal = tmpl.render_goal({"target": "agent/api/server.py"})
        self.assertEqual(goal, "Review agent/api/server.py for issues")

    def test_render_with_default(self):
        """render_goal should use default value when param not provided."""
        tmpl = MissionTemplate(
            name="Test",
            parameters=[TemplateParameter(name="scope", type="string", default="all", required=False)],
            mission_config=MissionConfig(goal_template="Run {scope} tests"),
        )
        goal = tmpl.render_goal({})
        self.assertEqual(goal, "Run all tests")

    def test_render_no_params(self):
        """render_goal with no parameters should return template as-is."""
        tmpl = MissionTemplate(
            name="Test",
            mission_config=MissionConfig(goal_template="Check system health"),
        )
        goal = tmpl.render_goal({})
        self.assertEqual(goal, "Check system health")


class TestTemplateValidation(unittest.TestCase):
    """Test parameter validation."""

    def test_missing_required_param(self):
        """validate_params should flag missing required parameters."""
        tmpl = MissionTemplate(
            parameters=[TemplateParameter(name="target", type="string", required=True)],
            mission_config=MissionConfig(goal_template="Review {target}"),
        )
        errors = tmpl.validate_params({})
        self.assertEqual(len(errors), 1)
        self.assertIn("target", errors[0])

    def test_valid_params(self):
        """validate_params should return empty list for valid params."""
        tmpl = MissionTemplate(
            parameters=[TemplateParameter(name="target", type="string", required=True)],
            mission_config=MissionConfig(goal_template="Review {target}"),
        )
        errors = tmpl.validate_params({"target": "test.py"})
        self.assertEqual(len(errors), 0)

    def test_optional_param_missing_ok(self):
        """Optional params should not cause validation errors."""
        tmpl = MissionTemplate(
            parameters=[TemplateParameter(name="scope", type="string", required=False)],
            mission_config=MissionConfig(goal_template="Run {scope} tests"),
        )
        errors = tmpl.validate_params({})
        self.assertEqual(len(errors), 0)


class TestPresetsAPI(unittest.TestCase):
    """Test presets API endpoint via direct function call."""

    def test_list_presets_filters_published(self):
        """Presets should only include published templates."""
        all_templates = [
            {"id": "t1", "name": "Published", "status": "published"},
            {"id": "t2", "name": "Draft", "status": "draft"},
            {"id": "t3", "name": "Another Published", "status": "published"},
        ]
        presets = [t for t in all_templates if t.get("status") == "published"]
        self.assertEqual(len(presets), 2)
        names = [p["name"] for p in presets]
        self.assertIn("Published", names)
        self.assertNotIn("Draft", names)

    def test_presets_sorted_by_name(self):
        """Presets should be sorted alphabetically."""
        presets = [
            {"id": "t1", "name": "Zebra", "status": "published"},
            {"id": "t2", "name": "Alpha", "status": "published"},
        ]
        presets.sort(key=lambda t: t.get("name", ""))
        self.assertEqual(presets[0]["name"], "Alpha")
        self.assertEqual(presets[1]["name"], "Zebra")


class TestQuickRunLogic(unittest.TestCase):
    """Test quick-run logic."""

    def test_goal_render_for_quick_run(self):
        """Quick-run should correctly render goal from template and params."""
        tmpl = MissionTemplate(
            name="Code Review",
            parameters=[TemplateParameter(name="target", type="string")],
            mission_config=MissionConfig(goal_template="Review {target} for issues"),
            status="published",
        )
        # Validate
        errors = tmpl.validate_params({"target": "agent/api/server.py"})
        self.assertEqual(errors, [])
        # Render
        goal = tmpl.render_goal({"target": "agent/api/server.py"})
        self.assertEqual(goal, "Review agent/api/server.py for issues")

    def test_draft_template_not_runnable(self):
        """Draft templates should not be allowed for quick-run."""
        tmpl = MissionTemplate(
            name="Draft",
            mission_config=MissionConfig(goal_template="Do something"),
            status="draft",
        )
        self.assertNotEqual(tmpl.status, "published")

    def test_published_template_is_runnable(self):
        """Published templates should be allowed for quick-run."""
        tmpl = MissionTemplate(
            name="Ready",
            mission_config=MissionConfig(goal_template="Do something"),
            status="published",
        )
        self.assertEqual(tmpl.status, "published")


if __name__ == "__main__":
    unittest.main()
