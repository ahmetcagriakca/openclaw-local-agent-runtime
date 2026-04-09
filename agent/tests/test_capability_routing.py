"""Tests for D-150 capability routing integration (controller + registry + policy)."""
from unittest.mock import MagicMock, patch

import pytest

from providers.capability_registry import (
    FUNCTION_CALLING,
    LONG_CONTEXT,
    REASONING,
    TEXT_GENERATION,
    resolve_capabilities,
)
from providers.routing_policy import ProviderRoutingPolicy, RoutingDecision


AGENT_CONFIG = {
    "defaultAgent": "azure-general",
    "agents": {
        "azure-general": {
            "provider": "azure-openai",
            "model": "gpt-5.3-codex-cagri",
            "enabled": True,
        },
        "gpt-general": {
            "provider": "gpt",
            "model": "gpt-4o",
            "enabled": True,
        },
        "claude-general": {
            "provider": "claude",
            "model": "claude-sonnet-4-20250514",
            "enabled": True,
        },
    },
}

_has_pydantic = pytest.importorskip("pydantic", reason="pydantic required") if False else None
try:
    import pydantic  # noqa: F401
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


class TestCapabilityRoutingIntegration:
    """D-150: Capability registry integrates with ProviderRoutingPolicy."""

    def test_analyst_routes_to_long_context_provider(self):
        """Analyst needs long_context — should route to capable provider."""
        caps = resolve_capabilities("analyst")
        assert LONG_CONTEXT in caps

        policy = ProviderRoutingPolicy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps,
        )
        assert decision.selected_provider == "claude-general"
        assert decision.fallback_used

    def test_developer_routes_to_function_calling_provider(self):
        """Developer needs function_calling — Azure supports it."""
        caps = resolve_capabilities("developer")
        assert FUNCTION_CALLING in caps

        policy = ProviderRoutingPolicy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps,
        )
        assert decision.selected_provider == "azure-general"
        assert not decision.fallback_used

    def test_unknown_role_uses_default_routing(self):
        """D-150 R3: Unknown role = empty caps = existing Azure-first."""
        caps = resolve_capabilities("nonexistent-role")
        assert caps == []

        policy = ProviderRoutingPolicy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=None,
        )
        assert decision.selected_provider == "azure-general"

    def test_manager_role_basic_routing(self):
        """Manager needs only text_generation — all providers support it."""
        caps = resolve_capabilities("manager")
        assert caps == [TEXT_GENERATION]

        policy = ProviderRoutingPolicy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps,
        )
        assert decision.selected_provider == "azure-general"

    def test_architect_routes_to_reasoning_and_long_context(self):
        """Architect needs reasoning + long_context."""
        caps = resolve_capabilities("architect")
        assert REASONING in caps
        assert LONG_CONTEXT in caps

        policy = ProviderRoutingPolicy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps,
        )
        assert decision.selected_provider == "claude-general"

    def test_skill_override_changes_routing(self):
        """Skill override can add capabilities that change routing."""
        caps_basic = resolve_capabilities("product-owner")
        policy = ProviderRoutingPolicy()
        decision_basic = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps_basic,
        )
        assert decision_basic.selected_provider == "azure-general"

        caps_with_skill = resolve_capabilities("product-owner", skill="repository_discovery")
        decision_skill = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps_with_skill,
        )
        assert decision_skill.selected_provider == "claude-general"

    def test_security_role_routing(self):
        """Security needs reasoning — Azure supports it."""
        caps = resolve_capabilities("security")
        assert REASONING in caps

        policy = ProviderRoutingPolicy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps,
        )
        assert decision.selected_provider == "azure-general"

    def test_tester_role_routing(self):
        """Tester needs function_calling — Azure supports it."""
        caps = resolve_capabilities("tester")
        assert FUNCTION_CALLING in caps

        policy = ProviderRoutingPolicy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps,
        )
        assert decision.selected_provider == "azure-general"

    def test_reviewer_role_routing(self):
        """Reviewer needs reasoning — Azure supports it."""
        caps = resolve_capabilities("reviewer")
        policy = ProviderRoutingPolicy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=caps,
        )
        assert decision.selected_provider == "azure-general"

    def test_recovery_triage_skill_needs_reasoning(self):
        """recovery_triage skill adds reasoning requirement."""
        caps = resolve_capabilities("analyst", skill="recovery_triage")
        assert REASONING in caps
        assert LONG_CONTEXT in caps


@pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic required for controller tests")
class TestControllerCapabilityWiring:
    """Test that controller passes capabilities through to routing policy."""

    @pytest.fixture
    def controller(self, tmp_path):
        """Create MissionController with mocked dependencies."""
        with patch("mission.controller.MISSIONS_DIR", str(tmp_path / "missions")), \
             patch("providers.factory.load_agent_config", return_value=AGENT_CONFIG), \
             patch("mission.controller.MissionController._update_capability_manifest"), \
             patch("mission.controller.MissionController._recover_orphaned_missions"):

            from mission.controller import MissionController
            mc = MissionController(planner_agent_id="azure-general")
            yield mc

    def test_select_agent_passes_capabilities(self, controller):
        """Controller resolves capabilities and passes to routing policy."""
        with patch("providers.provider_telemetry.emit_provider_selection"), \
             patch("context.policy_telemetry.emit_policy_event"), \
             patch("providers.factory.load_agent_config", return_value=AGENT_CONFIG):
            agent_id = controller._select_agent_for_role(
                "analyst", mission_id="test-m1", stage_id="s1",
                skill="repository_discovery"
            )
            assert agent_id == "claude-general"

    def test_select_agent_emits_capability_telemetry(self, controller):
        """Controller emits capability info in telemetry."""
        with patch("providers.provider_telemetry.emit_provider_selection"), \
             patch("context.policy_telemetry.emit_policy_event") as mock_emit, \
             patch("providers.factory.load_agent_config", return_value=AGENT_CONFIG):
            controller._select_agent_for_role(
                "developer", mission_id="test-m2", stage_id="s1",
                skill="targeted_code_change"
            )
            mock_emit.assert_called_once()
            payload = mock_emit.call_args[0][1]
            assert "required_capabilities" in payload
            assert payload["capability_source"] == "registry"

    def test_select_agent_backward_compat_no_skill(self, controller):
        """Without skill parameter, still works (backward compatibility)."""
        with patch("providers.provider_telemetry.emit_provider_selection"), \
             patch("context.policy_telemetry.emit_policy_event"), \
             patch("providers.factory.load_agent_config", return_value=AGENT_CONFIG):
            agent_id = controller._select_agent_for_role(
                "developer", mission_id="test-m3"
            )
            assert agent_id == "azure-general"

    def test_select_agent_unknown_role_azure_first(self, controller):
        """Unknown role = Azure-first routing."""
        with patch("providers.provider_telemetry.emit_provider_selection"), \
             patch("providers.factory.load_agent_config", return_value=AGENT_CONFIG):
            agent_id = controller._select_agent_for_role("unknown-role")
            assert agent_id == "azure-general"
