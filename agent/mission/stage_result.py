"""Stage Result — D-102 L1 stage boundary isolation.

Strips tool call history at stage boundaries so only the final
artifact text passes downstream to subsequent stages.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from context.token_budget import estimate_tokens

logger = logging.getLogger("mcc.stage_result")


@dataclass(frozen=True)
class StageResult:
    """Immutable output of a completed stage.

    Contains only what downstream stages need:
    - artifact_text: final assistant response text
    - token_count: total tokens consumed in this stage
    - tool_calls_made: count of tool calls (metric only, no content)
    - policy_denies: count of policy denials

    Explicitly excludes:
    - Raw message thread
    - Tool call request/response bodies
    - Intermediate assistant messages
    """
    stage_name: str
    specialist: str
    artifact_text: str
    artifact_tokens: int
    token_count: int
    tool_calls_made: int
    policy_denies: int
    duration_ms: int


def extract_stage_result(stage: dict) -> StageResult:
    """Extract a clean StageResult from a completed stage dict.

    This is the L1 isolation boundary: everything that crosses this
    function is safe to pass downstream. Tool call content, raw
    message threads, and intermediate outputs are discarded.

    Args:
        stage: completed stage dict from controller (has result,
               tool_call_count, token_report, etc.)

    Returns:
        StageResult with only artifact text and metrics.
    """
    artifact_text = stage.get("result") or ""

    # Strip any tool call JSON that may have leaked into result text
    if isinstance(artifact_text, dict):
        artifact_text = json.dumps(artifact_text, ensure_ascii=False)
    elif not isinstance(artifact_text, str):
        artifact_text = str(artifact_text)

    token_report = stage.get("token_report") or {}

    result = StageResult(
        stage_name=stage.get("id", "unknown"),
        specialist=stage.get("specialist", "unknown"),
        artifact_text=artifact_text,
        artifact_tokens=estimate_tokens(artifact_text),
        token_count=token_report.get("total_tokens", 0),
        tool_calls_made=stage.get("tool_call_count", 0),
        policy_denies=stage.get("policy_deny_count", 0),
        duration_ms=stage.get("duration_ms", 0),
    )

    logger.info(
        "[L1 ISOLATION] %s (%s): artifact=%d tok, consumed=%d tok, "
        "tools=%d, denies=%d",
        result.stage_name, result.specialist,
        result.artifact_tokens, result.token_count,
        result.tool_calls_made, result.policy_denies,
    )

    return result
