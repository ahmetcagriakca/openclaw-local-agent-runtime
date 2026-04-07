"""Provider factory — creates the right provider based on config."""
import json
import os


def load_agent_config() -> dict:
    """Load agent configuration from agent-config.json."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent-config.json")
    if not os.path.exists(config_path):
        return {
            "defaultAgent": "gpt-general",
            "agents": {
                "gpt-general": {
                    "provider": "gpt",
                    "model": "gpt-4o",
                    "apiKeyEnv": "OPENAI_API_KEY",
                    "maxTokens": 4096,
                    "maxTurns": 10,
                    "enabled": True
                }
            }
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_provider(agent_id: str = None):
    """Create a provider instance for the given agent ID.

    Returns: (provider, agent_config)
    """
    config = load_agent_config()

    if agent_id is None:
        agent_id = config.get("defaultAgent", "gpt-general")

    agents = config.get("agents", {})
    if agent_id not in agents:
        raise ValueError(f"Unknown agent: {agent_id}. Available: {list(agents.keys())}")

    agent_config = agents[agent_id]

    if not agent_config.get("enabled", False):
        raise ValueError(f"Agent '{agent_id}' is disabled. Enable it in agent-config.json")

    provider_type = agent_config.get("provider", "gpt")
    model = agent_config.get("model")

    if provider_type == "azure-openai":
        from .azure_openai_provider import AzureOpenAIProvider
        api_key = os.environ.get(agent_config.get("apiKeyEnv", "AZURE_OPENAI_API_KEY"))
        endpoint_env = agent_config.get("endpointEnv", "AZURE_OPENAI_ENDPOINT")
        endpoint = os.environ.get(endpoint_env)
        api_version = agent_config.get("apiVersion", "2025-04-01-preview")
        timeout = agent_config.get("timeoutSeconds", 120)
        retirement_date = agent_config.get("retirementDate")
        return AzureOpenAIProvider(
            endpoint=endpoint,
            deployment=model,
            api_key=api_key,
            api_version=api_version,
            retirement_date=retirement_date,
            timeout=timeout,
        ), agent_config

    elif provider_type == "gpt":
        from .gpt_provider import GPTProvider
        api_key = os.environ.get(agent_config.get("apiKeyEnv", "OPENAI_API_KEY"))
        return GPTProvider(model=model, api_key=api_key), agent_config

    elif provider_type == "claude":
        from .claude_provider import ClaudeProvider
        api_key = os.environ.get(agent_config.get("apiKeyEnv", "ANTHROPIC_API_KEY"))
        return ClaudeProvider(model=model, api_key=api_key), agent_config

    elif provider_type == "ollama":
        from .ollama_provider import OllamaProvider
        base_url = agent_config.get("baseUrl", "http://localhost:11434")
        return OllamaProvider(model=model, base_url=base_url), agent_config

    elif provider_type == "mock":
        from .mock_provider import MockProvider
        return MockProvider(), agent_config

    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
