"""Correlation ID context for tracing events across a mission.

Each mission gets a correlation_id at start. All events within that
mission share the same correlation_id, enabling end-to-end tracing.
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar

_current_correlation_id: ContextVar[str] = ContextVar(
    "correlation_id", default="")


def new_correlation_id() -> str:
    """Generate and set a new correlation ID for this context."""
    cid = uuid.uuid4().hex[:12]
    _current_correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get the current correlation ID, or empty string if none set."""
    return _current_correlation_id.get()


def set_correlation_id(cid: str) -> None:
    """Explicitly set the correlation ID (e.g., from parent context)."""
    _current_correlation_id.set(cid)
