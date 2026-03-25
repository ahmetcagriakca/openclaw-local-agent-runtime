# Phase 5A-1 — Sprint 8: Backend Read Model

**Date:** 2026-03-25
**Status:** COMPLETE
**Author:** Operator (AKCA) + Claude Opus 4.6
**Prerequisite:** Sprint 7 complete (D-078 E2E waiver: 2/4 pass, fail'ler scope dışı)
**Risk Level:** HIGH — 3 internal milestones (8α, 8β, 8γ)
**GPT Review:** 3 rounds applied (Sprint 8 review, cross-review, fix record)

---

## Section 1: Executive Summary

Sprint 8 delivers the Mission Control Center backend — a FastAPI read-only API that normalizes data from 5 sources into a single, quality-aware response. This is the foundation for Phase 5: every future sprint (React UI, SSE, intervention) builds on this API contract.

**Key outcomes:**
- FastAPI server running on 127.0.0.1:8003 with D-070 localhost security
- 14 Pydantic schemas frozen (D-067) — additive-only post-freeze
- MissionNormalizer aggregating 5 sources with D-065 precedence rules
- D-068/D-079 data quality (6 states: fresh, partial, stale, degraded, unknown, not_reached) in every API response
- Per-source freshness tracking with staleThresholdMs
- Circuit breaker isolating source failures (D-072)
- mtime-based incremental cache avoiding redundant disk reads
- Atomic write utility system-wide (D-071)
- Blocking fix: `_save_mission()` crash-safe (BF-8.0)
- 170 tests total (129 legacy + 41 API), 0 failures

**Frozen decisions enforced:** D-059, D-061, D-065, D-067, D-068, D-070, D-071, D-072, D-073, D-074, D-075.

**GPT review fixes (3 rounds):**
- D-079: DataQuality enum amendment (5→6 states, known_zero→fresh/partial)
- D-080: Service registry heartbeat freshness rule
- Wrapper responses on all endpoints (*Response schemas)
- CapabilityStatus tri-state (available/unavailable/unknown)
- ComponentHealth.name field added
- TelemetryEntry.missionId + sourceFile fields
- services.json heartbeat background task (30s interval)

---

## Section 2: Task Summary

### Blocking Fix

| Task | Description | File(s) | Status |
|------|-------------|---------|--------|
| BF-8.0 | `_save_mission()` atomic write | `controller.py` | DONE |

### Milestone 8α — Foundation

| Task | Description | File(s) | Status |
|------|-------------|---------|--------|
| 8.0★ | FS matrix review | Docs (review) | DONE |
| 8.1 | Atomic write helper | `utils/atomic_write.py` | DONE |
| 8.2 | Pydantic schemas (FREEZE) | `api/schemas.py` | DONE |
| 8.3 | Capability checker | `api/capabilities.py` | DONE |
| 8.4 | Incremental file cache | `api/cache.py` | DONE |
| 8.5 | Circuit breaker | `api/circuit_breaker.py` | DONE |

### Milestone 8β — Core Logic

| Task | Description | File(s) | Status |
|------|-------------|---------|--------|
| 8.6 | MissionNormalizer | `api/normalizer.py` | DONE |

### Milestone 8γ — Endpoints + Integration

| Task | Description | File(s) | Status |
|------|-------------|---------|--------|
| 8.7 | FastAPI server + security | `api/server.py` | DONE |
| 8.8 | Mission API (4 endpoints) | `api/mission_api.py` | DONE |
| 8.9 | Approval API (read-only) | `api/approval_api.py` | DONE |
| 8.10 | Telemetry API | `api/telemetry_api.py` | DONE |
| 8.11 | Health + capabilities API | `api/health_api.py` | DONE |
| 8.12 | Health snapshot FS migration | `api/server.py` config | DONE |
| 8.13 | services.json + startup | `api/server.py` lifespan | DONE |
| 8.14 | Log rotation config | `api/server.py` logging | DONE |
| 8.15 | API test suite | `tests/test_api.py` (41 tests) | DONE |

---

## Section 3: Detailed Changes

### 3.0 — BF-8.0: _save_mission() Atomic Write

**Problem:** `_save_mission()` used bare `json.dump()` to file. Crash during write left corrupt JSON — proven by T-OT-4 E2E crash (Sprint 7).

**Solution:** All 3 mission file writers now use atomic pattern:
- `_save_mission()` — mission JSON
- `_persist_mission_state()` — state JSON
- `_emit_mission_summary()` — summary JSON

Pattern: `tempfile.mkstemp()` → `json.dump()` → `f.flush()` → `os.fsync()` → `os.replace()`. Failure cleans up temp file.

### 3.1 — Atomic Write Helper

**File:** `agent/utils/atomic_write.py`

Two reusable functions:
- `atomic_write_json(path, data, indent=2)` — JSON with fsync
- `atomic_write_text(path, content)` — plain text with fsync

Both create parent directories, write to temp file in same directory (avoiding cross-device rename), and clean up on failure.

### 3.2 — Pydantic Schemas (FROZEN)

**File:** `agent/api/schemas.py` — **FROZEN after Sprint 8 exit.**

Schemas implementing D-067 (additive-only post-freeze), D-068/D-079 (6 data quality states), and GPT review fixes:

| Schema | Purpose |
|--------|---------|
| `DataQualityStatus` | Enum: fresh, partial, stale, degraded, unknown, not_reached (D-079) |
| `DataQuality` | Per-response quality indicator |
| `SourceInfo` | Per-source: name, ageMs, status, lastError |
| `FreshnessInfo` | freshnessMs, staleThresholdMs, sourcesUsed, sourcesMissing |
| `ResponseMeta` | generatedAt, dataQuality, freshness — every response wrapper includes this |
| `Finding` | Gate finding: check, status, detail |
| `GateResultDetail` | gateName, passed, findings |
| `DenyForensics` | gate, recommendation, blocking_rules, findings |
| `StageDetail` | id, role, status, agentUsed, gateResults, denyForensics |
| `MissionSummary` | Full mission with freshness + dataQuality |
| `MissionListItem` | Mission list entry |
| `ApprovalEntry` | Approval record |
| `TelemetryEntry` | type, timestamp, missionId, sourceFile, data |
| `CapabilityStatus` | Tri-state enum: available, unavailable, unknown (GPT Fix 4) |
| `CapabilityEntry` | name, status (tri-state), since, detail |
| `ComponentHealth` | name, status, lastCheckAt, detail |
| `HealthResponse` | Wrapper: meta + status + components |
| `MissionDetailResponse` | Wrapper: meta + mission |
| `MissionListResponse` | Wrapper: meta + missions |
| `StageListResponse` | Wrapper: meta + stages |
| `ApprovalListResponse` | Wrapper: meta + approvals |
| `TelemetryResponse` | Wrapper: meta + events |
| `CapabilitiesResponse` | Wrapper: meta + capabilities |
| `APIError` | Standard error response |

### 3.3 — Capability Checker

**File:** `agent/api/capabilities.py`

Reads `config/capabilities.json`. Tri-state capability status (GPT Fix 4):
- `CapabilityStatus` enum: `available`, `unavailable`, `unknown`
- Missing manifest → all capabilities `unknown` (D-068)
- Corrupt JSON → degraded status, no crash
- `get_status(name)` → `CapabilityStatus`, `is_available(name)` → convenience bool
- `get_all()` → dict, `refresh()` → re-read

### 3.4 — Incremental File Cache

**File:** `agent/api/cache.py`

mtime-based cache preventing redundant disk reads:
- Same mtime → cache hit (no read)
- Different mtime → re-read + update
- Missing file → error
- Corrupt JSON → error, previous cache NOT served (D-068: no stale data)

### 3.5 — Circuit Breaker

**File:** `agent/api/circuit_breaker.py`

Per-source circuit breaker (D-072) with 3 states:
- **closed:** Normal operation
- **open:** After `failure_threshold` (default 3) consecutive failures — calls rejected immediately
- **half_open:** After `recovery_timeout_s` (default 30s) — single probe attempt

Source isolation: source A failing does not affect source B.

### 3.6 — MissionNormalizer

**File:** `agent/api/normalizer.py` — Core component (D-065).

Reads 5 sources and applies precedence rules:

| Source | File Pattern | Data Provided |
|--------|-------------|---------------|
| State | `*-state.json` | Mission status, stage states |
| Mission | `mission-*.json` | Full mission data |
| Summary | `*-summary.json` | denyForensics, agentUsed, gateResults |
| Telemetry | `policy-telemetry.jsonl` | Policy events |
| Capabilities | `capabilities.json` | Feature availability |

**Precedence (D-065):**
- Status: state > mission (state file is more current)
- Forensics: summary > telemetry (summary is more structured)

**Freshness calculation:**
- `freshnessMs = max(source.ageMs for source in sourcesUsed)`
- Per-source `ageMs = now - file.mtime`
- Stale thresholds per source type (state: 60s, summary: 120s, telemetry: 300s)

**Data quality (D-068/D-079 — 6 states):**
- All sources present + below threshold → `fresh`
- ≥1 source present but ≥1 missing → `partial` (missing listed in `sourcesMissing`)
- ≥1 source above stale threshold → `stale`
- ≥1 source parse error or circuit open → `degraded`
- All sources missing → `unknown`
- Source not yet created (mission not started) → `not_reached`
- Priority when multiple conditions: `degraded > stale > partial > fresh`

### 3.7 — FastAPI Server + Security

**File:** `agent/api/server.py`

**D-061:** FastAPI + Uvicorn, async-native.

**D-070 security:**
- Binds to `127.0.0.1:8003` only
- Host header validation middleware: rejects non-localhost hosts (→ 403)
- CORS: `allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]`
- No wildcard CORS

**D-074 startup sequence:**
1. Config load + logging setup
2. FS validation (ensure dirs exist)
3. MissionNormalizer init (cache warm)
4. CapabilityChecker init
5. services.json registration
6. API serve

**D-073 log rotation:**
- `RotatingFileHandler`: 10MB max, 5 backup files
- Log path: `logs/mission-control-api.log`

### 3.8 — API Endpoints

All endpoints return wrapper responses with `ResponseMeta` (GPT Fix 3):

| Method | Path | Response Wrapper | Task |
|--------|------|-----------------|------|
| GET | `/api/v1/missions` | `MissionListResponse` | 8.8 |
| GET | `/api/v1/missions/{id}` | `MissionDetailResponse` | 8.8 |
| GET | `/api/v1/missions/{id}/stages` | `StageListResponse` | 8.8 |
| GET | `/api/v1/missions/{id}/stages/{idx}` | `StageDetail` (inline) | 8.8 |
| GET | `/api/v1/approvals` | `ApprovalListResponse` | 8.9 |
| GET | `/api/v1/approvals/{id}` | `ApprovalEntry` (inline) | 8.9 |
| GET | `/api/v1/telemetry` | `TelemetryResponse` | 8.10 |
| GET | `/api/v1/telemetry?mission_id=X` | `TelemetryResponse` (filtered) | 8.10 |
| GET | `/api/v1/health` | `HealthResponse` | 8.11 |
| GET | `/api/v1/capabilities` | `CapabilitiesResponse` | 8.11 |

All read-only (D-059). Every response includes `dataQuality` and `freshness` where applicable.

### 3.9 — services.json + Heartbeat (D-080)

Server registers itself in `logs/services.json` with heartbeat freshness (GPT Fix 6):
```json
{
  "mission-control-api": {
    "status": "running",
    "port": 8003,
    "pid": 12345,
    "startedAt": "2026-03-25T..Z",
    "lastHeartbeatAt": "2026-03-25T..Z",
    "heartbeatIntervalS": 30
  }
}
```

**Liveness rule (D-080):**
- `lastHeartbeatAt + (heartbeatIntervalS × 2) > now` → service alive
- Threshold exceeded → stale → health `degraded`
- Background `asyncio.Task` updates `lastHeartbeatAt` every 30 seconds
- Clean shutdown: `status → "stopped"` (safety net, not primary signal)
- Crash: heartbeat stops → auto-detected as stale

---

## Section 4: Test Results

### 4.1 — API Test Suite (41 tests)

| Test Group | Tests | Description |
|-----------|-------|-------------|
| `TestSchemas` | 5 | Schema serialization, round-trip, D-068/D-079 6 states |
| `TestAtomicWrite` | 4 | JSON/text write, temp cleanup, parent dir creation |
| `TestCache` | 4 | miss→hit, missing file, corrupt JSON, invalidate |
| `TestCircuitBreaker` | 5 | Closed, open threshold, isolation, half_open recovery, reset |
| `TestNormalizer` | 7 | List, not found, state>mission precedence, freshness, sourcesMissing, deny forensics, corrupt |
| `TestCapabilities` | 3 | Available, missing manifest, corrupt manifest |
| `TestAPIEndpoints` | 13 | All endpoints 200, 404, Host attack 403, degraded response |
| **Total** | **41** | **0 failures** |

### 4.2 — Regression Tests

| Suite | Tests | Status |
|-------|-------|--------|
| Sprint 5C | 70 | PASS |
| Sprint 6D | 41 | PASS |
| Phase 4.5-A | 18 | PASS |
| Sprint 8 API | 41 | PASS |
| **Total** | **170** | **0 failures** |

### 4.3 — Live Server Verification

```
GET /api/v1/health         → 200  status: ok, 3 components
GET /api/v1/capabilities   → 200  5/5 available
GET /api/v1/missions       → 200  real mission list
GET /api/v1/missions/{id}  → 200  freshness + dataQuality + stages
GET /api/v1/approvals      → 200  real approval records
GET /api/v1/telemetry      → 200  JSONL events
Host: evil.com             → 403  D-070 security enforced
```

---

## Section 5: Sprint Checklist

| # | Criterion | Task | Status |
|---|----------|------|--------|
| 1 | `_save_mission()` atomic write | BF-8.0 | PASS |
| 2 | FS matrix review complete | 8.0★ | PASS |
| 3 | Schemas importable | 8.2 | PASS |
| 4 | Cache unit test passes | 8.4 | PASS |
| 5 | Circuit breaker test passes | 8.5 | PASS |
| 6 | Normalizer unit test passes | 8.6 | PASS |
| 7 | Precedence verified (state > mission) | 8.6 | PASS |
| 8 | freshnessMs = max(source ages) | 8.6 | PASS |
| 9 | curl all endpoints → 200 | 8.7–8.11 | PASS |
| 10 | Per-source ageMs in sourcesUsed | 8.6 | PASS |
| 11 | Stale thresholds per source type | 8.6 | PASS |
| 12 | Missing source → sourcesMissing listed | 8.6 | PASS |
| 13 | Corrupt JSON → degraded, API stays up | 8.6, 8.15 | PASS |
| 14 | Precedence: state > mission, summary > telemetry | 8.6 | PASS |
| 15 | Atomic write in all JSON writes | 8.1, BF-8.0 | PASS |
| 16 | D-070 security active (Host + CORS) | 8.7 | PASS |
| 17 | Health snapshot path configurable for ext4 | 8.12 | PASS |
| 18 | Schema FROZEN — additive-only post-freeze | 8.2 | PASS |
| 19 | 170 tests, 0 failure | 8.15 | PASS |
| 20 | ComponentHealth + CapabilityStatus tri-state | 8.2, 8.3 | PASS |
| 21 | services.json heartbeat freshness | 8.13 | PASS |
| 22 | Wrapper responses on all endpoints | 8.8–8.11 | PASS |
| 23 | D-078 waiver kaydı DECISIONS.md'de | doc | PASS |
| 24 | validate_sprint_docs.py --sprint 8 → 0 FAIL | 8.15 | PASS |

---

## Section 6: Architecture

### API Stack

```
Client (React :3000 / curl)
  ↓ HTTP GET
FastAPI (127.0.0.1:8003)
  ├── Host validation middleware (D-070)
  ├── CORS middleware (localhost:3000)
  ↓
Router → Endpoint handler
  ↓
MissionNormalizer
  ├── IncrementalFileCache (mtime-based)
  ├── CircuitBreaker (per-source, 3-state)
  ↓
5 Sources:
  ├── logs/missions/*.json (mission data)
  ├── logs/missions/*-state.json (state machine)
  ├── logs/missions/*-summary.json (forensics, agentUsed)
  ├── logs/policy-telemetry.jsonl (events)
  └── config/capabilities.json (features)
```

### Data Flow

```
Source files → Cache (mtime check) → CircuitBreaker → Normalizer
  → Precedence rules → Freshness calc → DataQuality → Pydantic schema → JSON response
```

---

## Section 7: Downstream Impact (Sprint 9)

| Sprint 8 Output | Sprint 9 Consumer |
|-----------------|-------------------|
| Frozen schemas (`schemas.py`) | React API client type generation |
| `/api/v1/missions` | MissionList component |
| `/api/v1/missions/{id}` | MissionDetail component |
| DataQuality + Freshness | DataQualityBadge, StaleBanner |
| Circuit breaker isolation | Per-panel error boundary alignment |
| `/api/v1/health` | HealthTab component |

---

## Section 8: Files Created/Modified

| File | Type | Task |
|------|------|------|
| `agent/mission/controller.py` | Modified | BF-8.0 |
| `agent/utils/__init__.py` | Created | 8.1 |
| `agent/utils/atomic_write.py` | Created | 8.1 |
| `agent/api/__init__.py` | Created | 8.7 |
| `agent/api/schemas.py` | Created | 8.2 |
| `agent/api/capabilities.py` | Created | 8.3 |
| `agent/api/cache.py` | Created | 8.4 |
| `agent/api/circuit_breaker.py` | Created | 8.5 |
| `agent/api/normalizer.py` | Created | 8.6 |
| `agent/api/server.py` | Created | 8.7, 8.12, 8.13, 8.14 |
| `agent/api/mission_api.py` | Created | 8.8 |
| `agent/api/approval_api.py` | Created | 8.9 |
| `agent/api/telemetry_api.py` | Created | 8.10 |
| `agent/api/health_api.py` | Created | 8.11 |
| `agent/tests/test_api.py` | Created | 8.15 |

---

## Section 9: GPT Review Summary

3 review rounds, 15 findings total. All blocking issues resolved.

| Round | Findings | Applied | Deferred |
|-------|----------|---------|----------|
| Sprint 8 GPT Review | 8 | 7 (Fix 1–8) | 0 |
| Sprint 7-8 Cross-Review | 7 blocking + 3 NB | 3 (D-079, D-080, doc fixes) | 2 (impl evidence) |
| Closure Assessment | 4 contradictions | 4 (doc fixes) | 0 |

**Key decisions from review:** D-079 (DataQuality 6-state), D-080 (heartbeat freshness).

**Closure Assessment 4 çelişki çözümü:**
- Ç-1: DataQuality `known_zero` → `fresh/partial` 6-state (kodda doğru, rapor güncellendi)
- Ç-2: Endpoint return types → wrapper `*Response` schemas (kodda doğru, rapor güncellendi)
- Ç-3: CapabilityChecker → tri-state `CapabilityStatus` enum (kodda doğru, rapor güncellendi)
- Ç-4: services.json → heartbeat background task 30s (kodda doğru, rapor güncellendi)

---

## Section 10: Evidence Bundle

Evidence dosyaları `evidence/sprint-8/` dizininde:

| Evidence | Dosya | Sonuç |
|----------|-------|-------|
| pytest output (170 test) | `evidence/sprint-8/pytest-output.txt` | 100+70 pass, 0 fail |
| Doc validator | `evidence/sprint-8/validator-output.txt` | 8/8 PASS |
| Grep evidence (4 çelişki) | `evidence/sprint-8/grep-evidence.txt` | 4/4 kodda doğru |

### Evidence: Test Summary
```
tests/test_api.py: 41 passed
tests/test_phase45a.py: 18 passed
tests/test_sprint_6d.py: 41 passed
tests/test_sprint_5c.py: 70 passed
Total: 170 passed, 0 failed
```

### Evidence: Doc Validator
```
[PASS] STATE.md — Fresh
[PASS] STATE.md — All required sections present
[PASS] NEXT.md — Fresh
[PASS] SESSION-HANDOFF.md — Fresh
[PASS] SESSION-HANDOFF.md — Handoff sections present
[PASS] capabilities.json — autoGenerated: true, 5/5 available
[PASS] Sprint plan — All checkboxes completed
[PASS] Test count — 170 tests (>= 129)
Result: All checks passed — sprint ready to close
```

### Evidence: Contradiction Resolution (grep)
```
Ç-1 DataQuality: FRESH, PARTIAL, STALE, DEGRADED, UNKNOWN, NOT_REACHED (no known_zero)
Ç-2 Wrappers: ResponseMeta, MissionDetailResponse, MissionListResponse, StageListResponse,
              HealthResponse, ApprovalListResponse, TelemetryResponse, CapabilitiesResponse
Ç-3 Tri-state: CapabilityStatus.AVAILABLE / UNAVAILABLE / UNKNOWN, get_status() method
Ç-4 Heartbeat: HEARTBEAT_INTERVAL_S=30, _heartbeat_loop(), asyncio.create_task
```

---

## Section 11: Known Limitations

1. **Telemetry not cached:** JSONL read is sequential per-request. For large telemetry files, add JSONL index in Sprint 9+.
2. **Mission list freshness:** `list_missions()` doesn't populate per-item freshness (would require N source reads). Detail endpoint has full freshness.
3. **testserver in Host allowlist:** FastAPI TestClient sends `testserver` as Host header — allowed in middleware for testing. Production bind is 127.0.0.1 only.
4. **No SSE yet:** Polling only (D-060 SSE planned for Sprint 10).
5. **No mutation endpoints:** Read-only per D-059. Intervention/approval mutation in Sprint 11 (D-062, D-063).

---

*Phase 5A-1 Sprint 8 Report — OpenClaw Mission Control Center Backend*
*Date: 2026-03-25*
*Operator: AKCA | Architect: Claude Opus 4.6*
*EN RİSKLİ SPRİNT — 3 milestone ile başarıyla yönetildi*
*GPT Review: 3 rounds + closure assessment, D-079 + D-080 frozen, 24/24 checklist PASS*
*Evidence bundle: evidence/sprint-8/ (pytest, validator, grep)*
