"""Session model — Sprint 16: operator identity + session tracking.

Task 16.19: Foundation for future multi-user support.
No authentication flow — just identity tracking.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Session:
    """Operator session — tracks who is using the system."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    operator: str = field(default_factory=lambda: os.environ.get("VEZIR_OPERATOR", "akca"))
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "api"  # api, telegram, cli

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "operator": self.operator,
            "started_at": self.started_at,
            "source": self.source,
        }


# Global session (single-operator for now)
_current_session: Session | None = None


def get_operator() -> str:
    """Get current operator name."""
    return os.environ.get("VEZIR_OPERATOR", "akca")


def get_session() -> Session:
    """Get or create current session."""
    global _current_session
    if _current_session is None:
        _current_session = Session()
    return _current_session


def new_session(source: str = "api") -> Session:
    """Create a new session."""
    global _current_session
    _current_session = Session(source=source)
    return _current_session
