"""File Watcher — D-085: polling-based (cross-platform).

Monitors mission dirs, telemetry, capabilities, health, approvals
via mtime polling at 1s interval. Pushes change events to asyncio.Queue.
Debouncing: mission 500ms, telemetry 2s (D-085 / Task 10.7).
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("mcc.watcher")

# Debounce windows (seconds)
DEBOUNCE_MISSION_S = 0.5
DEBOUNCE_TELEMETRY_S = 2.0
DEBOUNCE_DEFAULT_S = 0.5


@dataclass
class WatchEvent:
    """A single file-change event."""
    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            from datetime import datetime, timezone
            self.timestamp = datetime.now(timezone.utc).isoformat()


class FileWatcher:
    """Polls filesystem for mtime changes, emits WatchEvents.

    Parameters
    ----------
    missions_dir : Path to ``logs/missions/``
    telemetry_path : Path to ``logs/policy-telemetry.jsonl``
    capabilities_path : Path to ``config/capabilities.json``
    services_path : Path to ``logs/services.json``
    approvals_dir : Path to ``logs/approvals/``
    event_queue : asyncio.Queue that receives WatchEvent instances
    poll_interval : seconds between polls (D-085: 1s)
    """

    def __init__(
        self,
        missions_dir: Path,
        telemetry_path: Path,
        capabilities_path: Path,
        services_path: Path,
        approvals_dir: Path,
        event_queue: "asyncio.Queue[WatchEvent]",
        poll_interval: float = 1.0,
    ):
        self.missions_dir = missions_dir
        self.telemetry_path = telemetry_path
        self.capabilities_path = capabilities_path
        self.services_path = services_path
        self.approvals_dir = approvals_dir
        self.event_queue = event_queue
        self.poll_interval = poll_interval

        # mtime caches
        self._file_mtimes: dict[str, float] = {}
        self._mission_mtimes: dict[str, float] = {}
        self._mission_count: int = 0

        # Debounce tracking: {debounce_key: (WatchEvent, fire_at_time)}
        self._pending_events: dict[str, tuple[WatchEvent, float]] = {}

        self._running = False
        self._task: asyncio.Task | None = None

    # ── Lifecycle ────────────────────────────────────────────────

    async def start(self):
        """Warm mtime cache and start polling loop."""
        self._running = True
        self._warm_cache()
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("FileWatcher started (poll_interval=%.1fs)", self.poll_interval)

    async def stop(self):
        """Stop polling loop and wait for clean exit."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("FileWatcher stopped")

    # ── Polling loop ─────────────────────────────────────────────

    async def _poll_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
                self._check_all()
                self._flush_debounced()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("FileWatcher poll error: %s", e)

    # ── Check all watched targets ────────────────────────────────

    def _check_all(self):
        self._check_single_file(self.telemetry_path, "telemetry_new")
        self._check_single_file(self.capabilities_path, "capability_changed")
        self._check_single_file(self.services_path, "health_changed")
        self._check_approvals()
        self._check_missions()

    # ── Single file check ────────────────────────────────────────

    def _check_single_file(self, path: Path, event_type: str):
        key = str(path)
        mtime = self._safe_mtime(path)
        if mtime is None:
            return  # file missing — graceful skip
        prev = self._file_mtimes.get(key)
        if prev is not None and mtime != prev:
            debounce_s = DEBOUNCE_TELEMETRY_S if event_type == "telemetry_new" else DEBOUNCE_DEFAULT_S
            self._emit(
                WatchEvent(event_type=event_type, data={"updatedAt": self._iso_now()}),
                debounce_key=f"file:{event_type}",
                debounce_s=debounce_s,
            )
        self._file_mtimes[key] = mtime

    # ── Approvals dir check ──────────────────────────────────────

    def _check_approvals(self):
        key = str(self.approvals_dir)
        mtime = self._dir_max_mtime(self.approvals_dir)
        if mtime is None:
            return
        prev = self._file_mtimes.get(key)
        if prev is not None and mtime != prev:
            self._emit(
                WatchEvent(event_type="approval_changed", data={"updatedAt": self._iso_now()}),
                debounce_key="file:approval_changed",
            )
        self._file_mtimes[key] = mtime

    # ── Mission dir check ────────────────────────────────────────

    def _check_missions(self):
        if not self.missions_dir.exists():
            return

        try:
            current_dirs = [
                d for d in self.missions_dir.iterdir() if d.is_dir()
            ]
        except OSError:
            return

        # Mission list changed (new/removed dir)
        current_count = len(current_dirs)
        if current_count != self._mission_count:
            self._emit(
                WatchEvent(
                    event_type="mission_list_changed",
                    data={"count": current_count, "updatedAt": self._iso_now()},
                ),
                debounce_key="mission_list",
            )
        self._mission_count = current_count

        # Per-mission mtime check
        for mission_dir in current_dirs:
            mid = mission_dir.name
            mtime = self._mission_dir_mtime(mission_dir)
            if mtime is None:
                continue
            prev = self._mission_mtimes.get(mid)
            if prev is not None and mtime != prev:
                self._emit(
                    WatchEvent(
                        event_type="mission_updated",
                        data={"missionId": mid, "updatedAt": self._iso_now()},
                    ),
                    debounce_key=f"mission:{mid}",
                    debounce_s=DEBOUNCE_MISSION_S,
                )
            self._mission_mtimes[mid] = mtime

    # ── Cache warm (first scan, no events emitted) ───────────────

    def _warm_cache(self):
        """Populate mtime caches without emitting events."""
        for path, _ in [
            (self.telemetry_path, "telemetry_new"),
            (self.capabilities_path, "capability_changed"),
            (self.services_path, "health_changed"),
        ]:
            mtime = self._safe_mtime(path)
            if mtime is not None:
                self._file_mtimes[str(path)] = mtime

        # Approvals
        mtime = self._dir_max_mtime(self.approvals_dir)
        if mtime is not None:
            self._file_mtimes[str(self.approvals_dir)] = mtime

        # Missions
        if self.missions_dir.exists():
            try:
                dirs = [d for d in self.missions_dir.iterdir() if d.is_dir()]
                self._mission_count = len(dirs)
                for d in dirs:
                    mtime = self._mission_dir_mtime(d)
                    if mtime is not None:
                        self._mission_mtimes[d.name] = mtime
            except OSError:
                pass

    # ── Helpers ──────────────────────────────────────────────────

    def _emit(self, event: WatchEvent, debounce_key: str | None = None, debounce_s: float = DEBOUNCE_DEFAULT_S):
        """Schedule event with debounce. Same key resets the timer."""
        if debounce_key:
            fire_at = time.monotonic() + debounce_s
            self._pending_events[debounce_key] = (event, fire_at)
        else:
            self._emit_now(event)

    def _flush_debounced(self):
        """Emit events whose debounce window has expired."""
        now = time.monotonic()
        ready = [k for k, (_, fire_at) in self._pending_events.items() if now >= fire_at]
        for k in ready:
            event, _ = self._pending_events.pop(k)
            self._emit_now(event)

    def _emit_now(self, event: WatchEvent):
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping: %s", event.event_type)

    @staticmethod
    def _safe_mtime(path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except (OSError, FileNotFoundError):
            return None

    @staticmethod
    def _dir_max_mtime(dir_path: Path) -> float | None:
        if not dir_path.exists():
            return None
        try:
            mtimes = [
                f.stat().st_mtime
                for f in dir_path.iterdir()
                if f.is_file()
            ]
            return max(mtimes) if mtimes else None
        except OSError:
            return None

    def _mission_dir_mtime(self, mission_dir: Path) -> float | None:
        """Max mtime of state/mission/summary files in a mission dir."""
        try:
            mtimes = []
            for f in mission_dir.iterdir():
                if f.is_file() and (
                    f.name.endswith("-state.json")
                    or f.name.startswith("mission-")
                    or f.name.endswith("-summary.json")
                ):
                    mtimes.append(f.stat().st_mtime)
            return max(mtimes) if mtimes else None
        except OSError:
            return None

    @staticmethod
    def _iso_now() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
