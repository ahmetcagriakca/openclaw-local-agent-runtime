"""Tenant Guardrails — Phase 7 Sprint 30.

Usage counters + quota enforcement for missions and API calls.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mcc.guardrails")


@dataclass
class UsageCounters:
    missions_created: int = 0
    api_calls: int = 0
    llm_tokens_used: int = 0
    last_reset: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GuardrailConfig:
    max_missions_per_day: int = 100
    max_api_calls_per_hour: int = 10000
    max_llm_tokens_per_day: int = 1000000
    soft_stop_threshold: float = 0.8  # warn at 80%
    hard_stop_enabled: bool = True


class GuardrailService:
    """Enforces usage quotas and budget limits."""

    def __init__(self, config_path: Optional[Path] = None):
        self._counters = UsageCounters()
        self._config = GuardrailConfig()
        if config_path and config_path.exists():
            self._load_config(config_path)

    def _load_config(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in ("max_missions_per_day", "max_api_calls_per_hour",
                        "max_llm_tokens_per_day", "soft_stop_threshold", "hard_stop_enabled"):
                if key in data:
                    setattr(self._config, key, data[key])
        except (json.JSONDecodeError, OSError):
            pass

    def record_mission(self) -> dict:
        """Record a mission creation. Returns status."""
        self._counters.missions_created += 1
        return self._check("missions_created", self._counters.missions_created,
                           self._config.max_missions_per_day)

    def record_api_call(self) -> dict:
        """Record an API call."""
        self._counters.api_calls += 1
        return self._check("api_calls", self._counters.api_calls,
                           self._config.max_api_calls_per_hour)

    def record_tokens(self, count: int) -> dict:
        """Record LLM token usage."""
        self._counters.llm_tokens_used += count
        return self._check("llm_tokens", self._counters.llm_tokens_used,
                           self._config.max_llm_tokens_per_day)

    def _check(self, metric: str, current: int, limit: int) -> dict:
        ratio = current / limit if limit > 0 else 0
        if ratio >= 1.0 and self._config.hard_stop_enabled:
            logger.warning("HARD STOP: %s at %d/%d", metric, current, limit)
            return {"status": "denied", "metric": metric, "current": current, "limit": limit}
        if ratio >= self._config.soft_stop_threshold:
            logger.info("SOFT STOP warning: %s at %.0f%%", metric, ratio * 100)
            return {"status": "warning", "metric": metric, "current": current, "limit": limit}
        return {"status": "ok", "metric": metric, "current": current, "limit": limit}

    def get_usage(self) -> dict:
        return {
            "missions_created": self._counters.missions_created,
            "api_calls": self._counters.api_calls,
            "llm_tokens_used": self._counters.llm_tokens_used,
            "last_reset": self._counters.last_reset,
        }

    def reset(self) -> None:
        self._counters = UsageCounters()
