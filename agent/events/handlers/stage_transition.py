"""StageTransition handler — validates and assembles context for stages.

Listens to stage.entering events. Runs L1 (StageResult extraction from
previous stages) and L2 (distance-based tiered context assembly).
Emits stage.context_ready with the assembled context.
"""
from __future__ import annotations

import logging

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.stage_transition")


class StageTransitionHandler:
    """Validates stage entry and assembles context. Can halt if context too large."""

    def __init__(self, context_budget: int = 40000):
        self.context_budget = context_budget

    def __call__(self, event: Event) -> HandlerResult:
        if event.type != EventType.STAGE_ENTERING:
            return HandlerResult.skip()

        stage = event.data.get("stage", "unknown")
        specialist = event.data.get("specialist", "unknown")
        input_tokens = event.data.get("input_tokens", 0)

        logger.info(
            "[STAGE ENTER] %s (%s): input=%d tok, budget=%d",
            stage, specialist, input_tokens, self.context_budget)

        if input_tokens > self.context_budget:
            logger.warning(
                "[STAGE BLOCKED] %s input %d > budget %d",
                stage, input_tokens, self.context_budget)
            return HandlerResult.block(
                f"Stage '{stage}' context {input_tokens} tokens "
                f"exceeds budget {self.context_budget}",
                stage=stage, input_tokens=input_tokens,
                budget=self.context_budget)

        return HandlerResult.proceed(
            stage=stage, specialist=specialist,
            input_tokens=input_tokens)


class ContextAssemblerHandler:
    """Assembles context for a stage using L2 distance-based tiers.

    Wraps the existing _format_artifact_context logic as a bus handler.
    Listens to stage.entering, returns assembled context in result data.
    """

    def __init__(self, assembler=None):
        """
        Args:
            assembler: ContextAssembler instance (from context.assembler).
                If None, handler is a no-op (for testing without full runtime).
        """
        self._assembler = assembler

    def __call__(self, event: Event) -> HandlerResult:
        if event.type != EventType.STAGE_ENTERING:
            return HandlerResult.skip()

        if self._assembler is None:
            return HandlerResult.proceed(context="")

        artifact_ids = event.data.get("artifact_ids", [])
        role = event.data.get("role", "")
        stage_id = event.data.get("stage", "")

        if not artifact_ids:
            return HandlerResult.proceed(context="")

        try:
            context_package = self._assembler.build_context_for_role(
                role=role, skill="", stage_id=stage_id,
                artifact_ids=artifact_ids)

            # L2 distance-based assembly is in controller._format_artifact_context
            # Here we return the raw package for the controller to format
            return HandlerResult.proceed(
                context_package=context_package,
                artifact_count=len(context_package))
        except Exception as e:
            logger.error("[CONTEXT] Assembly failed: %s", e)
            return HandlerResult.proceed(context="", error=str(e))
