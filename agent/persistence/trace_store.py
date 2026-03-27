"""TraceStore — completed OTel trace storage + query.

Task 16.1: Read completed traces, filter by mission/stage/time.
Stores span data from TracingHandler after mission completion.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.persistence.traces")


class TraceStore:
    """Persistent trace storage for completed missions.

    Stores span trees indexed by mission correlation_id.
    """

    def __init__(self, store_path: Path | str | None = None):
        if store_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            store_path = root / "logs" / "trace-history.json"
        self._path = Path(store_path)
        self._lock = threading.Lock()
        self._traces: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._traces = data.get("traces", {})
            except Exception as e:
                logger.warning("TraceStore load failed: %s", e)

    def _save(self) -> None:
        try:
            atomic_write_json(self._path, {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "traces": self._traces,
            })
        except Exception as e:
            logger.error("TraceStore save failed: %s", e)

    def record_trace(self, mission_id: str, spans: list[dict]) -> None:
        """Store a completed trace (list of span dicts)."""
        with self._lock:
            self._traces[mission_id] = {
                "mission_id": mission_id,
                "span_count": len(spans),
                "spans": spans,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save()

    def get_trace(self, mission_id: str) -> dict | None:
        """Get trace for a specific mission."""
        with self._lock:
            return self._traces.get(mission_id)

    def get_span_tree(self, mission_id: str) -> list[dict]:
        """Get spans as a tree structure for waterfall rendering."""
        trace = self.get_trace(mission_id)
        if not trace:
            return []
        return trace.get("spans", [])

    def list_traces(
        self,
        from_ts: str | None = None,
        to_ts: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """List available traces (metadata only, no spans)."""
        with self._lock:
            items = []
            for mid, trace in self._traces.items():
                ts = trace.get("recorded_at", "")
                if from_ts and ts < from_ts:
                    continue
                if to_ts and ts > to_ts:
                    continue
                items.append({
                    "mission_id": mid,
                    "span_count": trace.get("span_count", 0),
                    "recorded_at": ts,
                })
            items.sort(key=lambda x: x.get("recorded_at", ""), reverse=True)
            return items[:limit]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._traces)

    def clear(self) -> None:
        with self._lock:
            self._traces.clear()
            self._save()
