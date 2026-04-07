"""Tests for T-78.01: planner/summary router bypass fix.

Verifies _plan_mission and _generate_summary route through
_select_agent_for_role (ProviderRoutingPolicy) instead of
direct create_provider(self.planner_agent_id).
"""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def controller(tmp_path):
    """Create MissionController with mocked dependencies."""
    with patch("mission.controller.MISSIONS_DIR", str(tmp_path / "missions")), \
         patch("providers.factory.load_agent_config", return_value={
             "defaultAgent": "mock-general",
             "agents": {
                 "mock-general": {
                     "provider": "mock", "model": "mock-v1", "enabled": True,
                 },
             },
         }), \
         patch("providers.routing_policy.ProviderRoutingPolicy.select") as mock_select, \
         patch("mission.controller.MissionController._update_capability_manifest"), \
         patch("mission.controller.MissionController._recover_orphaned_missions"):

        from providers.routing_policy import RoutingDecision
        mock_select.return_value = RoutingDecision(
            selected_provider="mock-general",
            reason="test default",
            fallback_used=False,
        )

        from mission.controller import MissionController
        mc = MissionController(planner_agent_id="mock-general")
        yield mc


class TestPlanMissionRoutingPolicy:
    """_plan_mission must use _select_agent_for_role, not direct create_provider."""

    def test_plan_mission_calls_select_agent_for_role(self, controller):
        """_plan_mission routes through _select_agent_for_role."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = MagicMock(
            text='{"stages": [{"specialist": "researcher", "skill": "deep-research", "objective": "test"}]}'
        )

        with patch.object(controller, "_select_agent_for_role",
                          return_value="mock-general") as mock_select, \
             patch("providers.factory.create_provider",
                   return_value=(mock_provider, {})):

            controller._plan_mission("test goal", "mission-001")

            mock_select.assert_called_once_with("planner", "mission-001")

    def test_plan_mission_does_not_use_planner_agent_id_directly(self, controller):
        """_plan_mission must NOT call create_provider(self.planner_agent_id) directly."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = MagicMock(
            text='{"stages": [{"specialist": "researcher", "skill": "deep-research", "objective": "test"}]}'
        )

        with patch.object(controller, "_select_agent_for_role",
                          return_value="routed-agent"), \
             patch("providers.factory.create_provider",
                   return_value=(mock_provider, {})) as mock_create:

            controller._plan_mission("test goal", "mission-002")

            # create_provider should be called with the ROUTED agent, not planner_agent_id
            mock_create.assert_called_once_with("routed-agent")

    def test_plan_mission_passes_mission_id_to_routing(self, controller):
        """mission_id is passed to _select_agent_for_role for telemetry."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = MagicMock(
            text='{"stages": [{"specialist": "implementer", "skill": "code-generation", "objective": "impl"}]}'
        )

        with patch.object(controller, "_select_agent_for_role",
                          return_value="mock-general") as mock_select, \
             patch("providers.factory.create_provider",
                   return_value=(mock_provider, {})):

            controller._plan_mission("build something", "mission-xyz")

            args, kwargs = mock_select.call_args
            assert args[0] == "planner"
            assert args[1] == "mission-xyz"


class TestGenerateSummaryRoutingPolicy:
    """_generate_summary must use _select_agent_for_role, not direct create_provider."""

    def test_generate_summary_calls_select_agent_for_role(self, controller):
        """_generate_summary routes through _select_agent_for_role."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = MagicMock(text="Mission completed successfully.")

        with patch.object(controller, "_select_agent_for_role",
                          return_value="mock-general") as mock_select, \
             patch("providers.factory.create_provider",
                   return_value=(mock_provider, {})):

            stages = [{"id": "s1", "objective": "test", "status": "completed", "result": "ok"}]
            controller._generate_summary("test goal", stages, [], mission_id="mission-003")

            mock_select.assert_called_once_with("planner", "mission-003")

    def test_generate_summary_uses_routed_agent(self, controller):
        """_generate_summary creates provider with routed agent name."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = MagicMock(text="Done.")

        with patch.object(controller, "_select_agent_for_role",
                          return_value="azure-general"), \
             patch("providers.factory.create_provider",
                   return_value=(mock_provider, {})) as mock_create:

            controller._generate_summary("goal", [], [], mission_id="mission-004")

            mock_create.assert_called_once_with("azure-general")

    def test_generate_summary_default_empty_mission_id(self, controller):
        """_generate_summary works with default empty mission_id."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = MagicMock(text="Summary.")

        with patch.object(controller, "_select_agent_for_role",
                          return_value="mock-general") as mock_select, \
             patch("providers.factory.create_provider",
                   return_value=(mock_provider, {})):

            controller._generate_summary("goal", [], [])

            mock_select.assert_called_once_with("planner", "")

    def test_generate_summary_produces_text(self, controller):
        """_generate_summary returns provider response text."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = MagicMock(text="Mission analysis complete.")

        with patch.object(controller, "_select_agent_for_role",
                          return_value="mock-general"), \
             patch("providers.factory.create_provider",
                   return_value=(mock_provider, {})):

            stages = [
                {"id": "s1", "objective": "research", "status": "completed", "result": "found data"},
                {"id": "s2", "objective": "implement", "status": "completed", "result": "code written"},
            ]
            result = controller._generate_summary("build feature", stages, [],
                                                    mission_id="mission-005")

            assert result == "Mission analysis complete."
            assert mock_provider.chat.called


class TestCSRFOriginCentralized:
    """Verify CSRF_ORIGIN and MUTATION_HEADERS are properly exported from conftest."""

    def test_csrf_origin_value(self):
        from conftest import CSRF_ORIGIN
        assert CSRF_ORIGIN == "http://localhost:4000"

    def test_mutation_headers_include_origin(self):
        from conftest import MUTATION_HEADERS
        assert "Origin" in MUTATION_HEADERS
        assert MUTATION_HEADERS["Origin"] == "http://localhost:4000"

    def test_mutation_headers_include_auth(self):
        from conftest import MUTATION_HEADERS
        assert "Authorization" in MUTATION_HEADERS

    def test_viewer_mutation_headers(self):
        from conftest import VIEWER_MUTATION_HEADERS
        assert "Origin" in VIEWER_MUTATION_HEADERS
        assert VIEWER_MUTATION_HEADERS["Origin"] == "http://localhost:4000"
        assert "Authorization" in VIEWER_MUTATION_HEADERS
