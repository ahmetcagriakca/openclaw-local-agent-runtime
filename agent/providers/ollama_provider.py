"""Ollama local LLM provider implementation."""
import json
import os

import requests

from .base import AgentProvider, AgentResponse, ToolCall


class OllamaProvider(AgentProvider):
    def __init__(self, model: str = None, base_url: str = None):
        self.model = model or os.environ.get("OC_OLLAMA_MODEL", "llama3.1")
        self.base_url = base_url or os.environ.get("OC_OLLAMA_URL", "http://localhost:11434")

    def chat(self, messages: list, tools: list, max_tokens: int = 4096) -> AgentResponse:
        # Convert messages — Ollama uses OpenAI-compatible format
        ollama_messages = []
        for msg in messages:
            if msg["role"] == "tool":
                ollama_messages.append({
                    "role": "user",
                    "content": f"Tool result: {msg['content']}"
                })
            elif msg["role"] == "assistant" and "tool_calls" in msg:
                text = msg.get("content") or ""
                for tc in msg["tool_calls"]:
                    text += f"\n[Called tool: {tc['function']['name']}({tc['function']['arguments']})]"
                ollama_messages.append({"role": "assistant", "content": text})
            else:
                ollama_messages.append({
                    "role": msg["role"],
                    "content": msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                })

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }

        # Ollama 0.4+ supports tool calling
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=180
            )
            data = resp.json()
        except requests.ConnectionError:
            raise ConnectionError(f"Ollama server unreachable at {self.base_url}. Is Ollama running?")
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")

        message = data.get("message", {})
        text = message.get("content")
        tool_calls = []

        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                args = func.get("arguments", {})
                tool_calls.append(ToolCall(
                    id=f"ollama-{func.get('name', 'unknown')}-{id(tc)}",
                    name=func.get("name", ""),
                    params=args if isinstance(args, dict) else json.loads(args)
                ))

        stop_reason = "tool_use" if tool_calls else "end_turn"

        return AgentResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason
        )

    def name(self) -> str:
        return f"ollama ({self.model})"
