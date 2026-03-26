# OpenClaw Mission Control — Operator Guide

## 1. System Overview

OpenClaw Mission Control is a governed multi-agent mission system with 9 specialist roles, 3 quality gates, and a 10-state mission state machine.

**Architecture:**
```
Telegram → OpenClaw (WSL) → Agent Runner (Windows) → Mission Controller
  → 9 roles with quality gates → MCP → PowerShell
```

**Port Map:**
| Port | Service | Purpose |
|------|---------|---------|
| 8001 | WMCP | Windows MCP Proxy |
| 8002 | Legacy Dashboard | Deprecated (D-097) |
| 8003 | Mission Control API | FastAPI backend |
| 3000 | Mission Control UI | React frontend (dev) |

## 2. Starting the System

### Backend (API Server)
```bash
cd agent
python -m uvicorn api.server:app --host 127.0.0.1 --port 8003
```

The API server performs startup validation (D-074):
1. Filesystem validation (creates `logs/missions/`, `logs/approvals/`)
2. Cache warm-up and normalizer initialization
3. Capability checker loading from `config/capabilities.json`
4. Service registration to `logs/services.json`
5. File watcher + SSE manager startup

### Frontend (React UI)
```bash
# Requires Node.js 20+
export Path="C:\Users\AKCA\node20\node-v20.18.1-win-x64;$Path"
cd frontend
npm run dev
```

Frontend proxies `/api` requests to `http://127.0.0.1:8003`.

### Agent Runner
```bash
cd agent
python oc-agent-runner.py
```

## 3. Health Monitoring

### API Health Check
```bash
curl http://localhost:8003/api/v1/health | python -m json.tool
```

Response includes component status:
- **api**: Always `ok` if responding
- **cache**: File cache stats (entries, hits, errors)
- **capabilities**: Manifest parse status

Overall status: `ok` / `degraded` / `error` (worst component wins).

### Services Heartbeat
The API writes `logs/services.json` every 30 seconds. If `lastHeartbeatAt` is stale (>60s), the service may be unhealthy.

### SSE Connection
The frontend shows connection status in the header:
- **Green (Live)**: SSE connected, real-time updates
- **Yellow (Connecting)**: Initial connection attempt
- **Orange (Reconnecting)**: Lost connection, retrying (exponential backoff)
- **Gray (Polling 30s)**: SSE failed after 3 retries, polling fallback

## 4. Mission Lifecycle

### State Machine (10 states)
```
pending → planning → executing → gate_check → rework → approval_wait → completed
                                                              ↓
                                             failed / aborted / timed_out
```

### Mission Flow
```
User goal → PO → Analyst → Architect → PM → Developer → Tester → Reviewer → Manager
            G1 (requirements)    G2 (code+test)    G3 (review)
```

### Viewing Missions
- **UI**: Navigate to `/missions` in the browser
- **API**: `curl http://localhost:8003/api/v1/missions`
- **Detail**: `curl http://localhost:8003/api/v1/missions/{id}`
- **Stages**: `curl http://localhost:8003/api/v1/missions/{id}/stages`

### Data Quality Indicators
Every API response includes a `meta.dataQuality` field:
- **fresh**: All sources present and recent
- **partial**: Some sources missing
- **stale**: Data older than threshold
- **degraded**: Parse errors or circuit breaker open
- **unknown**: All sources missing
- **not_reached**: Source not yet created

## 5. Approval Management

### Approval Flow
High-risk tool calls require operator approval before execution:
1. Agent requests high-risk tool → approval created (status: `pending`)
2. Operator approves/rejects via dashboard, CLI, or Telegram
3. Agent proceeds or aborts based on decision
4. Timeout (60s default) → auto-deny

### Approving/Rejecting via Dashboard
1. Navigate to `/approvals` in the UI
2. Pending approvals show **Approve** (green) and **Reject** (red) buttons
3. Reject is destructive — requires confirmation dialog (D-090)
4. After action, the UI shows a toast with mutation status

### Approving via CLI
```bash
cd agent
python -c "from services.approval_store import approve; approve('apv-XXXXX')"
```

### Approval Channels (D-092)
- **Dashboard** (primary): Approve/reject buttons in UI
- **Telegram** (deprecated): Plain yes/no + strict ID format
- **CLI**: `oc approve apv-XXX`
- **Timeout**: Auto-deny after 60 seconds

## 6. Mutation Lifecycle (D-096)

All mutations (approve, reject, cancel, retry) follow this lifecycle:
1. **Request**: API writes atomic signal artifact → returns `lifecycleState=requested`
2. **Acceptance**: Runtime reads artifact → emits SSE `mutation_applied`
3. **Timeout**: If no response within 10s → SSE `mutation_timed_out`

The API never directly calls services (D-001). It only writes signal artifacts.

### Cancel a Running Mission
- **UI**: Mission detail page → Cancel button (visible for active states)
- **API**: `POST /api/v1/missions/{id}/cancel` (requires Origin header)
- Valid states: pending, planning, executing, gate_check, rework, approval_wait

### Retry a Failed Mission
- **UI**: Mission detail page → Retry button (visible for terminal states)
- **API**: `POST /api/v1/missions/{id}/retry` (requires Origin header)
- Valid states: failed, aborted, timed_out

## 7. Security Model

### Localhost-Only Access (D-070)
- API binds to `127.0.0.1` only — no external network access
- Host header validation rejects non-localhost requests → 403
- CORS allows only `http://localhost:3000` and `http://127.0.0.1:3000`

### CSRF Protection (D-089)
- All POST requests require valid `Origin` header
- Missing or invalid origin → 403 Forbidden
- Origin must match `http://localhost:3000` or `http://127.0.0.1:3000`

### SSE Abuse Prevention (D-087)
- Maximum 10 concurrent SSE clients
- 1-hour idle timeout (closes inactive connections)
- Per-client queue limit: 50 events

## 8. Telemetry and Observability

### Viewing Telemetry
- **UI**: Navigate to `/telemetry` — filterable by mission_id
- **API**: `curl http://localhost:8003/api/v1/telemetry?mission_id=XXX&limit=200`

### Log Files
| Path | Content |
|------|---------|
| `logs/mission-control-api.log` | API requests, mutations, errors |
| `logs/policy-telemetry.jsonl` | Policy deny events |
| `logs/services.json` | Service registry + heartbeat |
| `logs/missions/` | Mission state files |
| `logs/approvals/` | Approval records |

### Capabilities
```bash
curl http://localhost:8003/api/v1/capabilities | python -m json.tool
```

Tri-state: `available` / `unavailable` / `unknown`.
Driven by `config/capabilities.json` (auto-generated).

## 9. Troubleshooting

### API Won't Start
1. Check port 8003 not in use: `netstat -an | findstr 8003`
2. Check Python path includes `agent/` directory
3. Check `config/capabilities.json` exists and is valid JSON

### SSE Not Connecting
1. Verify API is running: `curl http://localhost:8003/api/v1/health`
2. Check browser console for CORS errors
3. Frontend must be on `localhost:3000` (not 127.0.0.1)
4. Max 10 SSE clients — close extra tabs

### Mutations Not Applying
1. Check mutation response has `lifecycleState: "requested"`
2. Signal artifact written to `logs/missions/{id}/`
3. Runtime/controller must be running to consume artifacts
4. Check `logs/mission-control-api.log` for audit trail

### Data Quality Shows "degraded"
1. Check file parse errors in API log
2. Verify JSON files are not corrupted
3. Circuit breaker may be open — wait for recovery timeout

### Frontend Build Fails
1. Requires Node.js 20+ (not 14!)
2. Portable Node at: `C:\Users\AKCA\node20\node-v20.18.1-win-x64`
3. Run `npx tsc --noEmit` to check type errors first

## 10. Testing

### Backend Tests
```bash
cd agent && python -m pytest tests/ -v
```
Expected: 195+ tests (legacy + SSE + API + contract + E2E)

### Frontend Tests
```bash
cd frontend && npx vitest run
```
Expected: 29 tests

### E2E Tests (API-level)
```bash
cd agent && python -m pytest tests/test_e2e.py -v
```
Expected: 39 tests across 16 scenarios

## 11. API Reference

Full OpenAPI specification: `docs/api/openapi.json`

### Endpoints Summary
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | System health |
| GET | /api/v1/capabilities | System capabilities |
| GET | /api/v1/missions | List missions |
| GET | /api/v1/missions/{id} | Mission detail |
| GET | /api/v1/missions/{id}/stages | Mission stages |
| GET | /api/v1/missions/{id}/stages/{idx} | Single stage |
| GET | /api/v1/approvals | List approvals |
| GET | /api/v1/approvals/{id} | Approval detail |
| GET | /api/v1/telemetry | Telemetry events |
| GET | /api/v1/events/stream | SSE event stream |
| POST | /api/v1/approvals/{id}/approve | Approve approval |
| POST | /api/v1/approvals/{id}/reject | Reject approval |
| POST | /api/v1/missions/{id}/cancel | Cancel mission |
| POST | /api/v1/missions/{id}/retry | Retry mission |
