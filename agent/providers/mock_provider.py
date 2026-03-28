"""Mock LLM provider for deterministic E2E testing.

Returns stable fixture responses per role/prompt.
Enables deterministic mission execution without real LLM calls.
"""
from providers.base import AgentProvider, AgentResponse


# Fixture responses keyed by role
_ROLE_RESPONSES = {
    "analyst": "Analysis complete. The system shows 3 active components with no anomalies detected.",
    "planner": "Plan created: Phase 1 — data collection, Phase 2 — analysis, Phase 3 — reporting.",
    "executor": "Execution complete. All tasks finished successfully with no errors.",
    "reviewer": "Review passed. Quality gate criteria met: coverage > 80%, no critical issues.",
    "default": "Task completed successfully. No issues found.",
}


class MockProvider(AgentProvider):
    """Deterministic mock provider for testing.

    Returns stable fixture responses based on the specialist role
    extracted from the system prompt, or a default response.
    """

    def __init__(self):
        self._call_count = 0

    def chat(self, messages: list, tools: list, max_tokens: int = 4096) -> AgentResponse:
        self._call_count += 1

        # Extract role from system prompt if available
        role = "default"
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "system":
                content = msg.get("content", "")
                for r in _ROLE_RESPONSES:
                    if r in content.lower():
                        role = r
                        break

        return AgentResponse(
            text=_ROLE_RESPONSES.get(role, _ROLE_RESPONSES["default"]),
            tool_calls=[],
            stop_reason="end_turn",
        )

    def name(self) -> str:
        return "mock"

    @property
    def call_count(self) -> int:
        return self._call_count
