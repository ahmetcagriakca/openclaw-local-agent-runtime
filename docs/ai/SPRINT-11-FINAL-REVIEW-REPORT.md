# Sprint 11 Final Review Raporu — GPT'ye Gönderilecek

**Tarih:** 2026-03-26
**Sprint:** 11 — Phase 5C: Intervention / Mutation
**Review Tipi:** 11.FINAL — GPT Final Review (BLOCKER before closure)

---

## GPT'ye Gönderilecek Mesaj

`### — BAŞLANGIÇ —` ile `### — BİTİŞ —` arasını GPT'ye kopyala-yapıştır gönder.

---

### — BAŞLANGIÇ —

# Sprint 11 Final Review Request

**Project:** OpenClaw Local Agent Runtime
**Sprint:** 11 — Phase 5C: Intervention / Mutation
**Review Type:** 11.FINAL — Final Sprint Review (BLOCKER before closure)
**implementation_status:** done
**closure_status:** evidence_pending

## Context

Sprint 11 tüm code task'ları tamamlandı (11.0→11.11). Read-only Sprint 8-10 altyapısı üzerine mutation katmanı eklendi: 4 endpoint, CSRF middleware, atomic signal artifact bridge, mutation audit, D-096 lifecycle, frontend mutation UI. Bu review'ın PASS alması closure için zorunlu.

## Mid-Review PASS Recap

GPT mid-review backend completion sonrası PASS verdi. 4 kontrol alanı PASS:
1. **Contract drift** — 11/11 test PASS
2. **Ownership** — API'de controller/service import yok (grep: NO MATCHES)
3. **Lifecycle** — D-096 doğru uygulandı
4. **Security** — CSRF + duplicate + FSM validation çalışıyor

Mid-review follow-up: raw evidence dosyaları üretildi (ownership-grep.txt, bridge-check.txt, schema-compatibility.txt, contract-evidence.txt).

## Final Review Check Areas

1. **Frontend mutation UI** — ConfirmDialog, useMutation hook, approve/reject/cancel/retry buttons, toast feedback
2. **D-091 compliance** — Server-confirmed, no optimistic UI
3. **D-090 compliance** — Destructive actions (reject, cancel) require confirmation
4. **D-092 compliance** — Approval sunset warning on Telegram path
5. **End-to-end flow** — API → artifact → SSE → UI feedback chain
6. **Test coverage** — 195 backend (includes 11 contract) + 29 frontend = 224 total
7. **Schema compatibility** — MutationResponse additive-only (D-067 safe)

## Completed Tasks

| Task | Description | Commit |
|------|-------------|--------|
| 11.0 | DECISIONS.md D-081→D-096 (13 decisions, total 55) | `16427bc` |
| 11.1 | Contract-first test suite (11 tests, all FAIL → all PASS) | `947a396` |
| 11.2 | CSRF middleware — SameSite + Origin (D-089) | `6013eb2` |
| 11.3 | Mutation audit logger (requestId, tabId, sessionId) | `6013eb2` |
| 11.4 | Atomic request artifact bridge (D-001, D-062, D-063) | `9b245aa` |
| 11.5 | Approve/Reject endpoints + MutationResponse (D-096) | `e25053e` |
| 11.6 | Cancel/Retry endpoints | `e25053e` |
| 11.MID | GPT mid-review PASS + evidence patches | `25da086`, `42c05f3` |
| 11.7 | ConfirmDialog component (D-090) | `7054938` |
| 11.8 | Approval page mutation buttons | `7054938` |
| 11.9 | Mission detail cancel/retry buttons | `7054938` |
| 11.10 | useMutation hook + feedback (D-091) | `7054938` |
| 11.11 | Approval sunset warning (D-092) | `04122a9` |

**Remaining:** 11.12 (operator drill — manual, 5 live scenarios), 11.FINAL (this review).

## Architecture — Full Flow

```
Browser (React)
  → POST /api/v1/approvals/{id}/approve
  → Origin: http://localhost:3000, X-Tab-Id, X-Session-Id
  ↓
CSRFMiddleware (csrf_middleware.py)
  → validates Origin ∈ {localhost:3000, 127.0.0.1:3000, ...}
  → missing/invalid → 403
  ↓
approval_mutation_api.py
  → reads approval JSON, validates FSM state (must be "pending")
  → checks has_pending_signal() → 409 if duplicate exists
  → write_signal_artifact() → atomic JSON file
  → log_mutation() → MUTATION_AUDIT structured log
  → SSE broadcast: mutation_requested (best-effort)
  → returns MutationResponse { requestId, lifecycleState: "requested", timeoutAt }
  ↓
Signal Artifact (filesystem)
  logs/missions/{missionId}/approve-request-{requestId}.json
  ↓
Controller/Runtime (SOLE EXECUTOR — outside Sprint 11 scope)
  → polls ~1s, consumes artifact
  → SSE: mutation_accepted → mutation_applied | mutation_rejected | mutation_timed_out
  ↓
Frontend (useMutation hook)
  → receives MutationResponse → sets loading state
  → listens SSE: mutation_applied → success → refresh
  → listens SSE: mutation_rejected → error toast
  → listens SSE: mutation_timed_out OR 12s client timeout → timeout warning
  → NO optimistic UI (D-091)
```

## New Files — Full Source

### 1. agent/api/csrf_middleware.py (D-089)

```python
"""CSRF Middleware — D-089: SameSite=Strict + Origin Header Check.

Applied to POST requests only. Rejects requests without valid localhost Origin → 403.
Localhost single-operator system (D-070 extension).
"""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("mcc.csrf")

ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8003",
    "http://127.0.0.1:8003",
}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin", "")
            if not origin or origin not in ALLOWED_ORIGINS:
                logger.warning(
                    "CSRF reject: method=%s path=%s origin=%s",
                    request.method, request.url.path, origin or "(missing)",
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "forbidden",
                        "detail": "Missing or invalid Origin header",
                    },
                )
        return await call_next(request)
```

### 2. agent/api/mutation_audit.py

```python
"""Mutation Audit Logger — Sprint 11 Task 11.3.

Logs every mutation operation with required fields:
timestamp, source, operation, targetId, outcome, requestId, tabId, sessionId.
"""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("mcc.mutation.audit")


def log_mutation(
    *,
    request_id: str,
    operation: str,
    target_id: str,
    outcome: str,
    tab_id: str = "",
    session_id: str = "",
    detail: str = "",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "dashboard",
        "operation": operation,
        "targetId": target_id,
        "outcome": outcome,
        "requestId": request_id,
        "tabId": tab_id,
        "sessionId": session_id,
    }
    if detail:
        entry["detail"] = detail
    logger.info("MUTATION_AUDIT %s", json.dumps(entry, ensure_ascii=False))
```

### 3. agent/api/mutation_bridge.py (D-001, D-062, D-063)

```python
"""Mutation Bridge — Atomic request artifact writer.

Single rule: API only writes atomic request artifact;
runtime/controller remains sole executor.

Artifact path: logs/missions/{missionId}/{type}-request-{uuid}.json
"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.mutation.bridge")


def write_signal_artifact(
    *,
    missions_dir: Path,
    mutation_type: str,
    target_id: str,
    mission_id: str,
    tab_id: str = "",
    session_id: str = "",
) -> tuple[str, str, Path]:
    request_id = f"req-{uuid.uuid4()}"
    requested_at = datetime.now(timezone.utc).isoformat()

    artifact = {
        "requestId": request_id,
        "type": mutation_type,
        "targetId": target_id,
        "missionId": mission_id,
        "requestedAt": requested_at,
        "source": "dashboard",
        "operatorInfo": {
            "tabId": tab_id,
            "sessionId": session_id,
        },
    }

    mission_dir = missions_dir / mission_id
    mission_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = mission_dir / f"{mutation_type}-request-{request_id}.json"

    atomic_write_json(artifact_path, artifact)
    logger.info(
        "Signal artifact written: type=%s target=%s requestId=%s path=%s",
        mutation_type, target_id, request_id, artifact_path,
    )

    return request_id, requested_at, artifact_path


def has_pending_signal(
    missions_dir: Path,
    mission_id: str,
    mutation_type: str,
    target_id: str,
) -> Optional[str]:
    """Check if a pending signal artifact exists for same target+type.
    Returns existing requestId if found, None otherwise.
    """
    import json

    mission_dir = missions_dir / mission_id
    if not mission_dir.exists():
        return None

    pattern = f"{mutation_type}-request-req-*.json"
    for artifact_path in mission_dir.glob(pattern):
        try:
            data = json.loads(artifact_path.read_text(encoding="utf-8"))
            if data.get("targetId") == target_id:
                return data.get("requestId")
        except Exception:
            continue

    return None
```

### 4. agent/api/approval_mutation_api.py (D-096)

```python
"""Approval Mutation API — Sprint 11 Task 11.5.

POST /api/v1/approvals/{id}/approve
POST /api/v1/approvals/{id}/reject

D-096 lifecycle: API writes signal artifact → returns lifecycleState=requested.
D-001: No direct service/method call. Atomic signal artifact only.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from api.mutation_audit import log_mutation
from api.mutation_bridge import has_pending_signal, write_signal_artifact
from api.schemas import APIError, MutationResponse

logger = logging.getLogger("mcc.mutation.approval")

router = APIRouter(tags=["approval-mutations"])

MUTATION_TIMEOUT_S = 10


def _get_dirs():
    from api.server import APPROVALS_DIR, MISSIONS_DIR
    return APPROVALS_DIR, MISSIONS_DIR


def _read_approval(approvals_dir: Path, apv_id: str) -> dict | None:
    fpath = approvals_dir / f"{apv_id}.json"
    if not fpath.exists():
        return None
    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except Exception:
        return None


def _validate_approval_for_mutation(approval_data: dict, apv_id: str, operation: str):
    status = approval_data.get("status", "unknown")
    if status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Approval {apv_id} is '{status}', expected 'pending'. "
                   f"Cannot {operation} a non-pending approval.",
        )


def _extract_operator_info(request: Request) -> tuple[str, str]:
    return request.headers.get("x-tab-id", ""), request.headers.get("x-session-id", "")


async def _emit_mutation_requested(request, request_id, target_id, mutation_type):
    try:
        sse_mgr = getattr(request.app.state, "sse_manager", None)
        if sse_mgr:
            await sse_mgr.broadcast("mutation_requested", {
                "requestId": request_id, "targetId": target_id, "type": mutation_type,
            })
    except Exception as e:
        logger.warning("Failed to emit mutation_requested SSE: %s", e)


@router.post(
    "/approvals/{apv_id}/approve",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def approve_approval(apv_id: str, request: Request):
    approvals_dir, missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    approval_data = _read_approval(approvals_dir, apv_id)
    if approval_data is None:
        raise HTTPException(status_code=404, detail=f"Approval {apv_id} not found")

    _validate_approval_for_mutation(approval_data, apv_id, "approve")
    mission_id = approval_data.get("missionId", "unknown")

    existing = has_pending_signal(missions_dir, mission_id, "approve", apv_id)
    if existing:
        raise HTTPException(status_code=409,
            detail=f"Pending approve request already exists for {apv_id} (requestId={existing})")

    request_id, requested_at, _ = write_signal_artifact(
        missions_dir=missions_dir, mutation_type="approve", target_id=apv_id,
        mission_id=mission_id, tab_id=tab_id, session_id=session_id,
    )

    log_mutation(request_id=request_id, operation="approve", target_id=apv_id,
                 outcome="requested", tab_id=tab_id, session_id=session_id)

    await _emit_mutation_requested(request, request_id, apv_id, "approve")

    timeout_at = (datetime.fromisoformat(requested_at) + timedelta(seconds=MUTATION_TIMEOUT_S)).isoformat()
    return MutationResponse(requestId=request_id, lifecycleState="requested",
                            targetId=apv_id, requestedAt=requested_at, timeoutAt=timeout_at)


@router.post(
    "/approvals/{apv_id}/reject",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def reject_approval(apv_id: str, request: Request):
    # Same pattern as approve — validate, check duplicate, artifact, audit, SSE, respond
    approvals_dir, missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    approval_data = _read_approval(approvals_dir, apv_id)
    if approval_data is None:
        raise HTTPException(status_code=404, detail=f"Approval {apv_id} not found")

    _validate_approval_for_mutation(approval_data, apv_id, "reject")
    mission_id = approval_data.get("missionId", "unknown")

    existing = has_pending_signal(missions_dir, mission_id, "reject", apv_id)
    if existing:
        raise HTTPException(status_code=409,
            detail=f"Pending reject request already exists for {apv_id} (requestId={existing})")

    request_id, requested_at, _ = write_signal_artifact(
        missions_dir=missions_dir, mutation_type="reject", target_id=apv_id,
        mission_id=mission_id, tab_id=tab_id, session_id=session_id,
    )

    log_mutation(request_id=request_id, operation="reject", target_id=apv_id,
                 outcome="requested", tab_id=tab_id, session_id=session_id)

    await _emit_mutation_requested(request, request_id, apv_id, "reject")

    timeout_at = (datetime.fromisoformat(requested_at) + timedelta(seconds=MUTATION_TIMEOUT_S)).isoformat()
    return MutationResponse(requestId=request_id, lifecycleState="requested",
                            targetId=apv_id, requestedAt=requested_at, timeoutAt=timeout_at)
```

### 5. agent/api/mission_mutation_api.py

```python
"""Mission Mutation API — Sprint 11 Task 11.6.

POST /api/v1/missions/{id}/cancel
POST /api/v1/missions/{id}/retry

Same pattern as approval mutations. FSM state validation differs per action.
cancel: valid on {pending, planning, executing, gate_check, rework, approval_wait}
retry: valid on {failed, aborted, timed_out}
"""
# (Same structure as approval_mutation_api.py — omitted for brevity in review)
# Full source: agent/api/mission_mutation_api.py in repo
# Key differences:
#   - reads state.json instead of approval JSON
#   - CANCEL_VALID_STATES = {pending, planning, executing, gate_check, rework, approval_wait}
#   - RETRY_VALID_STATES = {failed, aborted, timed_out}
#   - writes cancel-request-{uuid}.json / retry-request-{uuid}.json
```

### 6. agent/api/schemas.py — MutationResponse (additive)

```python
class MutationResponse(BaseModel):
    """D-096 mutation response contract.
    API always returns lifecycleState=requested.
    Subsequent states (accepted/applied/rejected/timed_out) via SSE only.
    """
    requestId: str
    lifecycleState: str = "requested"
    targetId: str
    requestedAt: str
    acceptedAt: Optional[str] = None
    appliedAt: Optional[str] = None
    rejectedReason: Optional[str] = None
    timeoutAt: Optional[str] = None
```

### 7. frontend/src/components/ConfirmDialog.tsx (D-090)

```tsx
interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'default'
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel',
  variant = 'default', loading = false, onConfirm, onCancel,
}: ConfirmDialogProps) {
  if (!open) return null

  const confirmColor = variant === 'danger'
    ? 'bg-red-600 hover:bg-red-500 focus:ring-red-500'
    : 'bg-blue-600 hover:bg-blue-500 focus:ring-blue-500'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={loading ? undefined : onCancel} />
      <div className="relative z-10 w-full max-w-md rounded-lg border border-gray-700 bg-gray-800 p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
        <p className="mt-2 text-sm text-gray-300">{message}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onCancel} disabled={loading} className="rounded px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50">
            {cancelLabel}
          </button>
          <button onClick={onConfirm} disabled={loading} className={`flex items-center gap-2 rounded px-4 py-2 text-sm font-medium text-white disabled:opacity-50 ${confirmColor}`}>
            {loading && <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
```

### 8. frontend/src/hooks/useMutation.ts (D-091)

```typescript
export type MutationStatus = 'idle' | 'loading' | 'success' | 'error' | 'timeout'

export function useMutation(options: UseMutationOptions): UseMutationResult {
  // Flow: mutate() → POST → loading → SSE confirm → success/error/timeout
  // NO optimistic UI (D-091):
  //   - mutate() sets status='loading'
  //   - waits for MutationResponse from API
  //   - stores requestId, starts 12s client timeout
  //   - SSE mutation_applied → status='success' → onSuccess (refresh)
  //   - SSE mutation_rejected → status='error' → onError (toast)
  //   - SSE mutation_timed_out or client 12s → status='timeout' → onTimeout

  // Uses useSSEInvalidation for:
  //   'mutation_applied' → success
  //   'mutation_rejected' → error
  //   'mutation_timed_out' → timeout
}
```

### 9. frontend/src/pages/ApprovalsPage.tsx — Mutation Buttons

Key changes:
- `useState` for activeApprovalId, activeAction, confirmRejectId, toast
- `useMutation` for approve and reject
- **Approve** button: single click → `approveMutation.mutate()` (non-destructive, D-090)
- **Reject** button: opens ConfirmDialog first (destructive, D-090) → `rejectMutation.mutate()`
- Buttons disabled + spinner during loading (D-091)
- SSE invalidation on `mutation_applied` + `mutation_rejected` → refresh
- Toast notification for success / error / timeout

### 10. frontend/src/pages/MissionDetailPage.tsx — Cancel/Retry Buttons

Key changes:
- `useMutation` for cancel and retry
- **Cancel** button: visible on active states → ConfirmDialog (destructive, D-090)
- **Retry** button: visible on failed/aborted/timed_out → single click (non-destructive)
- Buttons disabled + spinner during loading (D-091)
- Toast notification for feedback

### 11. agent/services/approval_service.py — Sunset Warning (D-092)

```python
# Added to Telegram reply handler:
logger.warning(
    "APPROVAL_SUNSET D-092: Telegram %s used for %s. "
    "Dashboard approve/reject is the primary channel. "
    "Telegram approval will be removed in Sprint 12 (D-095).",
    reply, apv_id,
)
```

## Test Evidence

| Suite | Count | Status |
|-------|-------|--------|
| Backend (all) | 195 | ✅ ALL PASS |
| Contract tests (11) | 11 | ✅ ALL PASS |
| Frontend (all) | 29 | ✅ ALL PASS |
| **Total** | **224** | **0 failures** |
| TypeScript | — | 0 errors |
| ESLint | — | 0 errors |
| Vite build | — | 206KB JS, success |

## Contract Tests — 11/11 PASS

| # | Test | Verifies |
|---|------|----------|
| 1 | POST → lifecycleState=requested | D-096 response |
| 2 | SSE mutation_requested emitted | SSE + requestId correlation |
| 3 | Reject on already-approved → 409 | FSM validation |
| 4 | Timeout lifecycle (timeoutAt) | D-096 timeout |
| 5 | Duplicate approve → 409 | Race protection |
| 6 | Approve non-pending → 409 | Invalid FSM |
| 7 | Audit log fields | requestId, operation, targetId, tabId, sessionId |
| 8 | Signal artifact created | Atomic JSON in missions dir |
| 9 | POST without Origin → 403 | CSRF (D-089) |
| 10 | 2-tab race | First 200, second 409 |
| 11 | Cancel running mission | Signal artifact + lifecycle |

## Raw Evidence Files

| File | Content | Result |
|------|---------|--------|
| `ownership-grep.txt` | `grep controller/service` in agent/api/ | NO MATCHES |
| `bridge-check.txt` | `grep .approve()/.reject()` in agent/api/ | NO MATCHES |
| `contract-evidence.txt` | lifecycle field grep across agent+frontend | 67 lines |
| `schema-compatibility.txt` | MutationResponse additive + read-model intact | Verified |
| `contract-tests-initial.txt` | 11 tests pre-implementation | 11 FAILED |
| `contract-tests-final.txt` | 11 tests post-implementation | 11 PASSED |
| `closure-check-output.txt` | pytest + vitest + tsc + lint + build | ALL PASS |

## Frozen Decisions Compliance

| ID | Decision | Compliance |
|----|----------|------------|
| D-001 | Single execution owner = runtime | ✅ API writes artifact only |
| D-067 | Schema freeze (additive-only) | ✅ MutationResponse is new, read-models untouched |
| D-089 | CSRF Origin check enforced | ✅ CSRFMiddleware on all POST. SameSite depends on browser cookie context — Origin validation is the enforced layer. |
| D-090 | Confirm dialog for destructive | ✅ Reject + Cancel use ConfirmDialog |
| D-091 | Server-confirmed, no optimistic | ✅ useMutation waits for SSE |
| D-092 | Telegram sunset Phase 1 | ✅ APPROVAL_SUNSET logger.warning |
| D-096 | Full lifecycle response | ✅ MutationResponse schema + 11 tests |

## Remaining Before Closure

| # | Item | Owner |
|---|------|-------|
| 1 | Operator drill 11.12 (5 live scenarios) | Operator |
| 2 | `live-checks.txt` | Operator |
| 3 | Retrospective | Claude (after this review) |
| 4 | `closure-check.sh` run | Operator (WSL) |

## Questions for Review

1. **Frontend mutation flow:** D-091 server-confirmed pattern doğru uygulandı mı? useMutation hook'ta optimistic state var mı?
2. **ConfirmDialog:** D-090 — destructive action'lar (reject, cancel) onay gerektiriyor, non-destructive (approve, retry) tek click. Doğru mu?
3. **CSRF coverage:** CSRFMiddleware tüm POST'lara uygulanıyor. Bypass riski var mı?
4. **Schema compatibility:** MutationResponse eklenmesi mevcut read-model type'larını etkiliyor mu?
5. **Audit completeness:** Her mutation requestId + tabId + sessionId logluyor. Eksik alan var mı?
6. **SSE event flow:** useMutation 3 event dinliyor (applied/rejected/timed_out). mutation_accepted dinlenmemeli mi?
7. **Error handling:** API 404/409 hatalarını frontend doğru yakalıyor mu?

## Expected Review Output

```
VERDICT: PASS | FAIL
BLOCKING ISSUES: (list or "none")
NON-BLOCKING NOTES: (list or "none")
RECOMMENDATION: Proceed to closure | Fix issues first
```

### — BİTİŞ —

---

## Notlar

- `### — BAŞLANGIÇ —` ile `### — BİTİŞ —` arasını GPT'ye kopyala-yapıştır gönder.
- GPT PASS verirse → retrospective yazılır → operator drill sonrası closure.
- GPT FAIL verirse → blocking issue'lar çözülür → tekrar review.
- Review çıktısını `evidence/sprint-11/review-final.md` olarak kaydet.
