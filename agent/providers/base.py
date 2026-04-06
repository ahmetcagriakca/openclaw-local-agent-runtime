"""Base provider interface for agent LLM providers."""
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    params: dict


@dataclass
class AgentResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"


@dataclass
class TaskRequest:
    """Canonical internal request — all providers accept this."""

    task_type: str  # review, analysis, implementation, tool_call, research
    prompt: str
    tools_required: list[str] = field(default_factory=list)
    risk_tier: str = "low"  # low / medium / high / critical
    provider_preference: str | None = None  # azure / openai / anthropic / ollama


@dataclass
class ProviderResponse:
    """Canonical internal response — all providers produce this."""

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    provider_name: str = ""
    model: str = ""
    usage: dict = field(default_factory=dict)  # input_tokens, output_tokens, total_tokens

    def to_agent_response(self) -> AgentResponse:
        """Convert to legacy AgentResponse for backward compatibility."""
        return AgentResponse(
            text=self.text,
            tool_calls=self.tool_calls,
            stop_reason=self.stop_reason,
        )


class AgentProvider:
    """Base interface — every LLM provider implements this."""

    def chat(self, messages: list, tools: list, max_tokens: int = 4096) -> AgentResponse:
        raise NotImplementedError

    def name(self) -> str:
        raise NotImplementedError
