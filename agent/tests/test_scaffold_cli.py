"""Tests for B-109 Scaffolding CLI (Sprint 50).

Covers: template generation, role validation, plugin mode, output format.
"""

import json
import sys
from pathlib import Path

import pytest

# Add tools/ to path
TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from scaffold_template import scaffold_plugin, scaffold_template, validate_specialist


class TestTemplateGeneration:
    def test_generates_valid_template(self):
        t = scaffold_template(
            name="Test Analysis",
            specialist="analyst",
            goal="Analyze the codebase",
        )
        assert t["id"] == "preset_test_analysis"
        assert t["name"] == "Test Analysis"
        assert t["mission_config"]["specialist"] == "analyst"
        assert t["mission_config"]["goal_template"] == "Analyze the codebase"
        assert t["status"] == "draft"

    def test_template_has_all_fields(self):
        t = scaffold_template(
            name="Full", specialist="developer",
            goal="Build feature",
        )
        required = ["id", "name", "description", "version", "author",
                     "status", "parameters", "mission_config",
                     "created_at", "updated_at"]
        for field in required:
            assert field in t, f"Missing field: {field}"

    def test_custom_parameters(self):
        t = scaffold_template(
            name="Custom", specialist="tester",
            goal="Run tests for {target}",
            max_stages=3, timeout_minutes=10, provider="claude-sonnet",
        )
        assert t["mission_config"]["max_stages"] == 3
        assert t["mission_config"]["timeout_minutes"] == 10
        assert t["mission_config"]["provider"] == "claude-sonnet"

    def test_serializable_to_json(self):
        t = scaffold_template(
            name="JSON Test", specialist="analyst", goal="test",
        )
        output = json.dumps(t, indent=2)
        parsed = json.loads(output)
        assert parsed["id"] == t["id"]


class TestRoleValidation:
    def test_valid_roles(self):
        for role in ["analyst", "developer", "tester", "product-owner"]:
            assert validate_specialist(role) is True

    def test_invalid_role(self):
        assert validate_specialist("nonexistent") is False

    def test_invalid_role_raises_in_scaffold(self):
        with pytest.raises(ValueError, match="Invalid specialist"):
            scaffold_template(
                name="Bad", specialist="fakerole", goal="test",
            )


class TestPluginMode:
    def test_generates_plugin_manifest(self):
        p = scaffold_plugin(
            name="Notifier",
            events=["mission.completed", "mission.failed"],
        )
        assert p["id"] == "plugin_notifier"
        assert "hooks" in p
        assert "event_subscriptions" in p
        assert "mission.completed" in p["event_subscriptions"]

    def test_plugin_has_hooks(self):
        p = scaffold_plugin(name="Test Plugin")
        assert "on_mission_start" in p["hooks"]
        assert "on_stage_complete" in p["hooks"]
        assert "on_mission_complete" in p["hooks"]
        assert "on_mission_failed" in p["hooks"]
