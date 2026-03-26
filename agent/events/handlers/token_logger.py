"""TokenLogger handler — operational token usage logging.

Listens to tool.executed, tool.truncated, tool.blocked, stage.completed
events and logs token metrics. Registered as global handler (priority 10)
so it sees everything after AuditTrail but before enforcement handlers.
"""
from __future__ import annotations

import logging

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.token_logger")


class TokenLoggerHandler:
    """Logs token usage per tool call and per stage. Never halts."""

    def __init__(self):
        self.stage_tokens: dict[str, int] = {}
        self.tool_call_log: list[dict] = []
        self.truncations = 0
        self.blocks = 0

    def __call__(self, event: Event) -> HandlerResult:
        if event.type == EventType.TOOL_EXECUTED:
            return self._log_tool_executed(event)
        elif event.type == EventType.TOOL_TRUNCATED:
            return self._log_tool_truncated(event)
        elif event.type == EventType.TOOL_BLOCKED:
            return self._log_tool_blocked(event)
        elif event.type == EventType.STAGE_COMPLETED:
            return self._log_stage_completed(event)
        return HandlerResult.skip()

    def _log_tool_executed(self, event: Event) -> HandlerResult:
        stage = event.data.get("stage", "unknown")
        tool = event.data.get("tool", "unknown")
        req_tokens = event.data.get("request_tokens", 0)
        resp_tokens = event.data.get("response_tokens", 0)

        self.stage_tokens.setdefault(stage, 0)
        self.stage_tokens[stage] += resp_tokens

        self.tool_call_log.append({
            "stage": stage, "tool": tool,
            "request_tokens": req_tokens,
            "response_tokens": resp_tokens,
            "correlation_id": event.correlation_id,
        })

        logger.info(
            "[TOKEN] %s/%s: req=%d, resp=%d, cumulative=%d",
            stage, tool, req_tokens, resp_tokens,
            self.stage_tokens[stage])

        return HandlerResult.proceed()

    def _log_tool_truncated(self, event: Event) -> HandlerResult:
        self.truncations += 1
        tool = event.data.get("tool", "unknown")
        original = event.data.get("original_tokens", 0)
        truncated_to = event.data.get("truncated_to", 0)
        logger.info("[TOKEN TRUNCATE] %s: %d → %d tok", tool, original, truncated_to)
        return HandlerResult.proceed()

    def _log_tool_blocked(self, event: Event) -> HandlerResult:
        self.blocks += 1
        tool = event.data.get("tool", "unknown")
        tokens = event.data.get("tokens", 0)
        logger.warning("[TOKEN BLOCK] %s: %d tok exceeded hard limit", tool, tokens)
        return HandlerResult.proceed()

    def _log_stage_completed(self, event: Event) -> HandlerResult:
        stage = event.data.get("stage", "unknown")
        artifact_tokens = event.data.get("artifact_tokens", 0)
        tool_calls = event.data.get("tool_calls", 0)
        total = self.stage_tokens.get(stage, 0)

        logger.info(
            "[STAGE COMPLETE] %s: artifact=%d tok, consumed=%d tok, tools=%d",
            stage, artifact_tokens, total, tool_calls)

        return HandlerResult.proceed()

    def get_report(self) -> dict:
        """Return mission-level token report."""
        total = sum(self.stage_tokens.values()) or 1
        stages = []
        for sid, tok in self.stage_tokens.items():
            tools = sum(1 for t in self.tool_call_log if t["stage"] == sid)
            stages.append({
                "stage": sid,
                "tokens_consumed": tok,
                "tool_calls": tools,
                "pct_of_total": round(tok / total * 100, 1),
            })
        return {
            "total_tokens": sum(self.stage_tokens.values()),
            "total_tool_calls": len(self.tool_call_log),
            "truncations": self.truncations,
            "blocks": self.blocks,
            "stages": stages,
        }
