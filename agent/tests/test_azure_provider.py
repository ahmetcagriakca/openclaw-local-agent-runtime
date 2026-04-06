"""Tests for Azure OpenAI provider (D-148)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from providers.azure_openai_provider import AzureOpenAIProvider
from providers.base import AgentResponse, ProviderResponse, TaskRequest, ToolCall


# --- Fixtures ---

MOCK_ENDPOINT = "https://test.openai.azure.com"
MOCK_DEPLOYMENT = "test-deployment"
MOCK_API_KEY = "test-key-123"
MOCK_API_VERSION = "2025-04-01-preview"


def make_provider(**overrides):
    defaults = {
        "endpoint": MOCK_ENDPOINT,
        "deployment": MOCK_DEPLOYMENT,
        "api_key": MOCK_API_KEY,
        "api_version": MOCK_API_VERSION,
    }
    defaults.update(overrides)
    return AzureOpenAIProvider(**defaults)


def mock_response_json(text="hello", tool_calls=None, usage=None):
    """Build a mock Responses API JSON body."""
    output = []
    if text:
        output.append({
            "id": "msg_001",
            "type": "message",
            "status": "completed",
            "content": [{"type": "output_text", "text": text}],
            "role": "assistant",
        })
    if tool_calls:
        for tc in tool_calls:
            output.append({
                "type": "function_call",
                "call_id": tc["id"],
                "name": tc["name"],
                "arguments": json.dumps(tc["params"]),
            })
    return {
        "id": "resp_001",
        "object": "response",
        "status": "completed",
        "model": MOCK_DEPLOYMENT,
        "output": output,
        "usage": usage or {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    }


# --- Init tests ---


class TestAzureProviderInit:
    def test_requires_endpoint(self):
        with pytest.raises(ValueError, match="endpoint required"):
            AzureOpenAIProvider(
                endpoint="", deployment=MOCK_DEPLOYMENT, api_key=MOCK_API_KEY
            )

    def test_requires_deployment(self):
        with pytest.raises(ValueError, match="deployment name required"):
            AzureOpenAIProvider(
                endpoint=MOCK_ENDPOINT, deployment="", api_key=MOCK_API_KEY
            )

    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="API key required"):
            AzureOpenAIProvider(
                endpoint=MOCK_ENDPOINT, deployment=MOCK_DEPLOYMENT, api_key=""
            )

    def test_valid_init(self):
        p = make_provider()
        assert p.endpoint == MOCK_ENDPOINT
        assert p.deployment == MOCK_DEPLOYMENT
        assert p.api_key == MOCK_API_KEY
        assert p.api_version == MOCK_API_VERSION
        assert not p.retired

    def test_name(self):
        p = make_provider()
        assert p.name() == f"azure-openai ({MOCK_DEPLOYMENT})"

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": "https://env-test.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "env-deploy",
        "AZURE_OPENAI_API_KEY": "env-key",
    })
    def test_init_from_env(self):
        p = AzureOpenAIProvider()
        assert p.endpoint == "https://env-test.openai.azure.com"
        assert p.deployment == "env-deploy"
        assert p.api_key == "env-key"

    @patch.dict("os.environ", {
        "APIM_ENDPOINT": "https://apim.openai.azure.com/openai/responses",
        "APIM_MODEL": "apim-model",
        "APIM_KEY": "apim-key",
    }, clear=False)
    def test_init_from_apim_env_fallback(self):
        """Falls back to APIM_* env vars when AZURE_OPENAI_* not set."""
        # Clear Azure-specific vars
        import os
        for k in ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY"]:
            os.environ.pop(k, None)
        p = AzureOpenAIProvider()
        assert "apim" in p.endpoint
        assert p.deployment == "apim-model"
        assert p.api_key == "apim-key"


# --- Retirement guard tests ---


class TestRetirementGuard:
    def test_no_retirement_date(self):
        p = make_provider()
        assert not p.retired

    def test_past_retirement(self):
        p = make_provider(retirement_date="2020-01-01")
        assert p.retired

    def test_future_retirement(self):
        p = make_provider(retirement_date="2099-12-31")
        assert not p.retired

    def test_near_retirement_warning(self, caplog):
        import datetime
        near = (datetime.datetime.now() + datetime.timedelta(days=15)).isoformat()
        with caplog.at_level("WARNING"):
            p = make_provider(retirement_date=near)
        assert not p.retired
        assert "retires in" in caplog.text


# --- Message conversion tests ---


class TestMessageConversion:
    def test_simple_user_message(self):
        p = make_provider()
        result = p._convert_messages_to_input([
            {"role": "user", "content": "hello"}
        ])
        assert "[User]" in result
        assert "hello" in result

    def test_system_message(self):
        p = make_provider()
        result = p._convert_messages_to_input([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "hi"},
        ])
        assert "[System]" in result
        assert "You are helpful" in result

    def test_assistant_with_tool_calls(self):
        p = make_provider()
        result = p._convert_messages_to_input([
            {"role": "assistant", "tool_calls": [
                {"function": {"name": "add", "arguments": '{"a":1}'}}
            ]},
        ])
        assert "[Assistant called add" in result

    def test_tool_result(self):
        p = make_provider()
        result = p._convert_messages_to_input([
            {"role": "tool", "content": "42", "tool_call_id": "tc_1"},
        ])
        assert "[Tool result" in result
        assert "42" in result


# --- Tool conversion tests ---


class TestCanonicalExecute:
    """Tests for the canonical execute() path — D-148 compliant."""

    @patch("providers.azure_openai_provider.requests.post")
    def test_execute_direct_path(self, mock_post):
        """execute() sends prompt directly as input, no messages conversion."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_json("hello")
        mock_post.return_value = mock_resp

        p = make_provider()
        req = TaskRequest(task_type="review", prompt="Review this code")
        result = p.execute(req)

        assert isinstance(result, ProviderResponse)
        assert result.text == "hello"
        # Verify the payload sent directly uses prompt, not messages
        call_body = mock_post.call_args[1]["json"]
        assert call_body["input"] == "Review this code"  # Direct, no [User] prefix
        assert call_body["model"] == MOCK_DEPLOYMENT

    @patch("providers.azure_openai_provider.requests.post")
    def test_execute_with_tools(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_json("ok")
        mock_post.return_value = mock_resp

        p = make_provider()
        req = TaskRequest(task_type="tool_call", prompt="Add 1+2")
        tools = [{"type": "function", "function": {
            "name": "add", "description": "add",
            "parameters": {"type": "object", "properties": {}},
        }}]
        result = p.execute(req, tools=tools)
        assert isinstance(result, ProviderResponse)

    @patch("providers.azure_openai_provider.requests.post")
    def test_execute_vs_chat_different_payloads(self, mock_post):
        """execute() and chat() send different payload formats."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_json("ok")
        mock_post.return_value = mock_resp

        p = make_provider()

        # execute() path — direct prompt
        req = TaskRequest(task_type="analysis", prompt="test prompt")
        p.execute(req)
        execute_body = mock_post.call_args[1]["json"]

        # chat() path — messages conversion
        p.chat([{"role": "user", "content": "test prompt"}], [])
        chat_body = mock_post.call_args[1]["json"]

        # execute sends raw prompt, chat converts to [User]\ntest prompt
        assert execute_body["input"] == "test prompt"
        assert "[User]" in chat_body["input"]

    @patch("providers.azure_openai_provider.requests.post")
    def test_base_provider_execute_default(self, mock_post):
        """Base AgentProvider.execute() delegates to chat() for compat."""
        from providers.base import AgentProvider
        provider = AgentProvider()
        req = TaskRequest(task_type="test", prompt="hello")
        with pytest.raises(NotImplementedError):
            provider.execute(req)


class TestToolConversion:
    def test_function_tool(self):
        p = make_provider()
        tools = [{"type": "function", "function": {
            "name": "add",
            "description": "Add numbers",
            "parameters": {"type": "object", "properties": {"a": {"type": "number"}}},
        }}]
        result = p._convert_tools(tools)
        assert len(result) == 1
        assert result[0]["name"] == "add"
        assert result[0]["type"] == "function"
        assert "parameters" in result[0]


# --- Chat tests ---


class TestChat:
    @patch("providers.azure_openai_provider.requests.post")
    def test_text_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_json("hello world")
        mock_post.return_value = mock_resp

        p = make_provider()
        result = p.chat([{"role": "user", "content": "hi"}], [])

        assert isinstance(result, AgentResponse)
        assert result.text == "hello world"
        assert result.stop_reason == "end_turn"
        assert result.tool_calls == []

    @patch("providers.azure_openai_provider.requests.post")
    def test_canonical_response_via_execute(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_json("hello")
        mock_post.return_value = mock_resp

        p = make_provider()
        req = TaskRequest(task_type="review", prompt="hi")
        result = p.execute(req)

        assert isinstance(result, ProviderResponse)
        assert result.text == "hello"
        assert result.provider_name == f"azure-openai ({MOCK_DEPLOYMENT})"
        assert result.model == MOCK_DEPLOYMENT
        assert result.usage["input_tokens"] == 10
        assert result.usage["output_tokens"] == 5

    @patch("providers.azure_openai_provider.requests.post")
    def test_tool_call_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_json(
            text=None,
            tool_calls=[{"id": "tc_1", "name": "add", "params": {"a": 1, "b": 2}}],
        )
        mock_post.return_value = mock_resp

        p = make_provider()
        result = p.chat([{"role": "user", "content": "add 1+2"}], [
            {"type": "function", "function": {
                "name": "add", "description": "add",
                "parameters": {"type": "object", "properties": {}},
            }}
        ])

        assert result.stop_reason == "tool_use"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "add"
        assert result.tool_calls[0].params == {"a": 1, "b": 2}

    @patch("providers.azure_openai_provider.requests.post")
    def test_min_tokens_enforced(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_json("ok")
        mock_post.return_value = mock_resp

        p = make_provider()
        p.chat([{"role": "user", "content": "hi"}], [], max_tokens=5)

        call_body = mock_post.call_args[1]["json"]
        assert call_body["max_output_tokens"] >= 16


# --- Error handling tests ---


class TestErrorHandling:
    @patch("providers.azure_openai_provider.requests.post")
    def test_401_auth_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        p = make_provider()
        with pytest.raises(PermissionError, match="401"):
            p.chat([{"role": "user", "content": "hi"}], [])

    @patch("providers.azure_openai_provider.requests.post")
    def test_404_deployment_not_found(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_post.return_value = mock_resp

        p = make_provider()
        with pytest.raises(ValueError, match="not found"):
            p.chat([{"role": "user", "content": "hi"}], [])

    @patch("providers.azure_openai_provider.requests.post")
    def test_429_rate_limit(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        p = make_provider()
        with pytest.raises(RuntimeError, match="rate limit"):
            p.chat([{"role": "user", "content": "hi"}], [])

    @patch("providers.azure_openai_provider.requests.post")
    def test_timeout(self, mock_post):
        import requests as req
        mock_post.side_effect = req.Timeout()

        p = make_provider()
        with pytest.raises(TimeoutError):
            p.chat([{"role": "user", "content": "hi"}], [])

    @patch("providers.azure_openai_provider.requests.post")
    def test_connection_error(self, mock_post):
        import requests as req
        mock_post.side_effect = req.ConnectionError()

        p = make_provider()
        with pytest.raises(ConnectionError):
            p.chat([{"role": "user", "content": "hi"}], [])

    @patch("providers.azure_openai_provider.requests.post")
    def test_generic_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        p = make_provider()
        with pytest.raises(RuntimeError, match="500"):
            p.chat([{"role": "user", "content": "hi"}], [])


# --- Canonical types tests ---


class TestCanonicalTypes:
    def test_task_request_defaults(self):
        req = TaskRequest(task_type="review", prompt="test")
        assert req.risk_tier == "low"
        assert req.tools_required == []
        assert req.provider_preference is None

    def test_task_request_full(self):
        req = TaskRequest(
            task_type="implementation",
            prompt="build feature",
            tools_required=["file_read", "file_write"],
            risk_tier="high",
            provider_preference="azure",
        )
        assert req.task_type == "implementation"
        assert len(req.tools_required) == 2
        assert req.risk_tier == "high"

    def test_provider_response_to_agent_response(self):
        pr = ProviderResponse(
            text="result",
            tool_calls=[ToolCall(id="1", name="fn", params={})],
            stop_reason="tool_use",
            provider_name="azure-openai (test)",
            model="test",
            usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        )
        ar = pr.to_agent_response()
        assert isinstance(ar, AgentResponse)
        assert ar.text == "result"
        assert len(ar.tool_calls) == 1
        assert ar.stop_reason == "tool_use"

    def test_provider_response_defaults(self):
        pr = ProviderResponse()
        assert pr.text is None
        assert pr.tool_calls == []
        assert pr.stop_reason == "end_turn"
        assert pr.provider_name == ""
        assert pr.usage == {}


# --- Factory tests ---


class TestFactory:
    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": MOCK_ENDPOINT,
        "AZURE_OPENAI_API_KEY": MOCK_API_KEY,
    })
    def test_create_azure_provider(self):
        from providers.factory import create_provider
        provider, config = create_provider("azure-general")
        assert isinstance(provider, AzureOpenAIProvider)
        assert config["provider"] == "azure-openai"

    def test_create_gpt_provider_config(self):
        from providers.factory import load_agent_config
        config = load_agent_config()
        assert "gpt-general" in config["agents"]
        assert config["agents"]["gpt-general"]["provider"] == "gpt"

    def test_disabled_agent(self):
        from providers.factory import create_provider
        with pytest.raises(ValueError, match="disabled"):
            # Temporarily disable an agent — mock the config
            with patch("providers.factory.load_agent_config", return_value={
                "defaultAgent": "test",
                "agents": {"test": {"provider": "mock", "enabled": False}},
            }):
                create_provider("test")

    def test_unknown_agent(self):
        from providers.factory import create_provider
        with pytest.raises(ValueError, match="Unknown agent"):
            create_provider("nonexistent-agent")

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": MOCK_ENDPOINT,
        "AZURE_OPENAI_API_KEY": MOCK_API_KEY,
    })
    def test_default_agent_is_azure(self):
        from providers.factory import create_provider
        provider, config = create_provider()
        assert isinstance(provider, AzureOpenAIProvider)
