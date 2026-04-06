"""Tests for policy engine fail-closed defaults — S76 P1.7.

Tests that:
1. No matching rules → deny (fail-closed)
2. default-allow.yaml is condition-gated (not unconditional)
"""
from pathlib import Path

import pytest
import yaml


class TestDefaultAllowYaml:
    """P1.7: Verify default-allow.yaml is condition-gated."""

    def test_default_allow_has_condition(self):
        policy_path = Path(__file__).resolve().parent.parent.parent / "config" / "policies" / "default-allow.yaml"
        if not policy_path.exists():
            pytest.skip("default-allow.yaml not present — removed (acceptable)")

        data = yaml.safe_load(policy_path.read_text())
        condition = data.get("condition", {})

        # Must NOT have "always: true" — must be condition-gated
        assert condition.get("always") is not True, \
            "default-allow.yaml must not have unconditional 'always: true'"

    def test_default_allow_has_environment_condition(self):
        policy_path = Path(__file__).resolve().parent.parent.parent / "config" / "policies" / "default-allow.yaml"
        if not policy_path.exists():
            pytest.skip("default-allow.yaml removed")

        data = yaml.safe_load(policy_path.read_text())
        condition = data.get("condition", {})

        # Should be gated by environment
        assert "environment" in condition, \
            "default-allow.yaml should be gated by environment condition"

    def test_default_allow_priority_is_lowest(self):
        policy_path = Path(__file__).resolve().parent.parent.parent / "config" / "policies" / "default-allow.yaml"
        if not policy_path.exists():
            pytest.skip("default-allow.yaml removed")

        data = yaml.safe_load(policy_path.read_text())
        assert data.get("priority") == 9999


class TestPolicyEngineDefaults:
    """P1.7: Policy engine fail-closed tests."""

    def test_no_rules_returns_deny(self, tmp_path):
        """Policy engine with no loaded rules should deny."""
        from mission.policy_engine import PolicyEngine

        # Empty dir — no YAML files
        empty_dir = tmp_path / "empty_policies"
        empty_dir.mkdir()
        engine = PolicyEngine(policies_dir=str(empty_dir))

        result = engine.evaluate(
            policy_context={"action": "tool.execute"},
            mission_config={"goal": "test", "complexity": "low"},
            tool_request={"tool": "some_tool"},
        )

        assert result.decision.value == "deny", \
            "Policy engine must deny when no rules match (fail-closed)"

    def test_constrained_default_allow_denies_non_matching(self, tmp_path):
        """default-allow with environment=development should deny for non-matching context."""
        from mission.policy_engine import PolicyEngine

        # Create policy dir with only the constrained default-allow
        policy_dir = tmp_path / "constrained_policies"
        policy_dir.mkdir()
        (policy_dir / "default-allow.yaml").write_text(
            "name: default-allow\n"
            "priority: 9999\n"
            "condition:\n"
            "  environment: development\n"
            "decision: allow\n"
        )

        engine = PolicyEngine(policies_dir=str(policy_dir))

        # With no environment in context — condition won't match
        result = engine.evaluate(
            policy_context={"action": "tool.execute"},
            mission_config={"goal": "test"},
            tool_request={"tool": "some_tool"},
        )

        assert result.decision.value == "deny", \
            "Constrained default-allow must deny when condition doesn't match"
