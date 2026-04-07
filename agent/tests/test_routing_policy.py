"""Tests for ProviderRoutingPolicy (D-148)."""
from unittest.mock import patch

import pytest

from providers.routing_policy import ProviderRoutingPolicy, RoutingDecision

# --- Fixtures ---

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
        "mock-general": {
            "provider": "mock",
            "model": "mock-v1",
            "enabled": True,
        },
    },
}


def make_policy(**overrides):
    defaults = {
        "primary": "azure-general",
        "fallback_chain": ["gpt-general", "claude-general"],
    }
    defaults.update(overrides)
    return ProviderRoutingPolicy(**defaults)


# --- Default routing tests ---


class TestDefaultRouting:
    def test_azure_is_primary(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.selected_provider == "azure-general"
        assert not decision.fallback_used
        assert "primary" in decision.reason

    def test_routing_decision_fields(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert isinstance(decision, RoutingDecision)
        assert decision.selected_provider
        assert decision.reason
        assert decision.fallback_reason is None


# --- Kill switch tests ---


class TestKillSwitch:
    @patch.dict("os.environ", {"AZURE_ENABLED": "false"})
    def test_kill_switch_false(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.selected_provider != "azure-general"
        assert decision.fallback_used
        assert "kill switch" in decision.fallback_reason

    @patch.dict("os.environ", {"AZURE_ENABLED": "0"})
    def test_kill_switch_zero(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.fallback_used
        assert "kill switch" in decision.fallback_reason

    @patch.dict("os.environ", {"AZURE_ENABLED": "no"})
    def test_kill_switch_no(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.fallback_used

    @patch.dict("os.environ", {"AZURE_ENABLED": "true"})
    def test_kill_switch_enabled(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.selected_provider == "azure-general"
        assert not decision.fallback_used

    @patch.dict("os.environ", {}, clear=False)
    def test_kill_switch_default_enabled(self):
        """No AZURE_ENABLED env var → Azure enabled by default."""
        import os
        os.environ.pop("AZURE_ENABLED", None)
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.selected_provider == "azure-general"


# --- Fallback tests ---


class TestFallback:
    def test_fallback_when_azure_disabled_in_config(self):
        config = {**AGENT_CONFIG, "agents": {**AGENT_CONFIG["agents"]}}
        config["agents"]["azure-general"] = {
            **config["agents"]["azure-general"],
            "enabled": False,
        }
        policy = make_policy()
        decision = policy.select(config)
        assert decision.selected_provider == "gpt-general"
        assert decision.fallback_used

    def test_fallback_when_azure_unhealthy(self):
        policy = make_policy()
        health = {"azure-general": False, "gpt-general": True}
        decision = policy.select(AGENT_CONFIG, health_status=health)
        assert decision.selected_provider == "gpt-general"
        assert decision.fallback_used

    def test_fallback_chain_order(self):
        """First healthy fallback is selected."""
        policy = make_policy()
        health = {"azure-general": False, "gpt-general": False, "claude-general": True}
        decision = policy.select(AGENT_CONFIG, health_status=health)
        assert decision.selected_provider == "claude-general"
        assert decision.fallback_used

    def test_no_available_provider_raises(self):
        policy = make_policy()
        health = {
            "azure-general": False,
            "gpt-general": False,
            "claude-general": False,
        }
        with pytest.raises(RuntimeError, match="No available provider"):
            policy.select(AGENT_CONFIG, health_status=health)

    @patch.dict("os.environ", {"AZURE_ENABLED": "false"})
    def test_kill_switch_fallback_to_gpt(self):
        """Azure kill switch → GPT handles full workload."""
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.selected_provider == "gpt-general"
        assert decision.fallback_used
        assert "kill switch" in decision.fallback_reason

    @patch.dict("os.environ", {"AZURE_ENABLED": "false"})
    def test_kill_switch_fallback_to_claude(self):
        """Azure kill switch + GPT unhealthy → Claude handles."""
        policy = make_policy()
        health = {"gpt-general": False}
        decision = policy.select(AGENT_CONFIG, health_status=health)
        assert decision.selected_provider == "claude-general"
        assert decision.fallback_used


# --- Provider preference tests ---


class TestProviderPreference:
    def test_explicit_openai_preference(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG, provider_preference="openai")
        assert decision.selected_provider == "gpt-general"
        assert "explicit preference" in decision.reason
        assert not decision.fallback_used

    def test_explicit_anthropic_preference(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG, provider_preference="anthropic")
        assert decision.selected_provider == "claude-general"
        assert "explicit preference" in decision.reason

    def test_explicit_azure_preference(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG, provider_preference="azure")
        assert decision.selected_provider == "azure-general"

    def test_explicit_ollama_preference(self):
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG, provider_preference="ollama")
        assert decision.selected_provider == "ollama-general"

    def test_preference_unavailable_falls_to_primary(self):
        """If preferred provider is disabled, fall through to primary."""
        config = {**AGENT_CONFIG, "agents": {**AGENT_CONFIG["agents"]}}
        config["agents"]["claude-general"] = {
            **config["agents"]["claude-general"],
            "enabled": False,
        }
        policy = make_policy()
        decision = policy.select(config, provider_preference="anthropic")
        # Preference unavailable → falls through to primary (azure)
        assert decision.selected_provider == "azure-general"


# --- Capability routing tests ---


class TestCapabilityRouting:
    def test_azure_missing_capability_fallback_to_gpt(self):
        """Azure lacks code_interpreter → GPT selected."""
        policy = make_policy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=["code_interpreter"],
        )
        assert decision.selected_provider == "gpt-general"
        assert decision.fallback_used
        assert "missing capabilities" in decision.fallback_reason

    def test_azure_missing_capability_gpt_unavailable_fallback_to_claude(self):
        """Azure lacks long_context, GPT also lacks it → Claude selected."""
        policy = make_policy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=["long_context"],
        )
        assert decision.selected_provider == "claude-general"
        assert decision.fallback_used

    def test_capability_match_stays_primary(self):
        """Azure has text_generation → stays primary."""
        policy = make_policy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=["text_generation"],
        )
        assert decision.selected_provider == "azure-general"
        assert not decision.fallback_used

    def test_all_providers_lack_capability(self):
        """No provider has 'browser_mutation' → RuntimeError."""
        policy = make_policy()
        with pytest.raises(RuntimeError, match="No available provider"):
            policy.select(
                AGENT_CONFIG,
                required_capabilities=["browser_mutation"],
            )

    def test_multiple_capabilities_required(self):
        """Needs function_calling + reasoning → Azure has both."""
        policy = make_policy()
        decision = policy.select(
            AGENT_CONFIG,
            required_capabilities=["function_calling", "reasoning"],
        )
        assert decision.selected_provider == "azure-general"
        assert not decision.fallback_used

    def test_no_capabilities_required(self):
        """No capability requirement → primary selected."""
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG, required_capabilities=None)
        assert decision.selected_provider == "azure-general"

    def test_empty_capabilities_list(self):
        """Empty list → primary selected."""
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG, required_capabilities=[])
        assert decision.selected_provider == "azure-general"


# --- Edge cases ---


class TestEdgeCases:
    def test_empty_fallback_chain(self):
        policy = ProviderRoutingPolicy(primary="azure-general", fallback_chain=[])
        health = {"azure-general": False}
        with pytest.raises(RuntimeError, match="No available provider"):
            policy.select(AGENT_CONFIG, health_status=health)

    def test_custom_primary(self):
        policy = ProviderRoutingPolicy(
            primary="gpt-general",
            fallback_chain=["azure-general", "claude-general"],
        )
        decision = policy.select(AGENT_CONFIG)
        assert decision.selected_provider == "gpt-general"

    def test_health_status_not_provided(self):
        """When no health status, all providers considered healthy."""
        policy = make_policy()
        decision = policy.select(AGENT_CONFIG)
        assert decision.selected_provider == "azure-general"
