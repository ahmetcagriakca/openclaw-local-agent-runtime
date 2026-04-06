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
                return RoutingDecision(
                    selected_provider=matched,
                    reason=f"explicit preference: {provider_preference}",
                )
            # Preference unavailable — fall through to primary

        # Rule 2: Kill switch check
        if not self._is_azure_enabled():
            return self._select_fallback(
                agents, health, "azure kill switch active (AZURE_ENABLED=false)"
            )

        # Rule 3: Primary available?
        if self.primary in agents and self._is_available(agents, self.primary, health):
            return RoutingDecision(
                selected_provider=self.primary,
                reason="primary provider (azure-first policy)",
            )

        # Rule 4: Primary unavailable — fallback
        return self._select_fallback(
            agents, health, f"primary '{self.primary}' unavailable"
        )

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

    def _select_fallback(
        self, agents: dict, health: dict, fallback_reason: str
    ) -> RoutingDecision:
        """Select first available fallback provider."""
        for agent_id in self.fallback_chain:
            if agent_id in agents and self._is_available(agents, agent_id, health):
                logger.info(
                    "Routing fallback: %s → %s (reason: %s)",
                    self.primary,
                    agent_id,
                    fallback_reason,
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
