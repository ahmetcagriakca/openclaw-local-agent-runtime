"""SSE API endpoint — D-087: localhost-only.

GET /api/v1/events/stream → Server-Sent Events stream.
Supports Last-Event-ID for reconnect replay.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

if TYPE_CHECKING:
    from api.sse_manager import SSEManager

logger = logging.getLogger("mcc.sse_api")

router = APIRouter(tags=["events"])


def _get_sse_manager(request: Request) -> "SSEManager":
    return request.app.state.sse_manager


@router.get("/events/stream")
async def sse_stream(request: Request):
    """SSE event stream endpoint.

    - Sends ``connected`` event on first connect
    - Replays missed events if ``Last-Event-ID`` header present
    - Streams events until client disconnects
    - Returns 503 if max clients reached
    """
    manager = _get_sse_manager(request)

    queue = await manager.subscribe()
    if queue is None:
        return StreamingResponse(
            iter(["data: {\"error\": \"max clients reached\"}\n\n"]),
            status_code=503,
            media_type="text/event-stream",
        )

    async def event_generator():
        try:
            # Send connected event
            from datetime import datetime, timezone
            connected_data = (
                f'{{"serverTime": "{datetime.now(timezone.utc).isoformat()}", '
                f'"version": "1.0.0"}}'
            )
            yield f"event: connected\ndata: {connected_data}\n\n"

            # Replay missed events if Last-Event-ID present
            last_id_header = request.headers.get("Last-Event-ID", "")
            if last_id_header:
                try:
                    last_id = int(last_id_header)
                    missed = manager.get_missed_events(last_id)
                    for event in missed:
                        yield event.format()
                except (ValueError, TypeError):
                    pass

            # Stream events
            idle_cycles = 0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if event is None:
                        break  # shutdown signal
                    idle_cycles = 0
                    yield event.format()
                except asyncio.TimeoutError:
                    idle_cycles += 1
                    if idle_cycles >= 3600:  # 1h silence → close
                        break
                    continue
        finally:
            await manager.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
