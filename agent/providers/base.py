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
    """Base interface — every LLM provider implements this.

    Canonical interface (D-148):
      execute(request: TaskRequest, tools: list, max_tokens: int) -> ProviderResponse

    Legacy interface (backward compatibility):
      chat(messages: list, tools: list, max_tokens: int) -> AgentResponse

    New providers MUST implement execute(). Legacy chat() is a compatibility
    shim that converts messages to TaskRequest and delegates to execute().
    Existing providers may override chat() directly until fully migrated.
    """

    def execute(self, request: TaskRequest, tools: list | None = None, max_tokens: int = 4096) -> ProviderResponse:
        """Canonical entrypoint — TaskRequest in, ProviderResponse out.

        Default implementation converts to legacy chat() for backward compat.
        New providers should override this directly.
        """
        messages = [{"role": "user", "content": request.prompt}]
        result = self.chat(messages, tools or [], max_tokens)
        return ProviderResponse(
            text=result.text,
            tool_calls=result.tool_calls,
            stop_reason=result.stop_reason,
            provider_name=self.name(),
        )

    def chat(self, messages: list, tools: list, max_tokens: int = 4096) -> AgentResponse:
        """Legacy entrypoint — maintained for backward compatibility.

        Default implementation converts to canonical execute() path.
        Existing providers override this directly.
        """
        raise NotImplementedError

    def name(self) -> str:
        raise NotImplementedError
