"""Tests for capability registry (D-150)."""
import pytest

from providers.capability_registry import (
    FUNCTION_CALLING,
    LONG_CONTEXT,
    REASONING,
    TEXT_GENERATION,
    get_role_capabilities,
    get_skill_overrides,
    resolve_capabilities,
)


class TestResolveCapabilities:
    """D-150 R1/R3: Capability resolution from role + skill."""

    def test_known_role_returns_capabilities(self):
        caps = resolve_capabilities("analyst")
        assert TEXT_GENERATION in caps
        assert LONG_CONTEXT in caps

    def test_developer_needs_function_calling(self):
        caps = resolve_capabilities("developer")
        assert FUNCTION_CALLING in caps
        assert TEXT_GENERATION in caps

    def test_architect_needs_reasoning_and_long_context(self):
        caps = resolve_capabilities("architect")
        assert REASONING in caps
        assert LONG_CONTEXT in caps
        assert TEXT_GENERATION in caps

    def test_unknown_role_returns_empty(self):
        """D-150 R3: Unknown role = empty capabilities = Azure-first fallback."""
        caps = resolve_capabilities("nonexistent-role")
        assert caps == []

    def test_unknown_skill_does_not_add_capabilities(self):
        caps_without = resolve_capabilities("manager")
        caps_with = resolve_capabilities("manager", skill="unknown_skill")
        assert caps_without == caps_with

    def test_skill_override_adds_capabilities(self):
        """Skill overrides add to role capabilities (union)."""
        caps = resolve_capabilities("product-owner", skill="repository_discovery")
        assert LONG_CONTEXT in caps  # from skill override
        assert TEXT_GENERATION in caps  # from role

    def test_controlled_execution_adds_function_calling(self):
        caps = resolve_capabilities("manager", skill="controlled_execution")
        assert FUNCTION_CALLING in caps

    def test_result_is_sorted_and_deduplicated(self):
        caps = resolve_capabilities("developer", skill="controlled_execution")
        # Both role and skill add FUNCTION_CALLING — should not duplicate
        assert caps == sorted(set(caps))
        assert caps.count(FUNCTION_CALLING) == 1

    def test_planner_role(self):
        caps = resolve_capabilities("planner")
        assert TEXT_GENERATION in caps
        assert REASONING in caps

    def test_summary_role(self):
        caps = resolve_capabilities("summary")
        assert caps == [TEXT_GENERATION]

    def test_security_role(self):
        caps = resolve_capabilities("security")
        assert TEXT_GENERATION in caps
        assert REASONING in caps

    def test_reviewer_role(self):
        caps = resolve_capabilities("reviewer")
        assert TEXT_GENERATION in caps
        assert REASONING in caps

    def test_tester_role(self):
        caps = resolve_capabilities("tester")
        assert TEXT_GENERATION in caps
        assert FUNCTION_CALLING in caps


class TestRegistryIntrospection:
    """Introspection APIs for telemetry/debug."""

    def test_get_role_capabilities_returns_dict(self):
        result = get_role_capabilities()
        assert isinstance(result, dict)
        assert "analyst" in result
        assert "developer" in result

    def test_get_role_capabilities_returns_copy(self):
        result = get_role_capabilities()
        result["analyst"] = []
        # Original should be unaffected
        assert resolve_capabilities("analyst") != []

    def test_get_skill_overrides_returns_dict(self):
        result = get_skill_overrides()
        assert isinstance(result, dict)
        assert "controlled_execution" in result

    def test_get_skill_overrides_returns_copy(self):
        result = get_skill_overrides()
        result["controlled_execution"] = []
        # Original should be unaffected
        caps = resolve_capabilities("manager", skill="controlled_execution")
        assert FUNCTION_CALLING in caps


class TestAllRolesHaveCapabilities:
    """Ensure all 9 canonical roles + synthetic roles are mapped."""

    @pytest.mark.parametrize("role", [
        "product-owner", "analyst", "architect", "project-manager",
        "developer", "tester", "reviewer", "security", "manager",
        "planner", "summary",
    ])
    def test_canonical_role_has_capabilities(self, role):
        caps = resolve_capabilities(role)
        assert len(caps) > 0, f"Role '{role}' has no capabilities"
        assert TEXT_GENERATION in caps, f"Role '{role}' missing text_generation"
