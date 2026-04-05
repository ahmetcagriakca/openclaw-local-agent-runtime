"""Mutation Audit Logger — Sprint 11 Task 11.3.

Logs every mutation operation with required fields:
timestamp, source, operation, targetId, outcome, requestId, tabId, sessionId.
Appends structured JSON lines to logs/mission-control-api.log.
"""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("mcc.mutation.audit")


def log_mutation(
    *,
    request_id: str,
    operation: str,
    target_id: str,
    outcome: str,
    tab_id: str = "",
    session_id: str = "",
    detail: str = "",
    actor: str = "",
) -> None:
    """Log a structured mutation audit entry.

    Args:
        request_id: Unique mutation request ID (req-uuid).
        operation: approve | reject | cancel | retry.
        target_id: Approval or mission ID being mutated.
        outcome: requested | accepted | applied | rejected | timed_out | error.
        tab_id: Browser tab ID (X-Tab-Id header).
        session_id: Browser session ID (X-Session-Id header).
        detail: Optional detail message.
        actor: Identity of the user who performed the mutation (B-136).
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "dashboard",
        "operation": operation,
        "targetId": target_id,
        "outcome": outcome,
        "requestId": request_id,
        "tabId": tab_id,
        "sessionId": session_id,
        "actor": actor or "unknown",
    }
    if detail:
        entry["detail"] = detail

    # Structured log line — JSON for machine parsing
    logger.info("MUTATION_AUDIT %s", json.dumps(entry, ensure_ascii=False))
