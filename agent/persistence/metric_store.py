"""MetricStore — metric snapshot storage + query.

Task 16.2: Snapshot current OTel metrics, historical query.
Periodically captures metric state for dashboard display.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.persistence.metrics")


class MetricStore:
    """Persistent metric snapshot storage.

    Captures periodic snapshots of OTel metric data for
    historical queries and dashboard display.
    """

    MAX_SNAPSHOTS = 1000

    def __init__(self, store_path: Path | str | None = None):
        if store_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            store_path = root / "logs" / "metric-history.json"
        self._path = Path(store_path)
        self._lock = threading.Lock()
        self._snapshots: list[dict] = []
        self._current: dict = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._snapshots = data.get("snapshots", [])
                if self._snapshots:
                    self._current = self._snapshots[-1].get("metrics", {})
            except Exception as e:
                logger.warning("MetricStore load failed: %s", e)

    def _save(self) -> None:
        try:
            atomic_write_json(self._path, {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "snapshots": self._snapshots[-self.MAX_SNAPSHOTS:],
            })
        except Exception as e:
            logger.error("MetricStore save failed: %s", e)

    def snapshot(self, metrics: dict) -> None:
        """Record a metric snapshot."""
        with self._lock:
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "metrics": metrics,
            }
            self._snapshots.append(entry)
            self._current = metrics
            if len(self._snapshots) > self.MAX_SNAPSHOTS:
                self._snapshots = self._snapshots[-self.MAX_SNAPSHOTS:]
            self._save()

    def get_current(self) -> dict:
        """Get the latest metric snapshot."""
        with self._lock:
            return dict(self._current)

    def get_history(
        self,
        from_ts: str | None = None,
        to_ts: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get historical metric snapshots."""
        with self._lock:
            items = self._snapshots[:]

        if from_ts:
            items = [s for s in items if s.get("ts", "") >= from_ts]
        if to_ts:
            items = [s for s in items if s.get("ts", "") <= to_ts]

        return items[-limit:]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._current.clear()
            self._save()
