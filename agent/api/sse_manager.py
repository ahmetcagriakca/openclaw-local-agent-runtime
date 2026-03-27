"""SSE Event Manager — D-086: per-entity change events.

Manages connected SSE clients, broadcasts events, handles heartbeats.
Max 10 clients (D-087 abuse prevention).
"""
import asyncio
import itertools
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from api.file_watcher import WatchEvent

logger = logging.getLogger("mcc.sse")

MAX_CLIENTS = 10
HEARTBEAT_INTERVAL_S = 30
EVENT_BUFFER_SIZE = 100


@dataclass
class SSEEvent:
    """Formatted SSE event ready for streaming."""
    id: int
    event: str
    data: str

    def format(self) -> str:
        """Format as SSE wire protocol."""
        lines = [f"id: {self.id}", f"event: {self.event}", f"data: {self.data}", "", ""]
        return "\n".join(lines)


class SSEManager:
    """Manages SSE client connections and event broadcasting.

    - subscribe() / unsubscribe() for client lifecycle
    - broadcast() pushes to all connected clients
    - heartbeat loop keeps connections alive
    - Event buffer for Last-Event-ID replay (100 events)
    """

    def __init__(self, heartbeat_interval_s: float = HEARTBEAT_INTERVAL_S):
        self._clients: set[asyncio.Queue[SSEEvent | None]] = set()
        self._counter = itertools.count(1)
        self._buffer: deque[SSEEvent] = deque(maxlen=EVENT_BUFFER_SIZE)
        self._heartbeat_interval_s = heartbeat_interval_s
        self._heartbeat_task: asyncio.Task | None = None
        self._watcher_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        return len(self._clients)

    # ── Client management ────────────────────────────────────────

    async def subscribe(self) -> "asyncio.Queue[SSEEvent | None] | None":
        """Register a new SSE client. Returns None if max clients reached."""
        async with self._lock:
            if len(self._clients) >= MAX_CLIENTS:
                logger.warning("SSE max clients (%d) reached, rejecting", MAX_CLIENTS)
                return None
            queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue(maxsize=50)
            self._clients.add(queue)
            logger.info("SSE client subscribed (%d total)", len(self._clients))
            return queue

    async def unsubscribe(self, queue: "asyncio.Queue[SSEEvent | None]"):
        """Remove a client queue."""
        async with self._lock:
            self._clients.discard(queue)
            logger.info("SSE client unsubscribed (%d remaining)", len(self._clients))

    # ── Broadcasting ─────────────────────────────────────────────

    async def broadcast(self, event_type: str, data: dict[str, Any] | None = None):
        """Create an SSE event and push to all connected clients."""
        import json
        sse_event = SSEEvent(
            id=next(self._counter),
            event=event_type,
            data=json.dumps(data or {}),
        )
        self._buffer.append(sse_event)

        async with self._lock:
            dead: list[asyncio.Queue] = []
            for client in self._clients:
                try:
                    client.put_nowait(sse_event)
                except asyncio.QueueFull:
                    dead.append(client)
            for d in dead:
                self._clients.discard(d)
                logger.warning("SSE client dropped (queue full)")

    def get_missed_events(self, last_event_id: int) -> list[SSEEvent]:
        """Return buffered events after the given ID for reconnect replay."""
        return [e for e in self._buffer if e.id > last_event_id]

    # ── Heartbeat ────────────────────────────────────────────────

    async def start_heartbeat(self):
        """Start periodic heartbeat broadcasting."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("SSE heartbeat started (interval=%ds)", self._heartbeat_interval_s)

    async def _heartbeat_loop(self):
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval_s)
                await self.broadcast("heartbeat", {
                    "serverTime": datetime.now(timezone.utc).isoformat(),
                })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("SSE heartbeat error: %s", e)

    # ── Watcher bridge ───────────────────────────────────────────

    async def start_watcher_bridge(self, event_queue: "asyncio.Queue[WatchEvent]"):
        """Read WatchEvents from FileWatcher queue and broadcast them."""
        self._watcher_task = asyncio.create_task(
            self._watcher_bridge_loop(event_queue)
        )
        logger.info("SSE watcher bridge started")

    async def _watcher_bridge_loop(self, event_queue: "asyncio.Queue[WatchEvent]"):
        while True:
            try:
                watch_event = await event_queue.get()
                await self.broadcast(watch_event.event_type, watch_event.data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("SSE watcher bridge error: %s", e)

    # ── Shutdown ─────────────────────────────────────────────────

    async def shutdown(self):
        """Stop heartbeat, watcher bridge, and signal all clients."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._watcher_task:
            self._watcher_task.cancel()
            try:
                await self._watcher_task
            except asyncio.CancelledError:
                pass

        # Signal clients to disconnect
        async with self._lock:
            for client in self._clients:
                try:
                    client.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            self._clients.clear()

        logger.info("SSE manager shutdown complete")
