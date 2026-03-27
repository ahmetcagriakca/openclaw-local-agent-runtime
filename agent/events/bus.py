"""EventBus — core dispatcher for D-102 event-driven governance.

All governance actions (tool permission checks, budget enforcement,
token logging, audit trail) flow through this bus. Handlers are
registered in priority order and can halt event propagation.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

logger = logging.getLogger("mcc.eventbus")


@dataclass(frozen=True)
class Event:
    """Immutable event dispatched through the bus."""
    type: str
    data: dict
    source: str
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_id: str | None = None

    def child(self, event_type: str, data: dict, source: str) -> Event:
        """Create a child event sharing the same correlation_id."""
        return Event(
            type=event_type,
            data=data,
            source=source,
            correlation_id=self.correlation_id,
            parent_id=self.correlation_id,
        )


@dataclass
class HandlerResult:
    """Result returned by a handler after processing an event."""
    handled: bool = True
    halt: bool = False
    data: dict = field(default_factory=dict)
    error: str | None = None

    @staticmethod
    def proceed(**data) -> HandlerResult:
        return HandlerResult(handled=True, halt=False, data=data)

    @staticmethod
    def block(reason: str, **data) -> HandlerResult:
        return HandlerResult(handled=True, halt=True, data=data, error=reason)

    @staticmethod
    def skip() -> HandlerResult:
        return HandlerResult(handled=False, halt=False)


# Handler type: callable(Event) -> HandlerResult
Handler = Callable[[Event], HandlerResult]


class EventBus:
    """Central event dispatcher.

    Handlers are registered with a priority (lower = earlier).
    When an event is emitted, handlers run in priority order.
    If any handler returns halt=True, remaining handlers are skipped.

    Thread safety: not thread-safe. Designed for single-threaded
    mission execution within one controller instance.
    """

    def __init__(self):
        self._handlers: dict[str, list[tuple[int, str, Handler]]] = defaultdict(list)
        self._global_handlers: list[tuple[int, str, Handler]] = []
        self._history: list[tuple[Event, list[HandlerResult]]] = []
        self._max_history = 10000

    def on(self, event_type: str, handler: Handler, *,
           priority: int = 100, name: str = "") -> None:
        """Register a handler for a specific event type."""
        handler_name = name or getattr(handler, "__name__", str(handler))
        self._handlers[event_type].append((priority, handler_name, handler))
        self._handlers[event_type].sort(key=lambda x: x[0])

    def on_all(self, handler: Handler, *, priority: int = 0,
               name: str = "") -> None:
        """Register a handler that receives ALL events (e.g., audit trail)."""
        handler_name = name or getattr(handler, "__name__", str(handler))
        self._global_handlers.append((priority, handler_name, handler))
        self._global_handlers.sort(key=lambda x: x[0])

    def emit(self, event: Event) -> list[HandlerResult]:
        """Dispatch event to registered handlers.

        Global handlers run first (audit, logging), then type-specific.
        If any handler returns halt=True, propagation stops.
        Returns list of all handler results.
        """
        results: list[HandlerResult] = []

        # Global handlers first (audit trail, logging — should never halt)
        for priority, name, handler in self._global_handlers:
            try:
                result = handler(event)
                results.append(result)
                if result.halt:
                    logger.warning(
                        "[BUS] Global handler %s halted %s (cid=%s)",
                        name, event.type, event.correlation_id)
                    break
            except Exception as e:
                logger.error(
                    "[BUS] Global handler %s error on %s: %s",
                    name, event.type, e)
                results.append(HandlerResult(
                    handled=False, error=f"handler error: {e}"))

        # Type-specific handlers
        if not any(r.halt for r in results):
            for priority, name, handler in self._handlers.get(event.type, []):
                try:
                    result = handler(event)
                    results.append(result)
                    if result.halt:
                        logger.info(
                            "[BUS] Handler %s halted %s: %s (cid=%s)",
                            name, event.type, result.error,
                            event.correlation_id)
                        break
                except Exception as e:
                    logger.error(
                        "[BUS] Handler %s error on %s: %s",
                        name, event.type, e)
                    results.append(HandlerResult(
                        handled=False, error=f"handler error: {e}"))

        # Record in history
        if len(self._history) < self._max_history:
            self._history.append((event, results))

        return results

    def was_halted(self, results: list[HandlerResult]) -> bool:
        """Check if any handler halted the event."""
        return any(r.halt for r in results)

    def history(self, event_type: str | None = None,
                correlation_id: str | None = None,
                limit: int = 100) -> list[tuple[Event, list[HandlerResult]]]:
        """Query event history with optional filters."""
        items = self._history
        if event_type:
            items = [(e, r) for e, r in items if e.type == event_type]
        if correlation_id:
            items = [(e, r) for e, r in items if e.correlation_id == correlation_id]
        return items[-limit:]

    @property
    def handler_count(self) -> int:
        total = len(self._global_handlers)
        for handlers in self._handlers.values():
            total += len(handlers)
        return total

    def registered_types(self) -> list[str]:
        """List all event types with registered handlers."""
        return sorted(self._handlers.keys())

    def clear(self) -> None:
        """Reset bus state. For testing only."""
        self._handlers.clear()
        self._global_handlers.clear()
        self._history.clear()
