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


class AgentProvider:
    """Base interface — every LLM provider implements this."""

    def chat(self, messages: list, tools: list, max_tokens: int = 4096) -> AgentResponse:
        raise NotImplementedError

    def name(self) -> str:
        raise NotImplementedError
