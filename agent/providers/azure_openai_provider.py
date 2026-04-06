"""Azure OpenAI provider implementation — Responses API (D-148)."""
import json
import logging
import os
from datetime import datetime

import requests

from .base import AgentProvider, AgentResponse, ProviderResponse, TaskRequest, ToolCall

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(AgentProvider):
    """Azure OpenAI provider using the Responses API.

    Uses /openai/responses endpoint (input-based, not messages-based).
    No legacy messages adapter — D-148 rule #1.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
        retirement_date: str | None = None,
        timeout: int = 120,
    ):
        self.endpoint = (
            endpoint
            or os.environ.get("AZURE_OPENAI_ENDPOINT")
            or os.environ.get("APIM_ENDPOINT", "").split("/openai/")[0]
        )
        if not self.endpoint:
            raise ValueError(
                "Azure OpenAI endpoint required. Set AZURE_OPENAI_ENDPOINT env var "
                "or pass endpoint parameter."
            )
        self.endpoint = self.endpoint.rstrip("/")

        self.deployment = (
            deployment
            or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
            or os.environ.get("APIM_MODEL")
        )
        if not self.deployment:
            raise ValueError(
                "Azure OpenAI deployment name required. Set AZURE_OPENAI_DEPLOYMENT env var."
            )

        self.api_key = (
            api_key
            or os.environ.get("AZURE_OPENAI_API_KEY")
            or os.environ.get("APIM_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "Azure OpenAI API key required. Set AZURE_OPENAI_API_KEY env var."
            )

        self.api_version = (
            api_version
            or os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
        )
        self.timeout = timeout
        self.retirement_date = retirement_date
        self._check_retirement()

    def _check_retirement(self) -> None:
        """Warn if deployment is near or past retirement date."""
        if not self.retirement_date:
            return
        try:
            retire_dt = datetime.fromisoformat(self.retirement_date)
            now = datetime.now()
            days_until = (retire_dt - now).days
            if days_until < 0:
                logger.warning(
                    "Azure deployment '%s' is PAST retirement date (%s). "
                    "Marking as retired.",
                    self.deployment,
                    self.retirement_date,
                )
                self._retired = True
            elif days_until <= 30:
                logger.warning(
                    "Azure deployment '%s' retires in %d days (%s).",
                    self.deployment,
                    days_until,
                    self.retirement_date,
                )
                self._retired = False
            else:
                self._retired = False
        except (ValueError, TypeError):
            self._retired = False

    @property
    def retired(self) -> bool:
        return getattr(self, "_retired", False)

    def _build_url(self) -> str:
        return (
            f"{self.endpoint}/openai/responses"
            f"?api-version={self.api_version}"
        )

    def _convert_messages_to_input(self, messages: list) -> str:
        """Convert OpenAI-style messages list to Responses API input string.

        The Responses API uses a flat 'input' string, not messages array.
        We concatenate the conversation into a structured prompt.
        """
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"[System]\n{content}")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        parts.append(
                            f"[Assistant called {tc['function']['name']}("
                            f"{tc['function']['arguments']})]"
                        )
                if content:
                    parts.append(f"[Assistant]\n{content}")
            elif role == "tool":
                parts.append(f"[Tool result ({msg.get('tool_call_id', '')})]\n{content}")
            else:
                parts.append(f"[User]\n{content}")
        return "\n\n".join(parts)

    def _convert_tools(self, tools: list) -> list:
        """Convert OpenAI-format tools to Responses API format."""
        resp_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                resp_tools.append({
                    "type": "function",
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {}),
                })
            else:
                resp_tools.append(tool)
        return resp_tools

    def execute(self, request: TaskRequest, tools: list | None = None, max_tokens: int = 4096) -> ProviderResponse:
        """Canonical entrypoint — TaskRequest directly to Responses API.

        No messages conversion. D-148 compliant: TaskRequest -> Responses payload.
        This is the primary path for Azure provider.
        """
        max_tokens = max(max_tokens, 16)  # Azure minimum

        payload: dict = {
            "model": self.deployment,
            "input": request.prompt,
            "max_output_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = self._convert_tools(tools)
            payload["tool_choice"] = "auto"

        return self._send_request(payload)

    def chat(self, messages: list, tools: list, max_tokens: int = 4096) -> AgentResponse:
        """Legacy compatibility entrypoint — converts messages to Responses API.

        This is a backward-compatibility shim. New callers should use execute().
        """
        resp = self._chat_via_messages(messages, tools, max_tokens)
        return resp.to_agent_response()

    def _chat_via_messages(
        self, messages: list, tools: list, max_tokens: int = 4096
    ) -> ProviderResponse:
        """Legacy path: messages -> input conversion -> Responses API."""
        input_text = self._convert_messages_to_input(messages)
        max_tokens = max(max_tokens, 16)  # Azure minimum

        payload: dict = {
            "model": self.deployment,
            "input": input_text,
            "max_output_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = self._convert_tools(tools)
            payload["tool_choice"] = "auto"

        return self._send_request(payload)

    def _send_request(self, payload: dict) -> ProviderResponse:
        """Send HTTP request to Azure OpenAI Responses API and parse result."""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        try:
            http_resp = requests.post(
                self._build_url(),
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.Timeout:
            raise TimeoutError(
                f"Azure OpenAI request timed out after {self.timeout}s"
            )
        except requests.ConnectionError:
            raise ConnectionError(
                f"Azure OpenAI endpoint unreachable: {self.endpoint}"
            )

        if http_resp.status_code == 401:
            raise PermissionError("Azure OpenAI authentication failed (401)")
        if http_resp.status_code == 404:
            raise ValueError(
                f"Azure deployment '{self.deployment}' not found (404). "
                "Check deployment name matches Azure portal."
            )
        if http_resp.status_code == 429:
            raise RuntimeError("Azure OpenAI rate limit exceeded (429)")
        if http_resp.status_code >= 400:
            error_detail = http_resp.text[:500]
            raise RuntimeError(
                f"Azure OpenAI error {http_resp.status_code}: {error_detail}"
            )

        data = http_resp.json()
        return self._parse_response(data)

    def _parse_response(self, data: dict) -> ProviderResponse:
        """Parse Responses API JSON into canonical ProviderResponse."""
        text_parts = []
        tool_calls = []

        for output_item in data.get("output", []):
            if output_item.get("type") == "message":
                for content in output_item.get("content", []):
                    if content.get("type") == "output_text":
                        text_parts.append(content["text"])
            elif output_item.get("type") == "function_call":
                call_id = output_item.get("call_id", output_item.get("id", ""))
                fn_name = output_item.get("name", "")
                args_str = output_item.get("arguments", "{}")
                try:
                    params = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    params = {}
                tool_calls.append(ToolCall(id=call_id, name=fn_name, params=params))

        stop_reason = "tool_use" if tool_calls else "end_turn"
        usage = data.get("usage", {})

        return ProviderResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            provider_name=self.name(),
            model=self.deployment,
            usage={
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )

    def name(self) -> str:
        return f"azure-openai ({self.deployment})"
