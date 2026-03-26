"""BudgetEnforcer handler — 4-tier token budget enforcement.

Listens to tool.executed events and enforces token limits:
- Per tool response: >10K truncate, >50K block
- Per stage cumulative: warning at 100K, halt at 150K
- Per mission total: hard abort at 500K

Uses BudgetConfig from context.token_budget.
"""
from __future__ import annotations

import logging

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.budget")


class BudgetEnforcerHandler:
    """4-tier token budget enforcement. Can halt on budget violation."""

    def __init__(self, config=None):
        if config is None:
            from context.token_budget import BudgetConfig
            config = BudgetConfig()
        self.config = config
        self.stage_totals: dict[str, int] = {}
        self.mission_total = 0

    def __call__(self, event: Event) -> HandlerResult:
        if event.type == EventType.TOOL_EXECUTED:
            return self._check_tool_response(event)
        elif event.type == EventType.STAGE_CONTEXT_READY:
            return self._check_stage_input(event)
        return HandlerResult.skip()

    def _check_tool_response(self, event: Event) -> HandlerResult:
        resp_tokens = event.data.get("response_tokens", 0)
        tool = event.data.get("tool", "unknown")
        stage = event.data.get("stage", "unknown")

        # Track cumulative
        self.stage_totals.setdefault(stage, 0)
        self.stage_totals[stage] += resp_tokens
        self.mission_total += resp_tokens

        # Tier 1: Per-tool response block
        if resp_tokens > self.config.tool_response_hard_limit:
            logger.warning(
                "[BUDGET BLOCK] %s: %d tok > hard limit %d",
                tool, resp_tokens, self.config.tool_response_hard_limit)
            return HandlerResult.block(
                f"Tool response too large: {resp_tokens} tokens "
                f"(limit {self.config.tool_response_hard_limit})",
                tool=tool, tokens=resp_tokens, action="block")

        # Tier 2: Per-tool response truncate (signal, don't halt)
        if resp_tokens > self.config.tool_response_limit:
            logger.info(
                "[BUDGET TRUNCATE] %s: %d tok > soft limit %d",
                tool, resp_tokens, self.config.tool_response_limit)
            return HandlerResult.proceed(
                tool=tool, tokens=resp_tokens, action="truncate",
                truncate_to=self.config.tool_response_limit)

        # Tier 3: Stage cumulative check
        stage_total = self.stage_totals[stage]
        if stage_total > self.config.stage_input_hard_limit:
            logger.warning(
                "[BUDGET STAGE] %s cumulative %d > hard limit %d",
                stage, stage_total, self.config.stage_input_hard_limit)
            return HandlerResult.block(
                f"Stage '{stage}' cumulative {stage_total} tokens "
                f"exceeds limit {self.config.stage_input_hard_limit}",
                stage=stage, tokens=stage_total, action="stage_halt")

        # Tier 4: Mission total check
        if self.mission_total > self.config.mission_total_limit:
            logger.warning(
                "[BUDGET MISSION] total %d > limit %d",
                self.mission_total, self.config.mission_total_limit)
            return HandlerResult.block(
                f"Mission total {self.mission_total} tokens "
                f"exceeds limit {self.config.mission_total_limit}",
                mission_total=self.mission_total, action="mission_abort")

        return HandlerResult.proceed()

    def _check_stage_input(self, event: Event) -> HandlerResult:
        input_tokens = event.data.get("input_tokens", 0)
        stage = event.data.get("stage", "unknown")

        if input_tokens > self.config.stage_input_hard_limit:
            return HandlerResult.block(
                f"Stage input {input_tokens} tokens exceeds "
                f"hard limit {self.config.stage_input_hard_limit}",
                stage=stage, input_tokens=input_tokens)

        if input_tokens > self.config.stage_input_limit:
            logger.warning(
                "[BUDGET WARNING] Stage %s input %d > soft limit %d",
                stage, input_tokens, self.config.stage_input_limit)

        return HandlerResult.proceed()
