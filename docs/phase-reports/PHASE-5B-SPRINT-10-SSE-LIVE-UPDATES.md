# Phase 5B — Sprint 10: SSE Live Updates

**Date:** 2026-03-25
**Status:** COMPLETE
**Author:** Operator (AKCA) + Claude (Copilot)
**Prerequisite:** Sprint 9 CLOSED (COMPLETE — 34/34 checklist, 18/18 test, evidence bundle)
**Risk Level:** MEDIUM-HIGH — backend+frontend real-time integration
**GPT Review:** PENDING

---

## Section 1: Executive Summary

Sprint 10 replaces the 30-second polling model with Server-Sent Events (SSE) push updates. A backend FileWatcher monitors file system changes (mtime polling, 1s interval), SSEManager broadcasts events to connected clients, and the frontend useSSE hook receives real-time invalidation signals. Polling is preserved as automatic fallback after 3 failed reconnection attempts.

**Key outcomes:**
- Backend FileWatcher: mtime polling 1s (D-085), debounce 500ms mission / 2s telemetry
- SSEManager: asyncio.Queue broadcast, 30s heartbeat, 100-event buffer, max 10 clients
- SSE endpoint: `GET /api/v1/events/stream` with `Last-Event-ID` replay (D-087 localhost security)
- Frontend useSSE hook: EventSource API, exponential backoff 1s→30s (D-088)
- SSEContext: shared connection per tab, useSSEInvalidation per-page subscription
- ConnectionIndicator: 4-state (connecting/connected/reconnecting/polling) — no fake live
- All 5 pages migrated: SSE event → immediate refresh(), polling fallback preserved
- Backend: 114 tests (100 legacy + 14 SSE), 0 failures
- Frontend: 29 tests (18 legacy + 11 SSE), 0 failures
- 0 TypeScript errors, 0 lint errors, production build success (198 KB JS)

**Frozen decisions enforced:** D-070, D-085, D-086, D-087, D-088.

---

## Section 2: Task Summary

| Task | Description | File(s) | Effort | Status |
|------|-------------|---------|--------|--------|
| 10.1 | File Watcher Service | `agent/api/file_watcher.py` | M | DONE |
| 10.2 | SSE Event Manager | `agent/api/sse_manager.py` | M | DONE |
| 10.3 | SSE Endpoint + FastAPI Integration | `agent/api/sse_api.py`, `server.py` mod | M | DONE |
| 10.4 | useSSE Hook (Frontend) | `frontend/src/hooks/useSSE.ts` | L | DONE |
| 10.5 | Connection Status Indicator | `ConnectionIndicator.tsx`, `SSEContext.tsx`, `Layout.tsx` mod | S | DONE |
| 10.6 | Page Integration (SSE Migration) | All 5 pages + `App.tsx` mod | L | DONE |
| 10.7 | Debouncing | `file_watcher.py` mod | M | DONE |
| 10.8 | Test Suite | `test_sse.py`, `useSSE.test.tsx`, `ConnectionIndicator.test.tsx` | M | DONE |

---

## Section 3: Architecture

### 3.1 — Data Flow

```
File System Change (mtime)
  → FileWatcher (1s poll, debounce)
    → asyncio.Queue
      → SSEManager (broadcast to all clients)
        → StreamingResponse (text/event-stream)
          → EventSource (browser)
            → useSSE hook
              → SSEContext event bus
                → useSSEInvalidation (per-page)
                  → refresh() → API fetch
```

### 3.2 — Event Types (D-086)

| Event Type | Trigger | Frontend Action |
|-----------|---------|-----------------|
| `connected` | Initial connection | Set "Live" state |
| `heartbeat` | Every 30s | Update lastEventAt |
| `mission_updated` | Mission file mtime change | Invalidate mission detail + list |
| `mission_list_changed` | New mission dir / count change | Refetch mission list |
| `health_changed` | Health file changed | Refetch health |
| `telemetry_new` | Telemetry file changed | Refetch telemetry |
| `capability_changed` | capabilities.json changed | Refetch capabilities |
| `approval_changed` | Approval store changed | Refetch approvals |

### 3.3 — Connection State Machine (D-088)

```
connecting → connected (SSE stream active)
connected → reconnecting (connection lost)
reconnecting → connected (reconnect success)
reconnecting → polling (3 consecutive failures)
polling → connecting (periodic retry)
connecting → connected (SSE restored)

Tab hidden → connection closed (bandwidth save)
Tab visible → reconnect attempt
```

### 3.4 — Debouncing

- **Backend (FileWatcher):** 500ms window for mission events, 2s window for telemetry. Implemented via `_pending_events` dict with monotonic fire time. `_flush_debounced()` emits expired events each poll cycle.
- **Frontend (SSEContext):** Event bus dedup via listener map — multiple events of same type within React render cycle result in single refresh.

---

## Section 4: Detailed Changes

### 4.1 — FileWatcher (`agent/api/file_watcher.py`) — Task 10.1, 10.7

New file. `FileWatcher` class with:
- `_warm_cache()`: initial mtime snapshot of all watched paths (no events on startup)
- `_check_all()`: polls missions dir, telemetry, health, capabilities, approvals
- `_check_missions()`: scans mission directories, emits `mission_list_changed` on count change, `mission_updated` on per-mission mtime change
- `_check_single_file()`: checks individual file mtime
- `_emit(debounce_key, debounce_s)`: queues event with optional debounce window
- `_flush_debounced()`: fires events whose debounce window has expired
- `WatchEvent` dataclass: `event_type`, `data`, `timestamp`
- Graceful: missing files logged, not crashed

### 4.2 — SSEManager (`agent/api/sse_manager.py`) — Task 10.2

New file. `SSEManager` class with:
- `subscribe() → asyncio.Queue`: adds client, returns queue
- `unsubscribe(queue)`: removes client
- `broadcast(event)`: pushes `SSEEvent` to all subscriber queues
- `get_missed_events(last_event_id)`: replays from 100-event ring buffer
- `start_heartbeat(interval_s)`: parametric heartbeat interval (default 30s)
- `start_watcher_bridge(queue)`: reads FileWatcher queue → broadcast
- `shutdown()`: cancels background tasks, clears subscribers
- `SSEEvent` dataclass: `event_type`, `data`, `id` (monotonic), `format()` for wire protocol

### 4.3 — SSE Endpoint (`agent/api/sse_api.py`) — Task 10.3

New file. FastAPI router with:
- `GET /api/v1/events/stream` → `StreamingResponse(media_type="text/event-stream")`
- `event_generator()`: async generator that yields SSE events
- Initial `connected` event with server time
- `Last-Event-ID` header → replay missed events
- Disconnect detection via `request.is_disconnected()`
- Safety: max 3600 idle cycles before auto-disconnect

### 4.4 — Server Integration (`agent/api/server.py`) — Task 10.3

Modified. Lifespan step 6 added:
- Creates `asyncio.Queue` (event bridge)
- Initializes `FileWatcher` with missions dir, telemetry, health, capabilities, approvals paths
- Initializes `SSEManager` with max_clients=10, buffer_size=100
- Starts watcher polling + heartbeat + watcher-to-SSE bridge
- Shutdown: `file_watcher.stop()`, `sse_manager.shutdown()`
- SSE router included at `/api/v1`

### 4.5 — useSSE Hook (`frontend/src/hooks/useSSE.ts`) — Task 10.4

New file. React hook with:
- EventSource connection to `/api/v1/events/stream`
- 4 states: `connecting`, `connected`, `reconnecting`, `polling`
- Exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s max
- 3 consecutive failures → polling fallback
- Page Visibility API: close on hidden, reconnect on visible
- Event listeners for all 8 event types
- Cleanup on unmount

### 4.6 — SSEContext (`frontend/src/hooks/SSEContext.tsx`) — Task 10.5

New file. React context with:
- `SSEProvider`: wraps app, manages single SSE connection
- `useSSEContext()`: exposes status, lastEventAt
- `useSSEInvalidation(eventTypes, callback)`: per-page subscription to specific event types
- Polling fallback: when status is `polling`, fires `polling_tick` every 30s to all handlers

### 4.7 — ConnectionIndicator (`frontend/src/components/ConnectionIndicator.tsx`) — Task 10.5

New file. 4-state visual indicator:
- `connecting`: yellow dot, pulse, "Connecting..."
- `connected`: green dot, "Live"
- `reconnecting`: orange dot, pulse, "Reconnecting..."
- `polling`: gray dot, "Polling 30s"
- Tooltip: "Last event Xs ago"

### 4.8 — Page Integration — Task 10.6

All 5 pages modified to add `useSSEInvalidation`:
- **MissionListPage**: `mission_list_changed`, `mission_updated`
- **MissionDetailPage**: `mission_updated`
- **HealthPage**: `health_changed`, `capability_changed`
- **ApprovalsPage**: `approval_changed`
- **TelemetryPage**: `telemetry_new`

`App.tsx` modified: `SSEProvider` wraps router.
`Layout.tsx` modified: `ConnectionIndicator` replaces static "Polling 30s" text.
`usePolling` preserved — not removed (D-088 fallback).

---

## Section 5: Frozen Decisions

| ID | Title | Status |
|----|-------|--------|
| D-085 | File Watcher — Polling-based (cross-platform, 1s) | Frozen |
| D-086 | SSE Event Granularity — Per-entity invalidation signal | Frozen |
| D-087 | SSE Auth — Localhost-only (D-070 extension) | Frozen |
| D-088 | SSE Reconnect — Exponential backoff + polling fallback | Frozen |

---

## Section 6: Test Results

### Backend (114 tests, 0 failures)

- 100 legacy tests (Sprint 5C/6D/4.5-A/8 suites)
- 14 SSE tests: 5 FileWatcher + 7 SSEManager + 2 endpoint
- pytest-anyio conflict resolved via `conftest.py` (unregisters anyio plugin)
- `test_sprint_5c.py` excluded (has `sys.exit(0)`)

### Frontend (29 tests, 0 failures)

- 18 legacy tests (Sprint 9 suites)
- 5 useSSE tests: initial state, connected event, reconnect backoff, error handling, cleanup
- 6 ConnectionIndicator tests: 4 states + tooltip + no-fake-live

### Quality Gates

- `npx tsc --noEmit` → 0 errors
- `npm run lint` → 0 errors
- `npm run build` → success (198 KB JS, 51 modules)

---

## Section 7: Files Created/Modified

| File | Type | Task |
|------|------|------|
| `agent/api/file_watcher.py` | Created | 10.1, 10.7 |
| `agent/api/sse_manager.py` | Created | 10.2 |
| `agent/api/sse_api.py` | Created | 10.3 |
| `agent/api/server.py` | Modified | 10.3 |
| `agent/tests/test_sse.py` | Created | 10.8 |
| `agent/tests/conftest.py` | Created | 10.8 |
| `frontend/src/hooks/useSSE.ts` | Created | 10.4 |
| `frontend/src/hooks/SSEContext.tsx` | Created | 10.5 |
| `frontend/src/components/ConnectionIndicator.tsx` | Created | 10.5 |
| `frontend/src/components/Layout.tsx` | Modified | 10.5 |
| `frontend/src/App.tsx` | Modified | 10.6 |
| `frontend/src/pages/MissionListPage.tsx` | Modified | 10.6 |
| `frontend/src/pages/MissionDetailPage.tsx` | Modified | 10.6 |
| `frontend/src/pages/HealthPage.tsx` | Modified | 10.6 |
| `frontend/src/pages/ApprovalsPage.tsx` | Modified | 10.6 |
| `frontend/src/pages/TelemetryPage.tsx` | Modified | 10.6 |
| `frontend/src/__tests__/useSSE.test.tsx` | Created | 10.8 |
| `frontend/src/__tests__/ConnectionIndicator.test.tsx` | Created | 10.8 |

**Total:** 10 created, 8 modified.

---

## Section 8: Evidence

All evidence files in `evidence/sprint-10/`:

| File | Content |
|------|---------|
| `pytest-output.txt` | 114 passed in 2.21s |
| `vitest-output.txt` | 29 passed (6 test files) |
| `tsc-output.txt` | 0 errors |
| `lint-output.txt` | 0 errors |
| `build-output.txt` | 51 modules, 198 KB JS |

---

## Section 9: Exit Criteria Status

| # | Criterion | Status |
|---|----------|--------|
| 1 | SSE endpoint streams events | ✅ |
| 2 | FileWatcher detects file changes | ✅ |
| 3 | Debounce works (rapid → single event) | ✅ |
| 4 | Frontend SSE connection established | ✅ |
| 5 | "Live" only on real SSE connection | ✅ |
| 6 | SSE event → immediate page refresh | ✅ |
| 7 | Server stop → reconnecting → backoff → polling | ✅ |
| 8 | Server restart → SSE reconnect | ✅ |
| 9 | Tab hidden → close, visible → reconnect | ✅ |
| 10 | Last-Event-ID replay | ✅ |
| 11 | Heartbeat 30s | ✅ |
| 12 | Max 10 SSE clients | ✅ |
| 13 | Multi-tab works | ✅ |
| 14 | usePolling fallback preserved | ✅ |
| 15 | Backend 100+ tests, 0 failure | ✅ (114/114) |
| 16 | Frontend tests all pass | ✅ (29/29) |
| 17 | 0 TypeScript errors | ✅ |
| 18 | 0 lint errors | ✅ |
| 19 | Production build success | ✅ |
| 20 | GPT review 0 blocking | ⬜ PENDING |
| 21 | validate_sprint_docs.py all PASS | ⬜ PENDING |

**19/21 criteria met.** GPT review and validator pending.

---

## Section 10: Known Issues

1. **pytest-anyio conflict:** `pytest-anyio` auto-registers and conflicts with `asyncio.run()` + `TestClient`. Fixed via `conftest.py` that unregisters the plugin. If `pytest-anyio` is removed from dependencies, `conftest.py` can be simplified.

2. **Documentation debt:** D-021→D-058 not yet extracted to `DECISIONS.md`. Carried forward.

---

*Phase 5B Sprint 10 — SSE Live Updates — OpenClaw Mission Control Center*
*Date: 2026-03-25*
*Operator: AKCA | Agent: Claude (Copilot)*
*Decisions: D-085, D-086, D-087, D-088*
