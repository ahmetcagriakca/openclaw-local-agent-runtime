# Phase 5A-2 — Sprint 9: React Read-Only UI

**Date:** 2026-03-25
**Status:** COMPLETE
**Author:** Operator (AKCA) + Claude (Copilot)
**Prerequisite:** Sprint 8 CLOSED (evidence: d20b05a, 4/4 contradiction resolved)
**Risk Level:** MEDIUM — UI sprint, backend stable
**GPT Review:** DONE — GPT cross-review handoff received 2026-03-25, closure pass executed, all items resolved

---

## Section 1: Executive Summary

Sprint 9 delivers the Mission Control Center frontend — a React + TypeScript + Tailwind dashboard that connects to the Sprint 8 FastAPI backend. 8 typed client functions cover 10 backend endpoints (6 actively consumed by pages, 2 defined for future use). The UI enforces data quality visualization rules established in D-068/D-079: every panel shows freshness, 6 data quality states are rendered distinctly, unknown ≠ zero, missing ≠ healthy, and silent absence is forbidden.

**Key outcomes:**
- React app on `:3000` with Vite proxy to `:8003`
- 22 TypeScript types from 22 frozen Pydantic schemas (1:1 match, D-067/D-082)
- Typed API client: 8 functions covering 10 endpoints (6 actively consumed by pages)
- Polling hook: 30s global interval + manual refresh + Page Visibility pause (D-083)
- DataQualityBadge: 6 distinct visual states (color + icon + label) (D-079)
- FreshnessIndicator: human-readable age, stale threshold alert, source status
- 5 pages: Missions, Mission Detail, Health, Approvals, Telemetry
- Per-panel ErrorBoundary isolation (D-084)
- Sidebar navigation with active route highlighting
- 18 Vitest tests, 0 failures
- 0 TypeScript errors, production build successful (195 KB JS / 61 KB gzip)

**Frozen decisions enforced:** D-067, D-079, D-081, D-082, D-083, D-084.

**Environment note:** Node.js 20.18.1 LTS portable installed at `C:\Users\AKCA\node20\` — system Node.js 14.19.2 is incompatible with Vite 6.

---

## Section 2: Task Summary

| Task | Description | File(s) | Effort | Status |
|------|-------------|---------|--------|--------|
| 9.1 | Vite + React + TS + Tailwind scaffold | `frontend/*` config files | S | DONE |
| 9.2 | TypeScript type definitions (22 types) | `src/types/api.ts` | M | DONE |
| 9.3 | API client + polling hook | `src/api/client.ts`, `src/hooks/usePolling.ts` | M | DONE |
| 9.4 | DataQualityBadge + FreshnessIndicator | `src/components/DataQualityBadge.tsx`, `FreshnessIndicator.tsx` | M | DONE |
| 9.5 | MissionList page | `src/pages/MissionListPage.tsx` | M | DONE |
| 9.6 | MissionDetail + StageTimeline + StageCard | `src/pages/MissionDetailPage.tsx`, `StageTimeline.tsx`, `StageCard.tsx` | L | DONE |
| 9.7 | HealthDashboard + Capabilities | `src/pages/HealthPage.tsx` | M | DONE |
| 9.8 | ApprovalList + TelemetryView | `src/pages/ApprovalsPage.tsx`, `TelemetryPage.tsx` | M | DONE |
| 9.9 | Layout, Router, Sidebar, ErrorBoundary | `src/App.tsx`, `Layout.tsx`, `Sidebar.tsx`, `ErrorBoundary.tsx` | M | DONE |
| 9.10 | Smoke tests (18 tests) | `src/__tests__/*.test.tsx` | M | DONE |

---

## Section 3: Detailed Changes

### 3.1 — Task 9.1: Vite + React + TypeScript Scaffold

**Files:** `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`, `eslint.config.js`, `index.html`, `src/main.tsx`, `src/index.css`, `src/vite-env.d.ts`

**Stack:**
- React 18.3.1 + ReactDOM
- TypeScript 5.6 (strict mode)
- Vite 6.4.1 (dev server + bundler)
- Tailwind CSS 3.4.15 (D-081)
- react-router-dom 6.28.0
- Vitest 2.1.5 + @testing-library/react 16

**Vite proxy config:**
```typescript
server: {
  port: 3000,
  proxy: { '/api': { target: 'http://127.0.0.1:8003' } }
}
```

**TypeScript strict mode:** `strict: true`, `noUnusedLocals`, `noUnusedParameters`, `noUncheckedIndexedAccess`, `noFallthroughCasesInSwitch`.

### 3.2 — Task 9.2: TypeScript Type Definitions

**File:** `src/types/api.ts` — 22 exported types from frozen `schemas.py` (D-082).

| Category | Types |
|----------|-------|
| Enums (3) | `DataQualityStatus` (6 values), `MissionState` (10 values), `CapabilityStatus` (3 values) |
| Core Models (11) | `SourceInfo`, `ResponseMeta`, `Finding`, `GateResultDetail`, `StageDetail`, `MissionSummary`, `MissionListItem`, `CapabilityEntry`, `ComponentHealth`, `ApprovalEntry`, `TelemetryEntry` |
| Response Wrappers (7) | `MissionDetailResponse`, `MissionListResponse`, `StageListResponse`, `HealthApiResponse`, `ApprovalListResponse`, `TelemetryListResponse`, `CapabilityListResponse` |
| Error (1) | `APIError` |

**Validation:** `grep "^class " schemas.py | wc -l` = 22, `grep "^export" api.ts | wc -l` = 22. Exact match.

**D-079 compliance:** `DataQualityStatus` contains exactly 6 values: `fresh`, `partial`, `stale`, `degraded`, `unknown`, `not_reached`. No `known_zero`.

### 3.3 — Task 9.3: API Client + Polling Hook

**API Client (`src/api/client.ts`):**
- Generic `apiGet<T>(path)` with typed response
- `ApiError` class: HTTP status + response body
- 8 named functions: `getMissions()`, `getMission(id)`, `getStages(missionId)`, `getStage(missionId, idx)`, `getApprovals()`, `getTelemetry(missionId?)`, `getHealth()`, `getCapabilities()`
- Base URL: `/api/v1` (Vite proxy handles routing to `:8003`)
- URL params properly encoded with `encodeURIComponent()`

**Polling Hook (`src/hooks/usePolling.ts`):**
- Signature: `usePolling<T>(fetcher, intervalMs?) → { data, error, loading, refresh, lastFetchedAt }`
- D-083: default interval 30,000ms
- `refresh()` → immediate fetch trigger
- Page Visibility API: tab hidden → polling stops, tab visible → immediate fetch + restart
- Error resilience: last successful `data` preserved on error
- Cleanup: `clearInterval` + `removeEventListener` on unmount

### 3.4 — Task 9.4: DataQualityBadge + FreshnessIndicator

**DataQualityBadge (`src/components/DataQualityBadge.tsx`):**

6 distinct visual states (D-079):

| State | Background | Icon | Label | Visual Distinction |
|-------|-----------|------|-------|--------------------|
| `fresh` | Green (600) | ✓ | Fresh | Solid green — healthy |
| `partial` | Lime (500) | ◐ | Partial | Yellow-green — partially available |
| `stale` | Orange (500) | ⏳ | Stale | Warm warning |
| `degraded` | Red (600) | ⚠ | Degraded | Danger |
| `unknown` | Gray (500) | ? | Unknown | Mid-gray — indeterminate |
| `not_reached` | Dark Gray (700) | — | Not Reached | Darkest — never attempted |

- Tooltip: quality label + optional detail + assessedAt timestamp
- `unknown` and `not_reached` are visually distinct (different gray tone, different icon, different label)

**FreshnessIndicator (`src/components/FreshnessIndicator.tsx`):**
- Human-readable age: ms → "2s ago", "45s ago", "3m ago", "2h ago"
- Stale threshold: `freshnessMs > staleThresholdMs` → red border + background
- Source status: green dot for `sourcesUsed`, red dot + "Missing:" for `sourcesMissing`
- Polling age: "Polled Xs ago" from `lastFetchedAt`

### 3.5 — Task 9.5: MissionList Page

**File:** `src/pages/MissionListPage.tsx`

- Calls `getMissions()` via `usePolling` (30s)
- Each mission: ID (truncated at 16 chars), status badge, data quality badge
- Stage progress: "Stage X/Y"
- Goal text (line-clamped)
- Click → navigate to `/missions/{id}`
- Response-level `FreshnessIndicator`

**Explicit states (silent absence forbidden):**
- Loading: animated spinner + "Loading missions…"
- Error: red panel + message + "Retry" button
- Empty: centered "No missions found"

**MissionStateBadge (`src/components/MissionStateBadge.tsx`):**
- 10 FSM states → 10 distinct colors (pending=gray, planning=blue, executing=indigo, gate_check=yellow, rework=orange, approval_wait=purple, completed=green, failed=red, aborted=dark red, timed_out=dark red)

### 3.6 — Task 9.6: MissionDetail + StageTimeline + StageCard

**MissionDetailPage (`src/pages/MissionDetailPage.tsx`):**
- Header: missionId, state badge, data quality badge, goal, complexity, dates, duration, artifacts, policy denies
- `FreshnessIndicator` with response-level meta
- 404 handling: `ApiError.status === 404` → "Mission not found" with ID shown
- Back navigation: "← Back to missions"
- Mission-level deny forensics (always visible, never hidden)

**StageTimeline (`src/components/StageTimeline.tsx`):**
- Horizontal pipeline: stages connected by lines
- Each stage: role label, status, agent model, gate result indicator
- Status colors: passed/completed=green, failed=red, running=indigo, pending=gray
- Gate passed → green ✓, gate failed → red ✗ + finding count
- Rework indicator: ↻ icon
- Click to select → ring highlight

**StageCard (`src/components/StageCard.tsx`):**
- Expanded detail for selected stage
- Metrics: tool calls, policy denies, started/finished timestamps
- Gate results panel: green/red background, finding list with check/status/detail
- **Deny forensics: always visible when present** — formatted JSON in amber panel
- Agent model shown (`agentUsed`)
- Rework cycle number and recovery indicator

### 3.7 — Task 9.7: HealthDashboard + Capabilities

**HealthPage (`src/pages/HealthPage.tsx`):**

**Health section:**
- Overall status badge: ok=green, degraded=orange, error=red, unknown=gray
- Component grid (responsive: 1→2→3 columns): each component card with name, status badge, detail, last check timestamp
- Empty state: "No components reported"

**Capabilities section:**
- Each capability: name + tri-state badge (D-068)
  - `available` → green ✓
  - `unavailable` → red ✗
  - `unknown` → gray ? (distinct from unavailable — "bilinmiyor", not "yok")
- Empty state: "No capabilities reported"

### 3.8 — Task 9.8: ApprovalList + TelemetryView

**ApprovalsPage (`src/pages/ApprovalsPage.tsx`):**
- Read-only list (mutation deferred to Sprint 11)
- Each approval: ID, status (color-coded: approved=green, denied=red, pending=yellow, expired=gray), risk level
- Mission ID, tool name, requested/responded timestamps
- Empty state: "No pending approvals"

**TelemetryPage (`src/pages/TelemetryPage.tsx`):**
- Filter by `mission_id` (URL search params, input + button)
- Clear filter button when active
- Events sorted newest-first (reverse chronological)
- Each event: type badge (indigo), mission ID, timestamp, source file, expandable JSON data
- Empty state: "No telemetry events" (with filter context if filtered)

### 3.9 — Task 9.9: Layout, Router, Sidebar, ErrorBoundary

**Router (`src/App.tsx`):**

| Route | Component | ErrorBoundary Label |
|-------|-----------|---------------------|
| `/` | `Navigate → /missions` | — |
| `/missions` | `MissionListPage` | "Missions panel error" |
| `/missions/:id` | `MissionDetailPage` | "Mission detail panel error" |
| `/health` | `HealthPage` | "Health panel error" |
| `/approvals` | `ApprovalsPage` | "Approvals panel error" |
| `/telemetry` | `TelemetryPage` | "Telemetry panel error" |
| `*` | `NotFoundPage` | — |

**Layout (`src/components/Layout.tsx`):**
- Full-height flex: sidebar (fixed 14rem) + header + scrollable content
- Header: "OpenClaw Mission Control" + green dot + "Polling 30s"
- Dark theme: `bg-gray-950 text-gray-100`

**Sidebar (`src/components/Sidebar.tsx`):**
- NavLink items: Missions 🎯, Health 💚, Approvals 🔐, Telemetry 📊
- Active route: `bg-gray-700/80 text-white`
- Inactive: `text-gray-400 hover:bg-gray-800`

**ErrorBoundary (`src/components/ErrorBoundary.tsx`) — D-084:**
- Class component (React error boundary requirement)
- `getDerivedStateFromError` + `componentDidCatch` (console.error)
- Fallback UI: red panel + configurable label + error message + "Retry" button
- Retry: `setState({ hasError: false })` → re-render children
- Per-panel: each route wrapped in its own ErrorBoundary — one panel crash does not affect others

**NotFoundPage (`src/pages/NotFoundPage.tsx`):**
- "404" + "Page not found" + "Go to Missions" button

---

## Section 4: Test Results

### 4.1 — Frontend Test Suite (18 tests)

| Test File | Tests | Description |
|-----------|-------|-------------|
| `DataQualityBadge.test.tsx` | 8 | 6 distinct state renders + 6-value enum count + tooltip detail |
| `usePolling.test.tsx` | 4 | Immediate fetch, interval polling, error resilience, manual refresh |
| `ErrorBoundary.test.tsx` | 3 | Normal render, error catch + fallback, retry reset |
| `client.test.tsx` | 3 | Typed response, 404 ApiError, network error handling |
| **Total** | **18** | **0 failures** |

### 4.2 — Build Verification

| Check | Result |
|-------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npm run build` | ✅ Production build (48 modules) |
| `npx vitest run` | ✅ 18/18 passed |
| Bundle: JS | 194.67 KB (gzip: 60.67 KB) |
| Bundle: CSS | 15.96 KB (gzip: 3.74 KB) |
| Bundle: HTML | 0.46 KB |

### 4.3 — Schema Parity Verification

```
Python schemas (agent/api/schemas.py):  22 classes
TypeScript types (src/types/api.ts):    22 exports
Match: ✅ 1:1

DataQualityStatus values: fresh, partial, stale, degraded, unknown, not_reached (6/6)
CapabilityStatus values: available, unavailable, unknown (3/3)
MissionState values: pending, planning, executing, gate_check, rework, approval_wait,
                     completed, failed, aborted, timed_out (10/10)
```

---

## Section 5: Sprint Checklist

| # | Criterion | Task | Status |
|---|----------|------|--------|
| 1 | Vite dev server `:3000` çalışıyor | 9.1 | PASS |
| 2 | API proxy çalışıyor (`/api` → `:8003`) | 9.1 | PASS |
| 3 | TS types `schemas.py` ile 1:1 eşleşir (22=22) | 9.2 | PASS |
| 4 | DataQualityStatus 6 state | 9.2 | PASS |
| 5 | CapabilityStatus tri-state | 9.2 | PASS |
| 6 | Polling 30s interval | 9.3 | PASS |
| 7 | Tab hidden → polling durur | 9.3 | PASS |
| 8 | Error → last data preserved | 9.3 | PASS |
| 9 | 6 DataQuality badge distinct render | 9.4 | PASS |
| 10 | FreshnessIndicator stale threshold | 9.4 | PASS |
| 11 | `sourcesMissing` explicit gösterim | 9.4 | PASS |
| 12 | Mission listesi render + click navigate | 9.5 | PASS |
| 13 | Empty state: "No missions found" | 9.5 | PASS |
| 14 | Loading state: spinner | 9.5 | PASS |
| 15 | Error state: message + retry | 9.5 | PASS |
| 16 | Mission detail header doğru | 9.6 | PASS |
| 17 | Stage timeline sıralı gösterim | 9.6 | PASS |
| 18 | Gate passed=yeşil, failed=kırmızı + findings | 9.6 | PASS |
| 19 | Deny forensics visible (hidden değil) | 9.6 | PASS |
| 20 | `agentUsed` her stage'de görünür | 9.6 | PASS |
| 21 | 404 mission → "Mission not found" | 9.6 | PASS |
| 22 | Health status büyük badge | 9.7 | PASS |
| 23 | Capability tri-state 3 farklı visual | 9.7 | PASS |
| 24 | Approvals read-only list | 9.8 | PASS |
| 25 | Telemetry filterable by mission_id | 9.8 | PASS |
| 26 | Telemetry newest-first | 9.8 | PASS |
| 27 | Router tüm sayfalar çalışıyor | 9.9 | PASS |
| 28 | Unknown route → 404 page | 9.9 | PASS |
| 29 | ErrorBoundary per-panel isolation | 9.9 | PASS |
| 30 | Polling indicator header'da | 9.9 | PASS |
| 31 | Sidebar aktif sayfa highlighted | 9.9 | PASS |
| 32 | 0 TypeScript error | 9.10 | PASS |
| 33 | Vitest 18/18 pass | 9.10 | PASS |
| 34 | Production build success | 9.10 | PASS |

---

## Section 6: Architecture

### Frontend Stack

```
Browser (:3000)
  ├── React 18 (SPA)
  ├── react-router-dom 6 (client-side routing)
  ├── Tailwind CSS 3 (utility-first styling)
  ├── TypeScript 5 (strict mode)
  └── Vite 6 (dev server + HMR + proxy + bundler)
        ↓ proxy /api/*
      FastAPI (:8003) — Sprint 8 backend
```

### Data Flow

```
usePolling(fetcher, 30s)
  → apiGet<T>('/api/v1/...')
    → Vite proxy → FastAPI :8003
      → MissionNormalizer → 5 sources
    ← JSON response (typed)
  → { data, error, loading, refresh, lastFetchedAt }
    → Page component
      → DataQualityBadge (6-state)
      → FreshnessIndicator (age + sources)
      → Domain UI (list, detail, timeline, etc.)
        ↳ ErrorBoundary (per-panel isolation)
```

### Component Tree

```
<BrowserRouter>
  <App>
    <Layout>
      <Sidebar />
      <header (polling indicator) />
      <Routes>
        <ErrorBoundary> <MissionListPage /> </ErrorBoundary>
        <ErrorBoundary> <MissionDetailPage>
          <StageTimeline />
          <StageCard />
        </MissionDetailPage> </ErrorBoundary>
        <ErrorBoundary> <HealthPage /> </ErrorBoundary>
        <ErrorBoundary> <ApprovalsPage /> </ErrorBoundary>
        <ErrorBoundary> <TelemetryPage /> </ErrorBoundary>
        <NotFoundPage />
      </Routes>
    </Layout>
  </App>
</BrowserRouter>
```

---

## Section 7: UI Principles Enforced

| Principle | Implementation | Where |
|-----------|----------------|-------|
| Unknown ≠ zero | `unknown` gray ?, `fresh` green ✓ — distinct color + icon | DataQualityBadge |
| Missing ≠ healthy | `sourcesMissing` shown with red dot | FreshnessIndicator |
| Silent absence forbidden | Empty states always have explicit message | All pages |
| Every block shows freshness | `FreshnessIndicator` on every page with data | All data pages |
| 6 DQ states distinct | 6 colors + 6 icons + 6 labels | DataQualityBadge |
| `not_reached` ≠ `unknown` | Dark gray — vs mid gray ? | DataQualityBadge |
| Stale visible | Red border when `freshnessMs > staleThresholdMs` | FreshnessIndicator |
| Deny forensics never hidden | Amber panel, always rendered when present | StageCard, MissionDetailPage |
| No fake live behavior | "Polling 30s" indicator in header | Layout header |

---

## Section 8: Frozen Decisions Applied

### D-081: Tailwind CSS (from SPRINT-9-TASK-BREAKDOWN)
Utility-first CSS. Applied across all components.

### D-082: Manual TypeScript Types
22 TS interfaces/enums manually mapped from 22 Pydantic schemas. No auto-generation — schema count manageable, FastAPI OpenAPI export untested.

### D-083: Global 30s Polling + Manual Refresh
Single `setInterval(30_000)` per active page. Manual "Refresh" button on every page. Page Visibility API: polling pauses when tab hidden.

### D-084: Per-Panel ErrorBoundary
Each route wrapped in `<ErrorBoundary>`. One panel crash doesn't affect others. Retry button resets boundary state.

---

## Section 9: Files Created

| File | Task | Purpose |
|------|------|---------|
| `frontend/package.json` | 9.1 | Dependencies + scripts |
| `frontend/vite.config.ts` | 9.1 | Dev server, proxy, vitest config |
| `frontend/tsconfig.json` | 9.1 | Strict TypeScript |
| `frontend/tailwind.config.js` | 9.1 | Tailwind content paths |
| `frontend/postcss.config.js` | 9.1 | PostCSS + Tailwind + Autoprefixer |
| `frontend/eslint.config.js` | 9.1 | ESLint + TS + React hooks |
| `frontend/index.html` | 9.1 | SPA entry point |
| `frontend/src/main.tsx` | 9.1 | React root + BrowserRouter |
| `frontend/src/index.css` | 9.1 | Tailwind directives |
| `frontend/src/vite-env.d.ts` | 9.1 | Vite type declarations |
| `frontend/src/test/setup.ts` | 9.1 | Vitest + jest-dom setup |
| `frontend/src/types/api.ts` | 9.2 | 22 TS types (1:1 from schemas.py) |
| `frontend/src/api/client.ts` | 9.3 | Typed API client (8 functions) |
| `frontend/src/hooks/usePolling.ts` | 9.3 | 30s polling hook |
| `frontend/src/components/DataQualityBadge.tsx` | 9.4 | 6-state quality badge |
| `frontend/src/components/FreshnessIndicator.tsx` | 9.4 | Freshness + sources |
| `frontend/src/components/MissionStateBadge.tsx` | 9.5 | FSM state badge (10 states) |
| `frontend/src/pages/MissionListPage.tsx` | 9.5 | Mission list |
| `frontend/src/pages/MissionDetailPage.tsx` | 9.6 | Mission detail |
| `frontend/src/components/StageTimeline.tsx` | 9.6 | Stage pipeline |
| `frontend/src/components/StageCard.tsx` | 9.6 | Expanded stage view |
| `frontend/src/pages/HealthPage.tsx` | 9.7 | Health + capabilities |
| `frontend/src/pages/ApprovalsPage.tsx` | 9.8 | Approval list |
| `frontend/src/pages/TelemetryPage.tsx` | 9.8 | Telemetry viewer |
| `frontend/src/App.tsx` | 9.9 | Router + layout |
| `frontend/src/components/Layout.tsx` | 9.9 | Sidebar + header |
| `frontend/src/components/Sidebar.tsx` | 9.9 | Navigation |
| `frontend/src/components/ErrorBoundary.tsx` | 9.9 | Per-panel error boundary |
| `frontend/src/pages/NotFoundPage.tsx` | 9.9 | 404 page |
| `frontend/src/__tests__/DataQualityBadge.test.tsx` | 9.10 | Badge render tests (8) |
| `frontend/src/__tests__/usePolling.test.tsx` | 9.10 | Polling hook tests (4) |
| `frontend/src/__tests__/ErrorBoundary.test.tsx` | 9.10 | Error boundary tests (3) |
| `frontend/src/__tests__/client.test.tsx` | 9.10 | API client tests (3) |
| `.gitignore` | 9.1 | Added `frontend/node_modules/`, `frontend/dist/` |

**Total:** 33 files created, 1 file modified.

---

## Section 10: Downstream Impact (Sprint 10)

| Sprint 9 Output | Sprint 10 Consumer |
|-----------------|-------------------|
| `usePolling` hook | Replace with `useSSE` hook (SSE replaces polling) |
| `client.ts` API functions | SSE event handling alongside REST |
| Polling indicator in header | Replace with "Live" / "Disconnected" indicator |
| Per-panel ErrorBoundary | SSE reconnect error handling |
| DataQualityBadge | Reused as-is |
| FreshnessIndicator | Real-time freshness from SSE events |

---

## Section 11: Known Limitations

| Limitation | Mitigation | Sprint |
|-----------|------------|--------|
| Node.js 14 system-wide — Vite 6 incompatible | Portable Node.js 20 at `C:\Users\AKCA\node20\` | — |
| No SSE — polling only (30s delay) | D-083 decision, SSE in Sprint 10 | 10 |
| No intervention (approve/deny from UI) | Read-only by design, intervention in Sprint 11 | 11 |
| No pagination on telemetry/missions | Frontend-side limit sufficient for current scale | 12 |
| `getStages()` / `getStage()` defined but unused | MissionDetail uses inline stages from `getMission()` response — no data loss | — |
| `/approvals/{id}` has no client function | Single-approval detail not needed in current UI; backlogged | 11 |

---

## Section 12: Evidence Bundle

### Evidence: Build

```
$ npx tsc --noEmit
(no output — 0 errors)

$ npm run build
vite v6.4.1 building for production...
✓ 48 modules transformed.
dist/index.html                   0.46 kB │ gzip:  0.31 kB
dist/assets/index-BDOgjO02.css   15.96 kB │ gzip:  3.74 kB
dist/assets/index-BwrzEq6y.js   194.67 kB │ gzip: 60.67 kB
✓ built in 2.47s
```

### Evidence: Tests

```
$ npx vitest run
 ✓ src/__tests__/client.test.tsx (3)
 ✓ src/__tests__/DataQualityBadge.test.tsx (8)
 ✓ src/__tests__/ErrorBoundary.test.tsx (3)
 ✓ src/__tests__/usePolling.test.tsx (4)

 Test Files  4 passed (4)
      Tests  18 passed (18)
   Duration  3.26s
```

### Evidence: Schema Parity

```
Python: grep "^class " agent/api/schemas.py | wc -l → 22
TS:     grep "^export" frontend/src/types/api.ts | wc -l → 22
Match: ✅
```

### Evidence: Lint

```
$ npm run lint
(exit code 0 — 0 errors, 0 warnings)
```

### Evidence: Sprint Doc Validator

```
$ python agent/tools/validate_sprint_docs.py --sprint 9 --sprint-date 2026-03-25

  [PASS] docs/ai/STATE.md — Fresh
  [PASS] docs/ai/STATE.md — All required sections present
  [PASS] docs/ai/NEXT.md — Fresh
  [PASS] SESSION-HANDOFF.md — Fresh
  [PASS] SESSION-HANDOFF.md — Handoff sections present
  [PASS] config/capabilities.json — autoGenerated: true, 5/5 capabilities available
  [PASS] SPRINT-9-TASK-BREAKDOWN.md — All checkboxes completed
  [PASS] Test count — 170 tests (>= 129)

  Result: All checks passed — sprint ready to close
```

### Evidence: Endpoint Inventory

| Backend Endpoint | Client Function | UI Consumer Page | Status |
|-----------------|----------------|-----------------|--------|
| `GET /api/v1/missions` | `getMissions()` | MissionListPage | ✅ Active |
| `GET /api/v1/missions/{id}` | `getMission(id)` | MissionDetailPage | ✅ Active |
| `GET /api/v1/missions/{id}/stages` | `getStages(missionId)` | — | ⚠ Defined, unused (inline stages) |
| `GET /api/v1/missions/{id}/stages/{idx}` | `getStage(missionId, idx)` | — | ⚠ Defined, unused (inline stages) |
| `GET /api/v1/approvals` | `getApprovals()` | ApprovalsPage | ✅ Active |
| `GET /api/v1/approvals/{id}` | — | — | ⚠ No client function (backlogged) |
| `GET /api/v1/telemetry` | `getTelemetry(missionId?)` | TelemetryPage | ✅ Active |
| `GET /api/v1/health` | `getHealth()` | HealthPage | ✅ Active |
| `GET /api/v1/capabilities` | `getCapabilities()` | HealthPage | ✅ Active |
| `GET /api/v1/missions/{id}/stages/{idx}/gate` | — | — | ⚠ No client function (gate data inline in stages) |

**Summary:** 8 client functions / 10 backend endpoints. 6 actively consumed by pages. 2 defined for future use. 2 endpoints have no client function (data available inline).

### Evidence: Code-Level Verification (14-point)

| # | Check | Result |
|---|-------|--------|
| 1 | /missions page renders MissionListPage | PASS |
| 2 | MissionListPage calls getMissions via usePolling | PASS |
| 3 | /missions/:id renders MissionDetailPage | PASS |
| 4 | MissionDetailPage shows gate results via StageCard | PASS |
| 5 | StageCard shows deny forensics (policyDenies) | PASS |
| 6 | StageCard shows agentUsed | PASS |
| 7 | /health renders HealthPage | PASS |
| 8 | HealthPage renders CapabilityStatus tri-state | PASS |
| 9 | /approvals renders ApprovalsPage | PASS |
| 10 | /telemetry renders TelemetryPage | PASS |
| 11 | TelemetryPage has mission_id filter | PASS |
| 12 | Layout header shows "Polling 30s" indicator | PASS |
| 13 | DataQualityBadge handles all 6 states distinctly | PASS |
| 14 | ErrorBoundary wraps each route (5 route wraps) | PASS |

---

*Phase 5A-2 — Sprint 9 Report — OpenClaw Mission Control Center React UI*
*Date: 2026-03-25*
*Operator: AKCA | Agent: Claude (Copilot)*
*Decisions Applied: D-067, D-079, D-081, D-082, D-083, D-084*
*GPT Cross-Review: Closure handoff received and executed 2026-03-25*
*Validator: 8/8 PASS — sprint ready to close*
