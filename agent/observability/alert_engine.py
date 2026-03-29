"""Alert Rules Engine — Sprint 16: configurable thresholds.

Task 16.6: Evaluates rules on EventBus events, fires alerts.
Task 16.9: Default alert rules.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from events.bus import Event, HandlerResult
from events.catalog import EventType
from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.observability.alerts")

# Default alert rules (D-107)
DEFAULT_RULES: list[dict] = [
    {
        "id": "A-001",
        "name": "Budget gates per mission",
        "event_types": [EventType.APPROVAL_REQUESTED],
        "condition": "count_per_mission",
        "threshold": 3,
        "severity": "warning",
        "notify": ["log", "telegram"],
        "enabled": True,
    },
    {
        "id": "A-002",
        "name": "Stage token percentage",
        "event_types": [EventType.STAGE_COMPLETED],
        "condition": "stage_token_pct",
        "threshold": 50,
        "severity": "warning",
        "notify": ["log"],
        "enabled": True,
    },
    {
        "id": "A-003",
        "name": "Rework count per stage",
        "event_types": [EventType.STAGE_REWORK],
        "condition": "count_per_mission",
        "threshold": 3,
        "severity": "warning",
        "notify": ["log", "telegram"],
        "enabled": True,
    },
    {
        "id": "A-004",
        "name": "Bypass detected",
        "event_types": [],
        "condition": "any",
        "threshold": 1,
        "severity": "critical",
        "notify": ["log", "telegram"],
        "enabled": True,
    },
    {
        "id": "A-005",
        "name": "Audit integrity failure",
        "event_types": [],
        "condition": "any",
        "threshold": 1,
        "severity": "critical",
        "notify": ["log", "telegram"],
        "enabled": True,
    },
    {
        "id": "A-006",
        "name": "Mission total tokens approaching limit",
        "event_types": [EventType.BUDGET_WARNING],
        "condition": "count_per_mission",
        "threshold": 1,
        "severity": "warning",
        "notify": ["log", "telegram"],
        "enabled": True,
    },
    {
        "id": "A-007",
        "name": "Tool response blocked by budget",
        "event_types": [EventType.BUDGET_EXCEEDED],
        "condition": "any",
        "threshold": 1,
        "severity": "info",
        "notify": ["log"],
        "enabled": True,
    },
    {
        "id": "A-008",
        "name": "Mission aborted",
        "event_types": [EventType.MISSION_ABORTED],
        "condition": "any",
        "threshold": 1,
        "severity": "warning",
        "notify": ["log", "telegram"],
        "enabled": True,
    },
    {
        "id": "A-009",
        "name": "Consecutive mission failures",
        "event_types": [EventType.MISSION_FAILED],
        "condition": "consecutive",
        "threshold": 2,
        "severity": "warning",
        "notify": ["log", "telegram"],
        "enabled": True,
    },
]


class Alert:
    """A fired alert instance."""

    def __init__(self, rule_id: str, rule_name: str, severity: str,
                 mission_id: str, details: dict):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.severity = severity
        self.mission_id = mission_id
        self.details = details
        self.ts = datetime.now(timezone.utc).isoformat()
        self.acknowledged = False

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "mission_id": self.mission_id,
            "details": self.details,
            "ts": self.ts,
            "acknowledged": self.acknowledged,
        }


class AlertEngine:
    """Evaluates alert rules on EventBus events.

    Register with bus.on_all(engine, priority=5, name="AlertEngine").
    """

    def __init__(self, notifier=None, rules: list[dict] | None = None,
                 config_path: Path | str | None = None):
        self._rules = list(rules or DEFAULT_RULES)
        self._notifier = notifier
        self._lock = threading.Lock()

        # Counters per mission for threshold tracking
        self._mission_counters: dict[str, dict[str, int]] = {}
        self._consecutive_failures: int = 0

        # Alert history
        self._active: list[Alert] = []
        self._history: list[Alert] = []

        # Config persistence
        if config_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            config_path = root / "config" / "alert-rules.json"
        self._config_path = Path(config_path)
        self._load_config()

    def _load_config(self) -> None:
        if self._config_path.exists():
            try:
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
                self._rules = data.get("rules", self._rules)
            except Exception as e:
                logger.debug("alert config load: %s", e)

    def _save_config(self) -> None:
        try:
            atomic_write_json(self._config_path, {"rules": self._rules})
        except Exception as e:
            logger.error("Failed to save alert config: %s", e)

    def __call__(self, event: Event) -> HandlerResult:
        """Evaluate rules against the event."""
        cid = event.correlation_id
        mid = event.data.get("mission_id", cid)

        with self._lock:
            # Track counters
            if cid not in self._mission_counters:
                self._mission_counters[cid] = {}
            counters = self._mission_counters[cid]
            counters[event.type] = counters.get(event.type, 0) + 1

            # Track consecutive failures
            if event.type == EventType.MISSION_FAILED:
                self._consecutive_failures += 1
            elif event.type == EventType.MISSION_COMPLETED:
                self._consecutive_failures = 0

        # Evaluate each rule
        for rule in self._rules:
            if not rule.get("enabled", True):
                continue
            event_types = rule.get("event_types", [])
            if event_types and event.type not in event_types:
                continue

            fired = self._evaluate(rule, event, counters)
            if fired:
                alert = Alert(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    severity=rule.get("severity", "info"),
                    mission_id=mid,
                    details={
                        "event_type": event.type,
                        "trigger_value": counters.get(event.type, 0),
                        "threshold": rule.get("threshold", 0),
                        **{k: v for k, v in event.data.items()
                           if isinstance(v, (str, int, float, bool))},
                    },
                )
                self._fire(alert, rule)

        return HandlerResult.proceed()

    def _evaluate(self, rule: dict, event: Event, counters: dict) -> bool:
        condition = rule.get("condition", "any")
        threshold = rule.get("threshold", 1)

        if condition == "any":
            return True
        elif condition == "count_per_mission":
            count = counters.get(event.type, 0)
            return count >= threshold
        elif condition == "consecutive":
            return self._consecutive_failures >= threshold
        elif condition == "stage_token_pct":
            total = event.data.get("total_consumed", 0)
            mission_total = event.data.get("mission_tokens", 300000)
            if mission_total > 0:
                pct = (total / mission_total) * 100
                return pct >= threshold
        return False

    def _fire(self, alert: Alert, rule: dict) -> None:
        with self._lock:
            self._active.append(alert)
            self._history.append(alert)
            # Cap history
            if len(self._history) > 500:
                self._history = self._history[-500:]

        logger.warning("ALERT [%s] %s: %s (mission=%s)",
                       alert.severity.upper(), alert.rule_id,
                       alert.rule_name, alert.mission_id)

        # Notify
        if self._notifier and "telegram" in rule.get("notify", []):
            try:
                self._notifier.send_alert(alert)
            except Exception as e:
                logger.error("Alert notification failed: %s", e)

    # ── Rule CRUD ──────────────────────────────────────────────

    def get_rules(self) -> list[dict]:
        return list(self._rules)

    def get_rule(self, rule_id: str) -> dict | None:
        for r in self._rules:
            if r["id"] == rule_id:
                return r
        return None

    def update_rule(self, rule_id: str, updates: dict) -> dict | None:
        for r in self._rules:
            if r["id"] == rule_id:
                r.update(updates)
                self._save_config()
                return r
        return None

    def add_rule(self, rule: dict) -> dict:
        self._rules.append(rule)
        self._save_config()
        return rule

    # ── Query ──────────────────────────────────────────────────

    def get_active(self, user_id: str | None = None) -> list[dict]:
        """Get active alerts, optionally filtered by user namespace."""
        with self._lock:
            alerts = [a.to_dict() for a in self._active if not a.acknowledged]
        if user_id:
            alerts = [a for a in alerts if a.get("user_id") in (None, "", user_id)]
        return alerts

    def get_history(self, from_ts: str | None = None,
                    to_ts: str | None = None,
                    user_id: str | None = None) -> list[dict]:
        """Get alert history, optionally filtered by user namespace."""
        with self._lock:
            items = self._history[:]
        if from_ts:
            items = [a for a in items if a.ts >= from_ts]
        if to_ts:
            items = [a for a in items if a.ts <= to_ts]
        alerts = [a.to_dict() for a in items]
        if user_id:
            alerts = [a for a in alerts if a.get("user_id") in (None, "", user_id)]
        return alerts

    def acknowledge(self, index: int) -> bool:
        with self._lock:
            if 0 <= index < len(self._active):
                self._active[index].acknowledged = True
                return True
        return False

    @classmethod
    def handled_event_types(cls) -> set[str]:
        """All event types that can trigger alerts."""
        types = set()
        for rule in DEFAULT_RULES:
            types.update(rule.get("event_types", []))
        return types
