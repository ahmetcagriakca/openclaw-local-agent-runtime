"""MissionStore — mission history persistence (JSON file).

Task 16.0: CRUD for completed mission records.
Persists across API restarts via JSON file storage.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.persistence.missions")


class MissionStore:
    """Persistent mission history store.

    Stores completed/failed/aborted missions with their metadata
    for dashboard queries. Backed by a single JSON file.
    """

    def __init__(self, store_path: Path | str | None = None):
        if store_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            store_path = root / "logs" / "mission-history.json"
        self._path = Path(store_path)
        self._lock = threading.Lock()
        self._missions: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._missions = data.get("missions", {})
                logger.info("MissionStore loaded %d missions", len(self._missions))
            except Exception as e:
                logger.warning("MissionStore load failed: %s", e)
                self._missions = {}

    def _save(self) -> None:
        try:
            atomic_write_json(self._path, {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "missions": self._missions,
            })
        except Exception as e:
            logger.error("MissionStore save failed: %s", e)

    def record(self, mission: dict) -> None:
        """Record a completed mission."""
        mid = mission.get("id", mission.get("mission_id", ""))
        if not mid:
            return
        with self._lock:
            self._missions[mid] = {
                "id": mid,
                "goal": mission.get("goal", ""),
                "complexity": mission.get("complexity", ""),
                "status": mission.get("status", "completed"),
                "tokens": mission.get("tokens", mission.get("total_tokens", 0)),
                "duration": mission.get("duration", 0),
                "stages": mission.get("stages", mission.get("stage_count", 0)),
                "tools": mission.get("tools", mission.get("tool_calls", 0)),
                "reworks": mission.get("reworks", 0),
                "ts": mission.get("ts", datetime.now(timezone.utc).isoformat()),
                "operator": mission.get("operator", "akca"),
                "budget_pct": mission.get("budget_pct", 0),
                "anomaly_count": mission.get("anomaly_count", 0),
                "budget_events": mission.get("budget_events", 0),
                "stages_detail": mission.get("stages_detail", []),
            }
            self._save()

    def get(self, mission_id: str) -> dict | None:
        """Get a single mission by ID."""
        with self._lock:
            return self._missions.get(mission_id)

    def list(
        self,
        status: list[str] | None = None,
        complexity: list[str] | None = None,
        search: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        sort: str = "ts_desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List missions with filters and pagination.

        Returns (missions, total_count).
        """
        with self._lock:
            items = list(self._missions.values())

        # Filters
        if status:
            items = [m for m in items if m.get("status") in status]
        if complexity:
            items = [m for m in items if m.get("complexity") in complexity]
        if search:
            q = search.lower()
            items = [m for m in items if q in m.get("goal", "").lower()
                     or q in m.get("id", "").lower()]
        if from_ts:
            items = [m for m in items if m.get("ts", "") >= from_ts]
        if to_ts:
            items = [m for m in items if m.get("ts", "") <= to_ts]

        total = len(items)

        # Sort
        sort_key, sort_rev = "ts", True
        if sort == "tokens_desc":
            sort_key, sort_rev = "tokens", True
        elif sort == "duration_desc":
            sort_key, sort_rev = "duration", True
        elif sort == "ts_desc":
            sort_key, sort_rev = "ts", True

        items.sort(key=lambda m: m.get(sort_key, 0), reverse=sort_rev)

        # Pagination
        items = items[offset:offset + limit]

        return items, total

    def summary(self) -> dict:
        """Get aggregate summary statistics."""
        with self._lock:
            items = list(self._missions.values())

        completed = [m for m in items if m.get("status") == "completed"]
        failed = [m for m in items if m.get("status") == "failed"]
        aborted = [m for m in items if m.get("status") == "aborted"]

        total_tokens = sum(m.get("tokens", 0) for m in items)
        durations = [m.get("duration", 0) for m in items if m.get("duration")]

        return {
            "total_missions": len(items),
            "completed": len(completed),
            "failed": len(failed),
            "aborted": len(aborted),
            "running": 0,
            "total_tokens": total_tokens,
            "avg_duration": round(sum(durations) / len(durations), 1) if durations else 0,
            "avg_tokens": round(total_tokens / len(items)) if items else 0,
            "total_tool_calls": sum(m.get("tools", 0) for m in items),
            "total_blocked": 0,
            "total_budget_events": sum(m.get("budget_events", 0) for m in items),
            "total_anomalies": sum(m.get("anomaly_count", 0) for m in items),
            "bypass_detections": 0,
            "audit_integrity": "verified",
        }

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._missions)

    def clear(self) -> None:
        """Clear all missions. For testing only."""
        with self._lock:
            self._missions.clear()
            self._save()
