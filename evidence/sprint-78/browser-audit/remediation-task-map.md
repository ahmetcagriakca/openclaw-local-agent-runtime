# Remediation Task Map — S78 UX Findings

## Work Package: FE-ERR-01 — Unified API Error State Contract

**Findings:** UX-001, UX-002, UX-003, UX-004, UX-005
**Priority:** P1 (3 high + 2 medium severity)
**Owner:** Claude Code (S79)
**Sprint:** S79 candidate

### Root Cause (CONFIRMED in code)

**File:** `frontend/src/api/client.ts:46-52`

```typescript
async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    let body: unknown
    try {
      body = await res.json()   // line 49: reads response body
    } catch {
      body = await res.text()   // line 51: reads body AGAIN → "body stream already read"
    }
    throw new ApiError(res.status, body)
  }
  return res.json() as Promise<T>
}
```

When backend is unreachable, Vite dev proxy returns 502/504. `res.json()` fails (not valid JSON), then `res.text()` attempts second read on already-consumed body stream. The resulting `TypeError: Failed to execute 'text' on 'Response': body stream already read` is what users see.

Same pattern exists in `apiPost` (line 134-140) and `apiPatchJson` (line 335-337).

### Fix Strategy

1. **Clone response before reading:** `const clone = res.clone()` before first read attempt
2. **Or use text-first approach:** `const text = await res.text()` then `JSON.parse(text)` in try/catch
3. **Create shared `useApiCall` hook** with:
   - Loading / error / data / empty state machine
   - User-friendly error messages per error class
   - Always-present Retry callback
   - Error OR empty, never both

### Target Files

| File | Change |
|------|--------|
| `frontend/src/api/client.ts` | Fix double-read bug in apiGet/apiPost/apiPatchJson |
| `frontend/src/hooks/useApiCall.ts` | NEW: shared hook with state machine |
| `frontend/src/components/ApiErrorBanner.tsx` | NEW: reusable error banner with Retry |
| `frontend/src/pages/MissionsPage.tsx` | Use useApiCall + ApiErrorBanner |
| `frontend/src/pages/HealthPage.tsx` | Use useApiCall + ApiErrorBanner (adds Retry — UX-002) |
| `frontend/src/pages/AgentsPage.tsx` | Use useApiCall + ApiErrorBanner (adds error state — UX-003) |
| `frontend/src/pages/ProjectsPage.tsx` | Use useApiCall, fix contradictory state (UX-004) |
| `frontend/src/pages/MonitoringPage.tsx` | Use useApiCall, fix mixed states (UX-005) |

### Verification

- Start frontend without backend → every page shows "API Unreachable" + Retry
- No "body stream already read" visible to user
- Error state and empty state never shown simultaneously
- Retry button present on all error states

---

## Work Package: FE-SSE-01 — SSE Connection Health Truthfulness

**Finding:** UX-007
**Priority:** P2 (medium severity)
**Owner:** Claude Code (S79)
**Sprint:** S79 candidate

### Target Files

| File | Change |
|------|--------|
| `frontend/src/hooks/useSSE.ts` or equivalent | Track consecutive failures, expose connection state |
| `frontend/src/components/SSEStatus.tsx` or equivalent | 3-state indicator: Connected (green) / Reconnecting (yellow) / Disconnected (red) |

### Verification

- Backend offline → status shows red "Disconnected"
- Backend online → status shows green "Connected"
- Backend flapping → status shows yellow "Reconnecting..." during attempts

---

## Work Package: FE-NAV-01 — Collapsed Sidebar Tooltip/Accessibility

**Finding:** UX-006
**Priority:** P3 (medium severity)
**Owner:** Claude Code (S79)
**Sprint:** S79 candidate

### Target Files

| File | Change |
|------|--------|
| `frontend/src/components/Sidebar.tsx` or equivalent | Add `title` attribute or tooltip component to nav items in collapsed state |

### Verification

- Hover over any sidebar icon in collapsed state → tooltip shows page name
- Keyboard focus on sidebar item → accessible name announced

---

## Summary

| Work Package | Findings | Severity | Files | Verification |
|-------------|----------|----------|-------|-------------|
| FE-ERR-01 | UX-001/002/003/004/005 | 3H + 2M | ~8 files | No technical error to user, Retry everywhere |
| FE-SSE-01 | UX-007 | 1M | ~2 files | 3-state connection indicator |
| FE-NAV-01 | UX-006 | 1M | ~1 file | Tooltip on hover |
