"""Structured logging — Sprint 14B.

JSON-formatted log entries for machine-readable log processing.
Use get_logger() instead of logging.getLogger() for structured output.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_json_logging(level: str = "INFO") -> None:
    """Configure root mcc logger with JSON formatter to stderr."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())

    logger = logging.getLogger("mcc")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the mcc namespace."""
    return logging.getLogger(f"mcc.{name}")
