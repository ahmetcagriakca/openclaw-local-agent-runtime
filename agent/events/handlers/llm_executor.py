"""LLMExecutor handler — gated LLM call execution.

Only way to call LLM providers. Listens to llm.requested events
(after budget check). Calls the LLM and emits llm.completed.
"""
from __future__ import annotations

import logging
from typing import Callable

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.llm_executor")


class LLMExecutorHandler:
    """Executes LLM calls. Only runs on llm.requested events."""

    def __init__(self, call_fn: Callable | None = None):
        """
        Args:
            call_fn: callable(agent_id, messages, tools) -> dict
                The actual LLM call function.
                If None, returns a stub result (for testing).
        """
        self._call = call_fn
        self.calls: list[dict] = []

    def __call__(self, event: Event) -> HandlerResult:
        if event.type != EventType.LLM_REQUESTED:
            return HandlerResult.skip()

        agent_id = event.data.get("agent_id", "")
        stage = event.data.get("stage", "unknown")
        input_tokens = event.data.get("input_tokens", 0)

        logger.info("[LLM EXEC] %s (stage=%s, input=%d tok)",
                     agent_id, stage, input_tokens)

        if self._call:
            try:
                result = self._call(
                    agent_id,
                    event.data.get("messages", []),
                    event.data.get("tools", []))
                success = True
                response = result.get("response", "")
                output_tokens = result.get("output_tokens", 0)
            except Exception as e:
                success = False
                response = str(e)
                output_tokens = 0
        else:
            success = True
            response = f"[stub] {agent_id} response"
            output_tokens = 50

        call_record = {
            "agent_id": agent_id,
            "stage": stage,
            "success": success,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "correlation_id": event.correlation_id,
        }
        self.calls.append(call_record)

        return HandlerResult.proceed(
            agent_id=agent_id, success=success,
            response=response, output_tokens=output_tokens)
