"""Simple audit logging for agent actions."""
import json
import os
from datetime import datetime, timezone

AUDIT_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "agent-audit.jsonl"
)

def log_agent_run(session_id: str, agent_id: str, user_id: str,
                  user_message: str, tool_calls: list, response: str,
                  status: str, turns_used: int, duration_ms: int,
                  approvals: list = None, artifacts: list = None):
    """Append an audit entry for an agent run."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sessionId": session_id,
        "agentId": agent_id,
        "userId": user_id,
        "userMessage": user_message[:500],
        "toolCalls": tool_calls,
        "approvals": approvals or [],
        "artifactCount": len(artifacts) if artifacts else 0,
        "artifactTypes": list(set(a["type"] for a in artifacts)) if artifacts else [],
        "response": response[:1000] if response else None,
        "turnsUsed": turns_used,
        "totalDurationMs": duration_ms,
        "status": status
    }
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
