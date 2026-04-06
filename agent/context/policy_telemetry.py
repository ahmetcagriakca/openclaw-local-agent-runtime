"""Policy telemetry — structured JSONL event logging for enforcer decisions."""
import json
import os
from datetime import datetime, timezone

TELEMETRY_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "policy-telemetry.jsonl"
)


def emit_policy_event(event_type: str, details: dict):
    """Append a structured policy event to JSONL log.

    Supported event_type values:
    - policy_denied
    - policy_soft_denied
    - filesystem_tool_allowed
    - path_resolution_failed
    - mutation_surface_mismatch
    - budget_exhausted
    - provider_selection (D-148)
    - provider_fallback (D-148)
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **details
    }
    os.makedirs(os.path.dirname(TELEMETRY_LOG_PATH), exist_ok=True)
    try:
        with open(TELEMETRY_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Telemetry is best-effort
