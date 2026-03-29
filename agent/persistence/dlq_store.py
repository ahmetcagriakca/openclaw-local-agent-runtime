"""DLQ Store — Dead Letter Queue for failed missions.

B-106: Failed missions are moved to DLQ with full context for
later retry, inspection, or purge. Backed by JSON file with
atomic writes (D-071).
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.persistence.dlq")


class DLQEntry:
    """Single DLQ entry wrapping a failed mission."""

    __slots__ = (
        "dlq_id", "mission_id", "goal", "error", "failed_stage_id",
        "failed_at", "retry_count", "last_retry_at", "status",
        "mission_snapshot",
    )

    def __init__(self, *, dlq_id: str, mission_id: str, goal: str,
                 error: str, failed_stage_id: str, failed_at: str,
                 retry_count: int = 0, last_retry_at: str | None = None,
                 status: str = "pending",
                 mission_snapshot: dict | None = None):
        self.dlq_id = dlq_id
        self.mission_id = mission_id
        self.goal = goal
        self.error = error
        self.failed_stage_id = failed_stage_id
        self.failed_at = failed_at
        self.retry_count = retry_count
        self.last_retry_at = last_retry_at
        self.status = status  # pending | retrying | resolved | purged
        self.mission_snapshot = mission_snapshot or {}

    def to_dict(self) -> dict:
        return {
            "dlq_id": self.dlq_id,
            "mission_id": self.mission_id,
            "goal": self.goal,
            "error": self.error,
            "failed_stage_id": self.failed_stage_id,
            "failed_at": self.failed_at,
            "retry_count": self.retry_count,
            "last_retry_at": self.last_retry_at,
            "status": self.status,
            "mission_snapshot": self.mission_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DLQEntry:
        return cls(
            dlq_id=data["dlq_id"],
            mission_id=data["mission_id"],
            goal=data.get("goal", ""),
            error=data.get("error", ""),
            failed_stage_id=data.get("failed_stage_id", ""),
            failed_at=data.get("failed_at", ""),
            retry_count=data.get("retry_count", 0),
            last_retry_at=data.get("last_retry_at"),
            status=data.get("status", "pending"),
            mission_snapshot=data.get("mission_snapshot", {}),
        )


class DLQStore:
    """Persistent Dead Letter Queue store.

    Stores failed missions that exhausted their retry budget for
    manual inspection, batch retry, or purge.
    """

    def __init__(self, store_path: Path | str | None = None):
        if store_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            store_path = root / "logs" / "dlq.json"
        self._path = Path(store_path)
        self._lock = threading.Lock()
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._entries = data.get("entries", {})
                logger.info("DLQStore loaded %d entries", len(self._entries))
            except Exception as e:
                logger.warning("DLQStore load failed: %s", e)
                self._entries = {}

    def _save(self) -> None:
        try:
            atomic_write_json(self._path, {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "entries": self._entries,
            })
        except Exception as e:
            logger.error("DLQStore save failed: %s", e)

    def enqueue(self, mission: dict, failed_stage_id: str = "",
                error: str = "") -> str:
        """Add a failed mission to the DLQ. Returns dlq_id."""
        mission_id = mission.get("missionId", mission.get("mission_id", ""))
        now = datetime.now(timezone.utc).isoformat()
        dlq_id = f"dlq-{mission_id}"

        entry = DLQEntry(
            dlq_id=dlq_id,
            mission_id=mission_id,
            goal=mission.get("goal", ""),
            error=error or mission.get("error", ""),
            failed_stage_id=failed_stage_id,
            failed_at=now,
            status="pending",
            mission_snapshot=mission,
        )

        with self._lock:
            self._entries[dlq_id] = entry.to_dict()
            self._save()

        logger.info("DLQ enqueued: %s (mission=%s)", dlq_id, mission_id)
        return dlq_id

    def get(self, dlq_id: str) -> dict | None:
        """Get a single DLQ entry."""
        with self._lock:
            return self._entries.get(dlq_id)

    def list(self, status: str | None = None,
             limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        """List DLQ entries with optional status filter."""
        with self._lock:
            items = list(self._entries.values())

        if status:
            items = [e for e in items if e.get("status") == status]

        total = len(items)
        # Sort by failed_at descending (newest first)
        items.sort(key=lambda e: e.get("failed_at", ""), reverse=True)
        items = items[offset:offset + limit]
        return items, total

    def mark_retrying(self, dlq_id: str) -> bool:
        """Mark entry as retrying. Returns False if not found."""
        with self._lock:
            entry = self._entries.get(dlq_id)
            if not entry:
                return False
            entry["status"] = "retrying"
            entry["retry_count"] = entry.get("retry_count", 0) + 1
            entry["last_retry_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
        return True

    def mark_resolved(self, dlq_id: str) -> bool:
        """Mark entry as resolved (retry succeeded)."""
        with self._lock:
            entry = self._entries.get(dlq_id)
            if not entry:
                return False
            entry["status"] = "resolved"
            self._save()
        return True

    def mark_pending(self, dlq_id: str) -> bool:
        """Reset entry back to pending (retry failed again)."""
        with self._lock:
            entry = self._entries.get(dlq_id)
            if not entry:
                return False
            entry["status"] = "pending"
            self._save()
        return True

    def purge(self, dlq_id: str) -> bool:
        """Remove entry from DLQ permanently."""
        with self._lock:
            if dlq_id not in self._entries:
                return False
            del self._entries[dlq_id]
            self._save()
        return True

    def purge_resolved(self) -> int:
        """Purge all resolved entries. Returns count purged."""
        with self._lock:
            to_remove = [k for k, v in self._entries.items()
                         if v.get("status") == "resolved"]
            for k in to_remove:
                del self._entries[k]
            if to_remove:
                self._save()
        return len(to_remove)

    def summary(self) -> dict:
        """DLQ summary statistics."""
        with self._lock:
            items = list(self._entries.values())
        pending = sum(1 for e in items if e.get("status") == "pending")
        retrying = sum(1 for e in items if e.get("status") == "retrying")
        resolved = sum(1 for e in items if e.get("status") == "resolved")
        return {
            "total": len(items),
            "pending": pending,
            "retrying": retrying,
            "resolved": resolved,
        }

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)
