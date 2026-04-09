"""Tests for D-150 capability telemetry and best-match fallback."""
import pytest

from providers.capability_registry import resolve_capabilities
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
        "ollama-general": {
            "provider": "ollama",
            "model": "qwen2.5:7b",
            "enabled": True,
        },
    },
}


class TestCapabilityTelemetryFields:
    """D-150: RoutingDecision includes capability telemetry."""

    def test_decision_includes_required_capabilities(self):
        caps = resolve_capabilities("analyst")
        policy = ProviderRoutingPolicy()
        decision = policy.select(AGENT_CONFIG, required_capabilities=caps)
        assert decision.required_capabilities == caps

    def test_decision_includes_matched_capabilities(self):
        caps = resolve_capabilities("analyst")
        policy = ProviderRoutingPolicy()
        decision = policy.select(AGENT_CONFIG, required_capabilities=caps)
        assert decision.matched_capabilities is not None
        # All required should be matched (since provider was selected for having them)
        for cap in caps:
            assert cap in decision.matched_capabilities

    def test_decision_includes_match_score(self):
        caps = resolve_capabilities("developer")
        policy = ProviderRoutingPolicy()
        decision = policy.select(AGENT_CONFIG, required_capabilities=caps)
        assert decision.capability_match_score is not None
        assert 0.0 <= decision.capability_match_score <= 1.0

    def test_no_capabilities_no_telemetry_fields(self):
        policy = ProviderRoutingPolicy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.required_capabilities is None
        assert decision.matched_capabilities is None
        assert decision.capability_match_score is None

    def test_empty_capabilities_no_telemetry(self):
        policy = ProviderRoutingPolicy()
        decision = policy.select(AGENT_CONFIG, required_capabilities=[])
        # Empty list treated as no capabilities
        assert decision.required_capabilities is None

    def test_fallback_decision_has_telemetry(self):
        caps = resolve_capabilities("architect")  # needs long_context → fallback
        policy = ProviderRoutingPolicy()
        decision = policy.select(AGENT_CONFIG, required_capabilities=caps)
        assert decision.fallback_used
        assert decision.required_capabilities == caps
        assert decision.matched_capabilities is not None


class TestBestMatchFallback:
    """D-150: Fallback prefers provider with best capability match."""

    def test_best_match_prefers_focused_provider(self):
        """When multiple fallbacks support required caps, prefer best match score."""
        # text_generation is required — both gpt and claude support it
        # gpt has 4 caps, claude has 4 caps — tie broken by chain order
        caps = ["text_generation"]
        policy = ProviderRoutingPolicy(
            primary="azure-general",
            fallback_chain=["gpt-general", "claude-general"],
        )
        # Disable azure to force fallback
        config = dict(AGENT_CONFIG)
        config["agents"] = dict(config["agents"])
        config["agents"]["azure-general"] = {
            "provider": "azure-openai", "model": "test", "enabled": False,
        }
        decision = policy.select(config, required_capabilities=caps)
        assert decision.fallback_used
        # Both gpt and claude have 4 caps each, text_generation in both
        # Equal score → chain order wins → gpt-general first
        assert decision.selected_provider == "gpt-general"

    def test_fallback_no_caps_uses_chain_order(self):
        """Without required capabilities, fallback uses simple chain order."""
        policy = ProviderRoutingPolicy(
            primary="azure-general",
            fallback_chain=["claude-general", "gpt-general"],
        )
        config = dict(AGENT_CONFIG)
        config["agents"] = dict(config["agents"])
        config["agents"]["azure-general"] = {
            "provider": "azure-openai", "model": "test", "enabled": False,
        }
        decision = policy.select(config)
        assert decision.selected_provider == "claude-general"

    def test_capability_match_score_calculation(self):
        policy = ProviderRoutingPolicy()
        # azure has 3 caps: text_generation, function_calling, reasoning
        score = policy._capability_match_score(
            "azure-general", ["text_generation", "function_calling"]
        )
        # 2 matched / 3 supported = 0.667
        assert abs(score - 2 / 3) < 0.01

    def test_capability_match_score_unknown_provider(self):
        policy = ProviderRoutingPolicy()
        score = policy._capability_match_score("unknown-provider", ["text_generation"])
        assert score == 0.5  # neutral

    def test_capability_match_score_perfect(self):
        policy = ProviderRoutingPolicy()
        # ollama has 1 cap: text_generation. Require text_generation → 1/1 = 1.0
        score = policy._capability_match_score("ollama-general", ["text_generation"])
        assert score == 1.0


class TestProviderTelemetryEmit:
    """D-150: provider_telemetry emits capability fields."""

    def test_emit_includes_capability_fields(self):
        from unittest.mock import patch

        caps = resolve_capabilities("analyst")
        policy = ProviderRoutingPolicy()
        decision = policy.select(AGENT_CONFIG, required_capabilities=caps)

        with patch("providers.provider_telemetry.emit_policy_event") as mock:
            from providers.provider_telemetry import emit_provider_selection
            emit_provider_selection(decision, task_type="analyst", mission_id="m1")

            mock.assert_called_once()
            details = mock.call_args[0][1]
            assert "capability.required" in details
            assert "capability.matched" in details
            assert "capability.match_score" in details

    def test_emit_without_capabilities(self):
        from unittest.mock import patch

        policy = ProviderRoutingPolicy()
        decision = policy.select(AGENT_CONFIG)

        with patch("providers.provider_telemetry.emit_policy_event") as mock:
            from providers.provider_telemetry import emit_provider_selection
            emit_provider_selection(decision, task_type="test")

            mock.assert_called_once()
            details = mock.call_args[0][1]
            assert "capability.required" not in details
            assert "capability.matched" not in details
