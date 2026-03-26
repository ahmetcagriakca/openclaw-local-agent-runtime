"""Token budget enforcement — D-102.

Estimates token counts and enforces budget limits to prevent
context overflow in multi-stage missions.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("mcc.token_budget")


def estimate_tokens(text: str) -> int:
    """Estimate token count from text. ~4 chars per token for English/mixed."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class BudgetConfig:
    """Token budget limits."""
    tool_response_limit: int = 10_000        # auto-truncate above this
    tool_response_hard_limit: int = 50_000   # block above this
    stage_input_limit: int = 50_000          # warn above this
    stage_input_hard_limit: int = 150_000    # would fail at API anyway
    mission_total_limit: int = 500_000       # hard abort


@dataclass
class TokenTracker:
    """Tracks token usage across a mission."""
    mission_id: str
    stage_tokens: dict = field(default_factory=dict)
    tool_call_log: list = field(default_factory=list)
    truncations: int = 0
    blocks: int = 0

    def log_tool_call(self, stage_id: str, tool_name: str,
                      request_tokens: int, response_tokens: int,
                      truncated: bool = False, blocked: bool = False):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage_id,
            "tool": tool_name,
            "request_tokens": request_tokens,
            "response_tokens": response_tokens,
            "truncated": truncated,
            "blocked": blocked,
        }
        self.tool_call_log.append(entry)

        if stage_id not in self.stage_tokens:
            self.stage_tokens[stage_id] = 0
        self.stage_tokens[stage_id] += response_tokens

        if truncated:
            self.truncations += 1
        if blocked:
            self.blocks += 1

        action = " [TRUNCATED]" if truncated else " [BLOCKED]" if blocked else ""
        logger.info(
            "[TOKEN] %s/%s: req=%d, resp=%d, cumulative=%d%s",
            stage_id, tool_name, request_tokens, response_tokens,
            self.stage_tokens[stage_id], action
        )

    def log_stage_complete(self, stage_id: str, artifact_tokens: int,
                           tool_calls: int):
        total = self.stage_tokens.get(stage_id, 0)
        logger.info(
            "[STAGE COMPLETE] %s: artifact=%d tok, consumed=%d tok, tools=%d",
            stage_id, artifact_tokens, total, tool_calls
        )

    @property
    def mission_total(self) -> int:
        return sum(self.stage_tokens.values())

    def get_report(self) -> dict:
        stages = []
        total = self.mission_total or 1
        for sid, tok in self.stage_tokens.items():
            tools = sum(1 for t in self.tool_call_log if t["stage"] == sid)
            stages.append({
                "stage": sid,
                "tokens_consumed": tok,
                "tool_calls": tools,
                "pct_of_total": round(tok / total * 100, 1),
            })
        return {
            "mission_id": self.mission_id,
            "total_tokens": self.mission_total,
            "total_tool_calls": len(self.tool_call_log),
            "truncations": self.truncations,
            "blocks": self.blocks,
            "stages": stages,
        }


def truncate_tool_response(response_text: str, config: BudgetConfig,
                           tool_name: str = "") -> tuple[str, bool, bool]:
    """Apply budget limits to a tool response.

    Returns: (text, was_truncated, was_blocked)
    """
    tokens = estimate_tokens(response_text)

    if tokens <= config.tool_response_limit:
        return response_text, False, False

    if tokens > config.tool_response_hard_limit:
        logger.warning(
            "[BUDGET BLOCK] %s returned %d tokens (hard limit: %d). Blocking.",
            tool_name, tokens, config.tool_response_hard_limit
        )
        return (
            f"[BLOCKED: Tool response too large ({tokens} tokens, limit {config.tool_response_hard_limit}). "
            f"Use a lighter tool or narrow your query.]"
        ), False, True

    # Auto-truncate
    char_limit = config.tool_response_limit * 4  # ~4 chars per token
    truncated = response_text[:char_limit]
    logger.info(
        "[BUDGET TRUNCATE] %s: %d tok → %d tok",
        tool_name, tokens, config.tool_response_limit
    )
    return (
        truncated + f"\n\n[Response truncated from ~{tokens} to ~{config.tool_response_limit} tokens]"
    ), True, False
