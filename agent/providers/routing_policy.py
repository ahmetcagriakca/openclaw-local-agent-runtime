"""Provider routing policy — Azure-first with deterministic fallback (D-148)."""
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Result of a routing policy evaluation."""

    selected_provider: str  # agent ID from agent-config.json
    reason: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    # D-150: Capability resolution telemetry
    required_capabilities: list[str] | None = None
    matched_capabilities: list[str] | None = None
    capability_match_score: float | None = None


@dataclass
class ProviderRoutingPolicy:
    """Azure-first routing with deterministic fallback chain.

    Rules (D-148):
    - Azure is default primary candidate
    - Kill switch: azure.enabled=false → skip Azure entirely
    - Unhealthy provider → next in fallback chain
    - Unsupported capability → reroute to capable provider
    - Explicit provider_preference overrides routing
    """

    primary: str = "azure-general"
    fallback_chain: list[str] = field(default_factory=lambda: ["gpt-general", "claude-general"])

    # Capability manifest: which provider supports which capabilities
    # Providers not listed are assumed to support all capabilities
    capability_manifest: dict[str, list[str]] = field(default_factory=lambda: {
        "azure-general": ["text_generation", "function_calling", "reasoning"],
        "gpt-general": ["text_generation", "function_calling", "code_interpreter", "reasoning"],
        "claude-general": ["text_generation", "function_calling", "reasoning", "long_context"],
        "ollama-general": ["text_generation"],
    })

    def select(
        self,
        agent_config: dict,
        provider_preference: str | None = None,
        required_capabilities: list[str] | None = None,
        health_status: dict[str, bool] | None = None,
    ) -> RoutingDecision:
        """Select the best provider based on policy rules.

        Args:
            agent_config: Full agent-config.json content
            provider_preference: Explicit provider override (azure/openai/anthropic/ollama)
            required_capabilities: List of capabilities needed for this task
            health_status: Provider health map (agent_id → healthy bool)

        Returns:
            RoutingDecision with selected provider and reason
        """
        agents = agent_config.get("agents", {})
        health = health_status or {}

        # Rule 1: Explicit preference overrides routing
        if provider_preference:
            matched = self._find_by_provider_type(agents, provider_preference)
            if matched and self._is_available(agents, matched, health):
                decision = RoutingDecision(
                    selected_provider=matched,
                    reason=f"explicit preference: {provider_preference}",
                )
                self._attach_capability_telemetry(decision, required_capabilities)
                return decision
            # Preference unavailable — fall through to primary

        # Rule 2: Kill switch check
        if not self._is_azure_enabled():
            decision = self._select_fallback(
                agents, health, "azure kill switch active (AZURE_ENABLED=false)",
                required_capabilities=required_capabilities,
            )
            self._attach_capability_telemetry(decision, required_capabilities)
            return decision

        # Rule 3: Capability check on primary
        if required_capabilities and not self._has_capabilities(self.primary, required_capabilities):
            decision = self._select_fallback(
                agents, health,
                f"primary '{self.primary}' missing capabilities: "
                f"{self._missing_capabilities(self.primary, required_capabilities)}",
                required_capabilities=required_capabilities,
            )
            self._attach_capability_telemetry(decision, required_capabilities)
            return decision

        # Rule 4: Primary available?
        if self.primary in agents and self._is_available(agents, self.primary, health):
            decision = RoutingDecision(
                selected_provider=self.primary,
                reason="primary provider (azure-first policy)",
            )
            self._attach_capability_telemetry(decision, required_capabilities)
            return decision

        # Rule 5: Primary unavailable — fallback
        decision = self._select_fallback(
            agents, health, f"primary '{self.primary}' unavailable",
            required_capabilities=required_capabilities,
        )
        self._attach_capability_telemetry(decision, required_capabilities)
        return decision

    def _is_azure_enabled(self) -> bool:
        """Check kill switch — env var AZURE_ENABLED=false disables Azure."""
        val = os.environ.get("AZURE_ENABLED", "true").lower()
        return val not in ("false", "0", "no")

    def _is_available(self, agents: dict, agent_id: str, health: dict) -> bool:
        """Check if agent is enabled and healthy."""
        agent = agents.get(agent_id, {})
        if not agent.get("enabled", False):
            return False
        if agent_id in health and not health[agent_id]:
            return False
        return True

    def _find_by_provider_type(self, agents: dict, provider_type: str) -> str | None:
        """Find first agent matching a provider type."""
        type_map = {
            "azure": "azure-openai",
            "openai": "gpt",
            "anthropic": "claude",
            "ollama": "ollama",
        }
        target = type_map.get(provider_type, provider_type)
        for agent_id, config in agents.items():
            if config.get("provider") == target and config.get("enabled", False):
                return agent_id
        return None

    def _has_capabilities(self, agent_id: str, required: list[str]) -> bool:
        """Check if agent supports all required capabilities."""
        supported = self.capability_manifest.get(agent_id)
        if supported is None:
            return True  # Unknown providers assumed capable
        return all(cap in supported for cap in required)

    def _missing_capabilities(self, agent_id: str, required: list[str]) -> list[str]:
        """Return list of capabilities the agent is missing."""
        supported = self.capability_manifest.get(agent_id, [])
        return [cap for cap in required if cap not in supported]

    def _select_fallback(
        self, agents: dict, health: dict, fallback_reason: str,
        required_capabilities: list[str] | None = None,
    ) -> RoutingDecision:
        """Select best available and capable fallback provider.

        D-150: When capabilities are required, prefer the fallback provider
        with the best capability match score. Ties broken by chain order.
        Without required capabilities, uses first-available (original behavior).
        """
        if required_capabilities:
            # D-150: Best-match fallback — score by capability coverage
            best_id = None
            best_score = -1.0
            for agent_id in self.fallback_chain:
                if agent_id not in agents or not self._is_available(agents, agent_id, health):
                    continue
                if not self._has_capabilities(agent_id, required_capabilities):
                    continue
                score = self._capability_match_score(agent_id, required_capabilities)
                if score > best_score:
                    best_score = score
                    best_id = agent_id
            if best_id:
                logger.info(
                    "Routing fallback (capability match): %s → %s (score: %.2f, reason: %s)",
                    self.primary, best_id, best_score, fallback_reason,
                )
                return RoutingDecision(
                    selected_provider=best_id,
                    reason=f"fallback: {best_id}",
                    fallback_used=True,
                    fallback_reason=fallback_reason,
                )
        else:
            # No capabilities required — first-available (original behavior)
            for agent_id in self.fallback_chain:
                if agent_id not in agents or not self._is_available(agents, agent_id, health):
                    continue
                logger.info(
                    "Routing fallback: %s → %s (reason: %s)",
                    self.primary, agent_id, fallback_reason,
                )
                return RoutingDecision(
                    selected_provider=agent_id,
                    reason=f"fallback: {agent_id}",
                    fallback_used=True,
                    fallback_reason=fallback_reason,
                )

        raise RuntimeError(
            f"No available provider. Primary: {self.primary}, "
            f"Fallback chain: {self.fallback_chain}. "
            f"Reason: {fallback_reason}"
        )

    def _capability_match_score(self, agent_id: str, required: list[str]) -> float:
        """D-150: Score how well a provider matches required capabilities.

        Returns ratio of matched capabilities to total supported capabilities.
        Lower is better (fewer unused capabilities = more focused match).
        But since all required are already met, we use: required/supported.
        Score 1.0 = perfect match (all supported are required).
        """
        supported = self.capability_manifest.get(agent_id)
        if supported is None:
            return 0.5  # Unknown providers get neutral score
        if not supported:
            return 0.0
        matched = [cap for cap in required if cap in supported]
        return len(matched) / len(supported)

    def _attach_capability_telemetry(
        self, decision: RoutingDecision, required_capabilities: list[str] | None
    ) -> None:
        """D-150: Attach capability resolution fields to RoutingDecision."""
        if not required_capabilities:
            return
        decision.required_capabilities = required_capabilities
        supported = self.capability_manifest.get(decision.selected_provider)
        if supported is not None:
            decision.matched_capabilities = [
                cap for cap in required_capabilities if cap in supported
            ]
            decision.capability_match_score = (
                len(decision.matched_capabilities) / len(supported) if supported else 0.0
            )
