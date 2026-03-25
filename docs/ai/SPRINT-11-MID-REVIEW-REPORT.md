# Sprint 11 Mid-Review Raporu — GPT'ye Sunulacak

**Tarih:** 2026-03-26
**Sprint:** 11 — Phase 5C: Intervention / Mutation
**Review Tipi:** 11.MID — GPT Mid-Sprint Review (BLOCKER)
**Amaç:** Backend implementasyonu tamamlandı, frontend task'lara geçiş için GPT onayı gerekli.

---

## GPT'ye Gönderilecek Mesaj

Aşağıdaki mesajı GPT'ye (cross-reviewer) kopyala-yapıştır olarak gönder:

---

### — BAŞLANGIÇ —

# Sprint 11 Mid-Sprint Review Request

**Project:** OpenClaw Local Agent Runtime
**Sprint:** 11 — Phase 5C: Intervention / Mutation
**Review Type:** 11.MID — Mid-Sprint Review (BLOCKER before frontend tasks)
**Risk Level:** HIGH — read-only → read-write transition

## Context

Sprint 11, dashboard'a operator müdahale (approve, reject, cancel, retry) yeteneği ekliyor. Read-only Sprint 8-10 altyapısı üzerine mutation katmanı ekleniyor. Backend tamamen implement edildi. Frontend task'lara geçmeden önce bu review'ın PASS alması zorunlu.

## Mutation Sprint — Mandatory Check Areas

Mutation sprint'lerde mid-review şu 4 alanı kontrol etmelidir:
1. **Contract drift** — test'lerle endpoint'ler arasında tutarsızlık var mı?
2. **Ownership** — API direct controller/service call yapıyor mu? (yasak)
3. **Lifecycle** — D-096 (requested→accepted→applied|rejected|timed_out) doğru mu?
4. **Security** — CSRF, Origin validation, duplicate protection çalışıyor mu?

## Completed Tasks (Backend — 11.0 through 11.6)

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 11.0 | DECISIONS.md debt burn-down D-081→D-096 (13 decisions) | `16427bc` | ✅ DONE |
| 11.1 | Contract-first test suite (11 tests, all FAIL initially) | `947a396` | ✅ DONE |
| 11.2 | CSRF middleware — SameSite + Origin header check (D-089) | `6013eb2` | ✅ DONE |
| 11.3 | Mutation audit logger (requestId, tabId, sessionId) | `6013eb2` | ✅ DONE |
| 11.4 | Atomic request artifact bridge (D-001, D-062, D-063) | `9b245aa` | ✅ DONE |
| 11.5 | Approve/Reject endpoints + MutationResponse (D-096) | `e25053e` | ✅ DONE |
| 11.6 | Cancel/Retry endpoints | `e25053e` | ✅ DONE |

## Remaining Tasks (Frontend — blocked on this review)

| Task | Description | Status |
|------|-------------|--------|
| 11.7 | Confirmation dialog component (D-090) | ⬜ BLOCKED |
| 11.8 | Approval page mutation buttons | ⬜ BLOCKED |
| 11.9 | Mission detail cancel/retry buttons | ⬜ BLOCKED |
| 11.10 | Mutation feedback (spinner, error toast, SSE confirm) | ⬜ BLOCKED |
| 11.11 | Approval sunset warning — Telegram deprecated (D-092) | ⬜ BLOCKED |
| 11.12 | Manual operator drill (5 scenarios) | ⬜ BLOCKED |

## Architecture — Mutation Bridge Pattern

```
Dashboard (React)
    ↓ POST /api/v1/approvals/{id}/approve
    ↓ Origin: http://localhost:3000
API Layer (FastAPI)
    ↓ CSRF middleware validates Origin (D-089)
    ↓ FSM state validation (pending → approve allowed)
    ↓ Duplicate signal check (→ 409 if pending exists)
    ↓ write_signal_artifact() → atomic JSON file
    ↓ audit log (MUTATION_AUDIT JSON line)
    ↓ SSE broadcast: mutation_requested (best-effort)
    ↓ HTTP response: { requestId, lifecycleState: "requested", ... }
    ↓
Signal Artifact (filesystem)
    logs/missions/{missionId}/{type}-request-{requestId}.json
    ↓
Controller/Runtime (SOLE EXECUTOR — not API)
    ↓ polls ~1s, consumes artifact
    ↓ SSE: mutation_accepted → mutation_applied | mutation_rejected | mutation_timed_out
```

**Critical rule:** API layer NEVER calls controller/service methods directly. API only writes an atomic signal artifact file. Controller is the sole executor (D-001, D-062, D-063).

## Frozen Decisions in This Sprint

| ID | Decision | Status |
|----|----------|--------|
| D-089 | CSRF: SameSite + Origin header check | Frozen |
| D-090 | Confirm dialog for destructive actions (cancel, reject) | Frozen |
| D-091 | Server-confirmed UI, no optimistic update | Frozen |
| D-092 | Approval sunset Phase 1 (Telegram deprecated warning) | Frozen |
| D-096 | Mutation response contract: full lifecycle with requestId | Frozen |

## File Inventory — Created/Modified

| File | Type | Purpose |
|------|------|---------|
| `agent/api/csrf_middleware.py` | NEW | D-089 Origin validation for POST |
| `agent/api/mutation_audit.py` | NEW | Structured MUTATION_AUDIT JSON log |
| `agent/api/mutation_bridge.py` | NEW | Atomic signal artifact writer + duplicate check |
| `agent/api/approval_mutation_api.py` | NEW | POST approve/reject endpoints |
| `agent/api/mission_mutation_api.py` | NEW | POST cancel/retry endpoints |
| `agent/api/schemas.py` | MODIFIED | MutationResponse schema added (D-096) |
| `agent/api/server.py` | MODIFIED | CSRF middleware + mutation routers registered, CORS POST added |
| `agent/tests/test_mutation_contracts.py` | NEW | 11 contract tests |
| `docs/ai/DECISIONS.md` | MODIFIED | D-081→D-096 (13 decisions added, total 55) |

## MutationResponse Schema (D-096)

```python
class MutationResponse(BaseModel):
    requestId: str              # "req-uuid"
    lifecycleState: str         # always "requested" from API
    targetId: str               # approval ID or mission ID
    requestedAt: str            # ISO-8601
    acceptedAt: Optional[str]   # null from API (controller sets)
    appliedAt: Optional[str]    # null from API (controller sets)
    rejectedReason: Optional[str]  # null from API (controller sets)
    timeoutAt: Optional[str]    # requestedAt + 10s
```

## Contract Tests — 11 Tests, All PASS

| # | Test | What It Verifies | Result |
|---|------|-----------------|--------|
| 1 | POST mutation → lifecycleState=requested | D-096 lifecycle response | ✅ PASS |
| 2 | SSE mutation_requested emitted | SSE event + requestId correlation | ✅ PASS |
| 3 | Reject on already-approved → 409 | FSM state validation | ✅ PASS |
| 4 | Timeout lifecycle (timeoutAt field) | D-096 timeout window | ✅ PASS |
| 5 | Duplicate approve → 409 | Race condition protection | ✅ PASS |
| 6 | Approve on non-pending → 409/422 | Invalid FSM state rejection | ✅ PASS |
| 7 | Audit log fields present | requestId, operation, targetId, tabId, sessionId | ✅ PASS |
| 8 | Signal artifact created | Atomic JSON file in missions dir | ✅ PASS |
| 9 | POST without Origin → 403 | CSRF protection (D-089) | ✅ PASS |
| 10 | 2-tab race (approve × 2) | First 200, second 409 | ✅ PASS |
| 11 | Cancel running mission | Signal artifact + lifecycle response | ✅ PASS |

## Test Counts

| Suite | Count | Status |
|-------|-------|--------|
| Backend total | 195 | ✅ ALL PASS |
| Sprint 11 contract tests | 11 | ✅ ALL PASS |
| Frontend (unchanged) | 29 | ✅ ALL PASS |

## Security Checklist

| Check | Implementation | Evidence |
|-------|---------------|----------|
| CSRF Origin validation | `csrf_middleware.py` — POST without valid Origin → 403 | Test 9 PASS |
| Duplicate mutation prevention | `mutation_bridge.has_pending_signal()` → 409 | Test 5, 10 PASS |
| FSM state validation | Approve/reject only on "pending", cancel on active states | Test 3, 6 PASS |
| No direct controller call | API writes file only, `write_signal_artifact()` | Preliminary grep validation (raw evidence at final closure) |
| Audit trail | Every mutation logged with requestId + operator info | Test 7 PASS |
| Host header validation | Existing D-070 middleware (unchanged) | Sprint 8 tests |

## Ownership Check — API Does NOT Call Controller

```
# grep for direct service/controller imports in mutation endpoints:
grep -rn "from.*controller\|from.*service\|import.*controller\|import.*service" agent/api/approval_mutation_api.py agent/api/mission_mutation_api.py
# Expected: EMPTY (no results)

# What API imports instead:
grep -rn "from api.mutation_bridge import" agent/api/approval_mutation_api.py agent/api/mission_mutation_api.py
# Result: write_signal_artifact, has_pending_signal (file I/O only)
```

## Verification Commands

```bash
# 1. Run all contract tests
cd agent && python -m pytest tests/test_mutation_contracts.py -v

# 2. Run all backend tests
cd agent && python -m pytest tests/ -v

# 3. CSRF evidence
cd agent && python -c "
from fastapi.testclient import TestClient
from api.server import app
c = TestClient(app)
r = c.post('/api/v1/approvals/test/approve')
print(f'No Origin: {r.status_code}')  # expect 403
r = c.post('/api/v1/approvals/test/approve', headers={'Origin': 'http://evil.com'})
print(f'Bad Origin: {r.status_code}')  # expect 403
"

# 4. Ownership evidence (no controller/service imports)
grep -rn "from.*controller\|from.*service" agent/api/approval_mutation_api.py agent/api/mission_mutation_api.py

# 5. Decision count
grep -c "^### D-" docs/ai/DECISIONS.md
# expect: 55
```

## Questions for Review

1. **Contract drift:** Test'ler ile endpoint implementasyonu arasında tutarsızlık görüyor musun?
2. **Ownership:** API katmanında controller/service'e doğrudan erişim var mı?
3. **Lifecycle:** D-096 lifecycle (requested → accepted → applied | rejected | timed_out) doğru uygulandı mı?
4. **Security:** CSRF, duplicate protection, FSM validation yeterli mi? Eksik attack vector var mı?
5. **Schema freeze:** MutationResponse eklenmesi D-067 freeze kuralını ihlal ediyor mu? (Additive-only rule)

## Expected Review Output

```
VERDICT: PASS | FAIL
BLOCKING ISSUES: (list or "none")
NON-BLOCKING NOTES: (list or "none")
RECOMMENDATION: Proceed to frontend tasks | Fix issues first
```

## Ownership Judgment Note

Mid-review ownership judgment is based on current code structure and preliminary grep validation; final closure requires raw negative evidence files in the closure packet and will not rely on narrative inspection text alone.

## FOLLOW-UP PATCHES FOR FINAL REVIEW

These items are non-blocking for 11.MID PASS, but mandatory before 11.FINAL closure assessment.

### 1) Ownership / bridge negative evidence must move from inspection text to raw evidence
Current mid-review judgment is accepted, but final closure cannot rely on "code inspection" wording alone.

Required final evidence:
- `evidence/sprint-11/ownership-grep.txt`
- `evidence/sprint-11/bridge-check.txt`

Required checks:
- no direct controller execution from API layer
- no direct service execution bypassing atomic request artifact bridge
- mutation API writes artifact only; runtime/controller remains sole executor

### 2) Mutation lifecycle raw evidence must be preserved
Final closure must include raw evidence for:
- `mutation_requested`
- `mutation_accepted`
- `mutation_applied`
- `mutation_rejected`
- `mutation_timed_out`
- `requestId`
- `lifecycleState`

Required final evidence:
- `evidence/sprint-11/contract-evidence.txt`

### 3) Additive-only compatibility must be checked explicitly
D-067 compatibility must not be assumed.

Required final evidence:
- `evidence/sprint-11/schema-compatibility.txt`

Required checks:
- no breaking change to existing read-model response contracts
- mutation response introduced as additive schema
- existing frontend read paths remain valid

### 4) Manual operator drill remains the real closure gate
Mid-review PASS does not waive:
- two-tab race verification
- cancel during active execution
- retry while pending
- timeout recovery
- SSE correlation verification

### — BİTİŞ —

---

## Notlar

- `### — BAŞLANGIÇ —` ile `### — BİTİŞ —` arasını GPT'ye kopyala-yapıştır gönder.
- GPT'nin PASS vermesi durumunda 11.7+ frontend task'larına geçilir.
- GPT FAIL verirse blocking issue'lar çözülene kadar frontend'e geçilmez.
- Review çıktısını `evidence/sprint-11/review-mid.md` olarak kaydet.
