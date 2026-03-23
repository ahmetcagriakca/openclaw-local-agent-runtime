"""Anthropic Claude provider implementation."""
import json
import os
from .base import AgentProvider, AgentResponse, ToolCall


class ClaudeProvider(AgentProvider):
    def __init__(self, model: str = None, api_key: str = None):
        import anthropic
        self.model = model or os.environ.get("OC_CLAUDE_MODEL", "claude-sonnet-4-20250514")
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = anthropic.Anthropic(api_key=key)

    def chat(self, messages: list, tools: list, max_tokens: int = 4096) -> AgentResponse:
        # Extract system message and convert message formats
        system = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "tool":
                # Convert OpenAI tool result format to Anthropic format
                chat_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_call_id"],
                        "content": msg["content"]
                    }]
                })
            elif msg["role"] == "assistant" and "tool_calls" in msg:
                # Convert OpenAI assistant tool_calls to Anthropic format
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    args = tc["function"]["arguments"]
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(args) if isinstance(args, str) else args
                    })
                chat_messages.append({"role": "assistant", "content": content})
            else:
                chat_messages.append(msg)

        # Convert OpenAI tool format to Anthropic tool format
        anthropic_tools = []
        if tools:
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool["function"]
                    anthropic_tools.append({
                        "name": func["name"],
                        "description": func["description"],
                        "input_schema": func["parameters"]
                    })

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": chat_messages,
        }
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = self.client.messages.create(**kwargs)

        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    params=block.input
                ))

        stop_reason = response.stop_reason
        if stop_reason == "tool_use":
            stop_reason = "tool_use"
        elif stop_reason == "end_turn":
            stop_reason = "end_turn"

        return AgentResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=stop_reason
        )

    def name(self) -> str:
        return f"claude ({self.model})"
