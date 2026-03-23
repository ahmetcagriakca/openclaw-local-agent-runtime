"""OpenAI GPT provider implementation."""
import json
import os
from openai import OpenAI
from .base import AgentProvider, AgentResponse, ToolCall


class GPTProvider(AgentProvider):
    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or os.environ.get("OC_GPT_MODEL", "gpt-4o")
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=key)

    def chat(self, messages: list, tools: list, max_tokens: int = 4096) -> AgentResponse:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)

        message = response.choices[0].message

        # Parse response
        text = message.content
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    params = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    params = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    params=params
                ))

        stop_reason = response.choices[0].finish_reason
        # Map OpenAI finish reasons to our standard
        if stop_reason == "tool_calls":
            stop_reason = "tool_use"
        elif stop_reason == "stop":
            stop_reason = "end_turn"

        return AgentResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason
        )

    def name(self) -> str:
        return f"gpt ({self.model})"
