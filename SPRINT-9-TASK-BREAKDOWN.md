# Sprint 9 — Phase 5A-2: React Read-Only UI — Task Breakdown

**Date:** 2026-03-25
**Status:** COMPLETE (10/10 tasks, 18 tests, 0 failures)
**Author:** Operator (AKCA) + Claude (Copilot)
**Prerequisite:** Sprint 8 CLOSED (evidence: d20b05a, 4/4 contradiction resolved)
**Risk Level:** MEDIUM — UI sprint, backend stable
**Report:** `docs/phase-reports/PHASE-5A2-SPRINT-9-REACT-READ-ONLY-UI.md`

---

## Section 1: Sprint Hedefi

Mission Control Center'ın read-only React dashboard'unu teslim et. Sprint 8 backend API'sine bağlanır. Polling-based (SSE Sprint 10). Operatör gözlem paneli — müdahale yok (Sprint 11).

**Definition of Done:**
- React app `:3000`'de serve ediliyor, API `:8003`'e proxy yapıyor
- Tüm 10 endpoint'ten veri çekiliyor ve render ediliyor
- DataQuality 6-state distinct rendering
- Freshness indicator her panelde
- Unknown ≠ zero, missing ≠ healthy — UI'da açıkça ayrı
- Stale/degraded/error visible, silent absence yok
- 0 TypeScript error, 0 lint error
- GPT cross-review (sprint ortası) tamamlanmış

---

## Section 2: Frozen Decisions (Sprint 9)

### D-081: CSS Framework — Tailwind CSS

**Phase:** 5A-2 | **Status:** Frozen

Tailwind CSS utility-first. Sebep: hızlı prototipleme, class-based theming, purge ile küçük bundle. Alternatifler (CSS Modules, styled-components) daha yavaş iteration süresi.

### D-082: Type Generation — Manual TypeScript Types from Frozen Schemas

**Phase:** 5A-2 | **Status:** Frozen

`schemas.py` FROZEN (D-067, additive-only). `openapi-typescript` yerine manual TS interface'ler tercih edildi. Sebep: FastAPI'nin OpenAPI export'u henüz test edilmedi, schema sayısı yönetilebilir (19 class). Sprint 12'de otomatik generation değerlendirilecek.

### D-083: Polling Strategy — Global 30s + Manual Refresh

**Phase:** 5A-2 | **Status:** Frozen

Tek global `setInterval(30_000)` tüm aktif sayfanın endpoint'lerini çeker. Manuel "Refresh" butonu her panelde. Per-panel polling yok (karmaşıklık/server load). SSE Sprint 10'da polling'i replace edecek.

### D-084: Error Boundary — Per-Panel

**Phase:** 5A-2 | **Status:** Frozen

Her panel kendi ErrorBoundary'sine sahip. Bir paneldeki hata diğerlerini etkilemez. Circuit breaker alignment: backend'de source-level isolation, frontend'de panel-level isolation.

---

## Section 3: Bağımlılık Grafiği

```
9.1 (Vite scaffold)
  ↓
9.2 (TS types from schemas.py)
  ↓
9.3 (API client + polling hook)
  ├──→ 9.4 (DataQualityBadge + FreshnessIndicator)
  │     ↓
  ├──→ 9.5 (MissionList page)
  │     ↓
  ├──→ 9.6 (MissionDetail + StageDetail)
  │     ↓
  ├──→ 9.7 (HealthDashboard + Capabilities)
  │     ↓
  ├──→ 9.8 (ApprovalList + TelemetryView)
  │     ↓
  └──→ 9.9 (ErrorBoundary + Layout + Router)
        ↓
      9.10 (E2E smoke + GPT review)
```

**Önerilen sıra:** 9.1 → 9.2 → 9.3 → 9.4 → 9.5 → 9.6 → 9.7 → 9.8 → 9.9 → 9.10

**GPT review checkpoint:** 9.6 sonrası (en riskli: normalizer data → UI rendering doğruluğu)

---

## Section 4: Task Kartları

---

### Task 9.1 — Vite + React + TypeScript Scaffold

| Alan | Değer |
|------|-------|
| ID | 9.1 |
| Dosya | `frontend/` (yeni dizin) |
| Efor | S |
| Bağımlılık | Sprint 8 CLOSED |
| Bağımlı | 9.2, 9.3, tüm diğer task'lar |

#### Scope

- `npm create vite@latest frontend -- --template react-ts`
- Tailwind CSS kurulumu (D-081)
- Vite proxy config: `/api` → `http://127.0.0.1:8003`
- ESLint + Prettier config
- `tsconfig.json` strict mode
- `.gitignore` güncellemesi (`frontend/node_modules/`, `frontend/dist/`)

#### Kapsam Dışı

- Component geliştirme (sonraki task'lar)
- Test framework kurulumu (9.10'da)

#### Kabul Kriterleri

1. `cd frontend && npm run dev` → `:3000`'de boş React app açılır
2. `fetch('/api/v1/health')` → proxy üzerinden `:8003`'ten response gelir
3. Tailwind class'ları çalışır (`className="text-red-500"` kırmızı render eder)
4. `npm run build` → `dist/` üretir, 0 error
5. `npx tsc --noEmit` → 0 error

#### Verification

```bash
cd frontend && npm install && npm run dev &
sleep 3
curl -s http://localhost:3000/api/v1/health | python -m json.tool
# Beklenen: Sprint 8 health response (proxy çalışıyor)
```

---

### Task 9.2 — TypeScript Type Definitions

| Alan | Değer |
|------|-------|
| ID | 9.2 |
| Dosya | `frontend/src/types/api.ts` |
| Efor | M |
| Bağımlılık | 9.1 |
| Bağımlı | 9.3, 9.4, 9.5, 9.6, 9.7, 9.8 |

#### Scope

`agent/api/schemas.py`'daki 19 frozen Pydantic schema'yı 1:1 TypeScript interface'e çevir.

```
DataQualityStatus (enum) → 6 state: fresh, partial, stale, degraded, unknown, not_reached
DataQuality
SourceInfo
FreshnessInfo
ResponseMeta
Finding
GateResultDetail
DenyForensics
StageDetail
MissionSummary
MissionListItem
ApprovalEntry
TelemetryEntry
HealthResponse / ComponentHealth
CapabilityEntry / CapabilityStatus (tri-state enum)
APIError
Wrapper types: MissionListResponse, MissionDetailResponse, StageListResponse,
               ApprovalListResponse, TelemetryListResponse, HealthApiResponse,
               CapabilityListResponse
```

#### Kabul Kriterleri

1. Her Pydantic schema'nın birebir TS interface karşılığı var
2. `DataQualityStatus` enum 6 değer içerir — `known_zero` KULLANILMAZ
3. `CapabilityStatus` tri-state enum: `available`, `unavailable`, `unknown`
4. Wrapper response type'lar `data` + `meta: ResponseMeta` pattern'ini takip eder
5. `npx tsc --noEmit` → 0 error

#### Validation

```bash
# schemas.py'daki class sayısı ile api.ts'deki interface sayısı eşleşmeli
grep "^class " agent/api/schemas.py | wc -l
grep "^export interface\|^export enum\|^export type" frontend/src/types/api.ts | wc -l
```

---

### Task 9.3 — API Client + Polling Hook

| Alan | Değer |
|------|-------|
| ID | 9.3 |
| Dosya | `frontend/src/api/client.ts`, `frontend/src/hooks/usePolling.ts` |
| Efor | M |
| Bağımlılık | 9.2 |
| Bağımlı | 9.5, 9.6, 9.7, 9.8 |

#### Scope

**API Client (`client.ts`):**
- Typed fetch wrapper: `apiGet<T>(path: string): Promise<T>`
- Error handling: network error → throw, HTTP 4xx/5xx → throw with status + body
- Base URL: `/api/v1` (Vite proxy handles)
- Her endpoint için named function: `getMissions()`, `getMission(id)`, `getStages(id)`, `getStage(id, idx)`, `getApprovals()`, `getTelemetry(missionId?)`, `getHealth()`, `getCapabilities()`

**Polling Hook (`usePolling.ts`):**
- `usePolling<T>(fetcher: () => Promise<T>, intervalMs: number): { data: T | null, error: Error | null, loading: boolean, refresh: () => void, lastFetchedAt: Date | null }`
- D-083: default interval 30_000ms
- `refresh()` → manual trigger
- Tab hidden → polling durur (Page Visibility API)
- Component unmount → cleanup

#### Kabul Kriterleri

1. `usePolling(getHealth, 30_000)` → 30 saniyede bir health data gelir
2. Tab hidden olunca polling durur, visible olunca devam eder
3. Network error → `error` state set, `data` korunur (son başarılı)
4. `refresh()` → anında yeni fetch
5. `lastFetchedAt` → her başarılı fetch sonrası güncellenir

#### Kapsam Dışı

- SSE (Sprint 10)
- Cache invalidation (Sprint 10 SSE ile replace)
- Retry logic (polling zaten retry gibi çalışıyor)

---

### Task 9.4 — DataQualityBadge + FreshnessIndicator

| Alan | Değer |
|------|-------|
| ID | 9.4 |
| Dosya | `frontend/src/components/DataQualityBadge.tsx`, `frontend/src/components/FreshnessIndicator.tsx` |
| Efor | M |
| Bağımlılık | 9.2 |
| Bağımlı | 9.5, 9.6, 9.7, 9.8 |

#### Scope

**DataQualityBadge:**
- 6 distinct visual state (D-079):

| State | Renk | İkon | Label |
|-------|------|------|-------|
| `fresh` | Yeşil | ✓ | Fresh |
| `partial` | Sarı-yeşil | ◐ | Partial |
| `stale` | Turuncu | ⏳ | Stale |
| `degraded` | Kırmızı | ⚠ | Degraded |
| `unknown` | Gri | ? | Unknown |
| `not_reached` | Koyu gri | — | Not Reached |

- Tooltip: `quality.detail` + `quality.assessedAt`

**FreshnessIndicator:**
- `freshnessMs` → human-readable: "2s ago", "45s ago", "3m ago"
- `staleThresholdMs` karşılaştırma: `freshnessMs > staleThresholdMs` → kırmızı indicator
- Source listesi: `sourcesUsed` (yeşil), `sourcesMissing` (kırmızı)
- `lastFetchedAt` (polling hook'tan): "Polled 5s ago"

#### Kabul Kriterleri

1. 6 DataQuality state → 6 farklı visual (renk + ikon + label)
2. `unknown` ve `not_reached` kesinlikle farklı render (ikisi de gri tonunda ama label + ikon farklı)
3. `fresh` ve `known_zero` AYNI DEĞİL — `known_zero` type'da yok, sadece `fresh`
4. Stale threshold aşımı → kırmızı border/background
5. `sourcesMissing` boş değilse explicit olarak gösterilir

#### UI Prensibi Kontrolü

- [x] Unknown ≠ zero
- [x] Missing ≠ healthy
- [x] Silent absence yok
- [x] Freshness her panelde

---

### Task 9.5 — MissionList Page

| Alan | Değer |
|------|-------|
| ID | 9.5 |
| Dosya | `frontend/src/pages/MissionListPage.tsx` |
| Efor | M |
| Bağımlılık | 9.3, 9.4 |
| Bağımlı | 9.9 |

#### Scope

- `GET /api/v1/missions` → `MissionListResponse` render
- Her mission item: id, status badge, complexity, createdAt, updatedAt
- Status badge: FSM state'e göre renk (pending, planning, executing, review, completed, failed, cancelled...)
- Click → `/missions/{id}` (9.6)
- DataQualityBadge + FreshnessIndicator (response-level)
- Empty state: "No missions found" (explicit, not blank)
- Loading state: skeleton/spinner
- Error state: error message + retry button

#### Kabul Kriterleri

1. Missions listeleniyor, her biri clickable
2. Status badge mission state'e göre renkli
3. Boş liste → "No missions found" mesajı (silent absence yok)
4. Loading → spinner/skeleton görünür
5. API error → error mesajı + "Retry" butonu
6. DataQualityBadge response-level quality gösterir

---

### Task 9.6 — MissionDetail + StageDetail

| Alan | Değer |
|------|-------|
| ID | 9.6 |
| Dosya | `frontend/src/pages/MissionDetailPage.tsx`, `frontend/src/components/StageTimeline.tsx`, `frontend/src/components/StageCard.tsx` |
| Efor | L |
| Bağımlılık | 9.3, 9.4 |
| Bağımlı | 9.9 |

#### Scope

**MissionDetailPage:**
- `GET /api/v1/missions/{id}` → header: id, status, complexity, createdAt, cost
- Stage pipeline visualization: horizontal timeline veya vertical card list
- Per-stage: role, status, agentUsed, gate results
- DataQuality + Freshness (per-response)

**StageTimeline:**
- Stages sıralı gösterim (stage index sırasına göre)
- Her stage: role icon/label, status badge (passed/failed/running/pending)
- Gate results: passed → yeşil check, failed → kırmızı X + finding count
- Active stage highlighted

**StageCard (expanded view):**
- `GET /api/v1/missions/{id}/stages/{idx}` → detay
- Gate findings listesi
- Deny forensics (varsa): gate, recommendation, blocking_rules
- agentUsed (model tracking)
- Stage-level freshness

#### Kabul Kriterleri

1. Mission header doğru render (id, status, complexity)
2. Stage timeline tüm stage'leri sıralı gösterir
3. Gate passed → yeşil, failed → kırmızı + findings
4. Deny forensics varsa explicit gösterilir (hidden değil)
5. Stage'e tıklayınca detay açılır (expanded card veya route)
6. 404 mission → "Mission not found" error page
7. `agentUsed` her stage'de görünür (hangi model kullanıldı)

#### Risk

Bu sprint'in en büyük task'ı. Normalizer'dan gelen karmaşık veri yapısını UI'a doğru map etmek kritik. **GPT review bu task sonrası yapılacak.**

---

### Task 9.7 — HealthDashboard + Capabilities

| Alan | Değer |
|------|-------|
| ID | 9.7 |
| Dosya | `frontend/src/pages/HealthPage.tsx` |
| Efor | M |
| Bağımlılık | 9.3, 9.4 |
| Bağımlı | 9.9 |

#### Scope

**Health paneli:**
- `GET /api/v1/health` → `HealthApiResponse`
- Overall status: ok/degraded/error → büyük badge
- ComponentHealth listesi: her component name + status + detail
- DataQuality + Freshness

**Capabilities paneli:**
- `GET /api/v1/capabilities` → `CapabilityListResponse`
- Her capability: name + tri-state status badge
  - `available` → yeşil
  - `unavailable` → kırmızı
  - `unknown` → gri (distinct from unavailable!)

#### Kabul Kriterleri

1. Health status büyük ve net görünür (ok=yeşil, degraded=turuncu, error=kırmızı)
2. Component listesi tüm bileşenleri gösterir
3. Capability tri-state: 3 farklı visual (available ≠ unavailable ≠ unknown)
4. `unknown` capability "bilinmiyor" olarak gösterilir, "yok" olarak değil

---

### Task 9.8 — ApprovalList + TelemetryView

| Alan | Değer |
|------|-------|
| ID | 9.8 |
| Dosya | `frontend/src/pages/ApprovalsPage.tsx`, `frontend/src/pages/TelemetryPage.tsx` |
| Efor | M |
| Bağımlılık | 9.3, 9.4 |
| Bağımlı | 9.9 |

#### Scope

**ApprovalList:**
- `GET /api/v1/approvals` → `ApprovalListResponse`
- Her approval: id, missionId, status, requestedAt
- Read-only (mutation Sprint 11)
- Empty state: "No pending approvals"

**TelemetryView:**
- `GET /api/v1/telemetry` → `TelemetryListResponse`
- Filter: mission_id (URL param veya dropdown)
- Her event: type, timestamp, sourceFile, data summary
- Reverse chronological (newest first)
- Pagination veya virtual scroll (telemetry büyüyebilir)

#### Kabul Kriterleri

1. Approval listesi render ediliyor, read-only
2. Telemetry events listeleniyor, mission_id ile filtrelenebilir
3. Empty states explicit ("No approvals", "No telemetry events")
4. Telemetry newest-first sıralı

---

### Task 9.9 — Layout, Router, ErrorBoundary

| Alan | Değer |
|------|-------|
| ID | 9.9 |
| Dosya | `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/components/ErrorBoundary.tsx`, `frontend/src/components/Sidebar.tsx` |
| Efor | M |
| Bağımlılık | 9.5, 9.6, 9.7, 9.8 |
| Bağımlı | 9.10 |

#### Scope

**Router (react-router-dom):**

| Route | Component | Page |
|-------|-----------|------|
| `/` | Redirect → `/missions` | — |
| `/missions` | MissionListPage | 9.5 |
| `/missions/:id` | MissionDetailPage | 9.6 |
| `/health` | HealthPage | 9.7 |
| `/approvals` | ApprovalsPage | 9.8 |
| `/telemetry` | TelemetryPage | 9.8 |
| `*` | NotFoundPage | 404 |

**Layout:**
- Sidebar navigation: Missions, Health, Approvals, Telemetry
- Active route highlighted
- Header: "OpenClaw Mission Control" + polling status indicator
- Polling indicator: "Last polled Xs ago" + yeşil/kırmızı dot

**ErrorBoundary (D-084):**
- Per-panel error boundary wrapping
- Caught error → "This panel encountered an error" + "Retry" button
- Diğer panel'ler çalışmaya devam eder
- Error logging to console (prod'da telemetry'ye gönderilebilir)

#### Kabul Kriterleri

1. Tüm route'lar çalışıyor, navigation seamless
2. Unknown route → 404 page
3. Bir panel crash olursa diğerleri çalışmaya devam eder
4. Polling indicator header'da görünür
5. Sidebar'da aktif sayfa highlighted

---

### Task 9.10 — Smoke Test + GPT Cross-Review

| Alan | Değer |
|------|-------|
| ID | 9.10 |
| Dosya | `frontend/src/__tests__/`, `docs/ai/SPRINT-9-GPT-REVIEW.md` |
| Efor | M |
| Bağımlılık | 9.9 |
| Bağımlı | — |

#### Scope

**Smoke Tests:**
- Component render tests (React Testing Library / Vitest)
- API client unit tests (msw mock)
- Polling hook test (timer mock)
- DataQualityBadge: 6 state → 6 distinct render
- ErrorBoundary: error caught, other panels survive

**GPT Cross-Review:**
- Tüm component'lerin DataQuality/Freshness doğru kullanımı
- UI prensip kontrolü (unknown≠zero, silent absence yok)
- Type safety: TS types ile Pydantic schema 1:1 eşleşme
- Accessibility basics (ARIA labels, keyboard nav)

**Live Browser Verification:**
- Backend `:8003` çalışırken frontend `:3000` açılır
- Tüm sayfalar gezilir, real data render edilir
- Network tab'da 30s polling görülür
- Stale data → FreshnessIndicator kırmızıya döner

#### Kabul Kriterleri

1. Vitest: tüm testler pass, 0 failure
2. `npx tsc --noEmit` → 0 error
3. `npm run lint` → 0 error
4. GPT review: 0 blocking finding
5. Live verification: tüm sayfalar real data ile çalışır
6. `npm run build` → production build başarılı

---

## Section 5: Sprint Exit Criteria

| # | Criterion | Task | Verification |
|---|----------|------|--------------|
| 1 | Vite dev server `:3000`'de çalışıyor | 9.1 | `curl localhost:3000` |
| 2 | API proxy çalışıyor | 9.1 | `curl localhost:3000/api/v1/health` |
| 3 | TS types schema.py ile 1:1 eşleşir | 9.2 | Class count match |
| 4 | DataQualityStatus 6 state (fresh, partial, stale, degraded, unknown, not_reached) | 9.2 | grep `api.ts` |
| 5 | Polling 30s interval çalışıyor | 9.3 | Network tab gözlem |
| 6 | Tab hidden → polling durur | 9.3 | Page Visibility test |
| 7 | 6 DataQuality badge distinct render | 9.4 | Visual inspection |
| 8 | FreshnessIndicator stale threshold gösterir | 9.4 | Stale data ile test |
| 9 | Mission listesi render | 9.5 | Browser |
| 10 | Mission detail + stage timeline | 9.6 | Browser |
| 11 | Gate results + deny forensics visible | 9.6 | Browser |
| 12 | Health status + components | 9.7 | Browser |
| 13 | Capability tri-state render | 9.7 | Browser |
| 14 | Approvals read-only list | 9.8 | Browser |
| 15 | Telemetry filterable | 9.8 | Browser |
| 16 | Router tüm sayfalar | 9.9 | Navigation test |
| 17 | ErrorBoundary per-panel isolation | 9.9 | Error injection test |
| 18 | 0 TypeScript error | 9.10 | `npx tsc --noEmit` |
| 19 | 0 lint error | 9.10 | `npm run lint` |
| 20 | Vitest all pass | 9.10 | `npx vitest run` |
| 21 | GPT review 0 blocking | 9.10 | Review doc |
| 22 | Production build success | 9.10 | `npm run build` |
| 23 | `validate_sprint_docs.py --sprint 9` 0 FAIL | 9.10 | Validator |

---

## Section 6: Files Created

| File | Task | Purpose |
|------|------|---------|
| `frontend/package.json` | 9.1 | React + Vite + Tailwind deps |
| `frontend/vite.config.ts` | 9.1 | API proxy config |
| `frontend/tailwind.config.js` | 9.1 | Tailwind setup |
| `frontend/tsconfig.json` | 9.1 | Strict TS |
| `frontend/src/types/api.ts` | 9.2 | 19+ TS interfaces from schemas.py |
| `frontend/src/api/client.ts` | 9.3 | Typed API client |
| `frontend/src/hooks/usePolling.ts` | 9.3 | 30s polling hook |
| `frontend/src/components/DataQualityBadge.tsx` | 9.4 | 6-state badge |
| `frontend/src/components/FreshnessIndicator.tsx` | 9.4 | Freshness + sources |
| `frontend/src/pages/MissionListPage.tsx` | 9.5 | Mission list |
| `frontend/src/pages/MissionDetailPage.tsx` | 9.6 | Mission detail + stages |
| `frontend/src/components/StageTimeline.tsx` | 9.6 | Stage pipeline viz |
| `frontend/src/components/StageCard.tsx` | 9.6 | Expanded stage view |
| `frontend/src/pages/HealthPage.tsx` | 9.7 | Health + capabilities |
| `frontend/src/pages/ApprovalsPage.tsx` | 9.8 | Approval list |
| `frontend/src/pages/TelemetryPage.tsx` | 9.8 | Telemetry viewer |
| `frontend/src/App.tsx` | 9.9 | Router + layout |
| `frontend/src/components/Layout.tsx` | 9.9 | Sidebar + header |
| `frontend/src/components/ErrorBoundary.tsx` | 9.9 | Per-panel error boundary |
| `frontend/src/components/Sidebar.tsx` | 9.9 | Navigation |
| `frontend/src/__tests__/*.test.tsx` | 9.10 | Component + hook tests |
| `docs/ai/SPRINT-9-TASK-BREAKDOWN.md` | — | Bu dosya |

---

## Section 7: Riskler ve Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Schema drift (api.ts ↔ schemas.py) | HIGH | LOW (FROZEN) | D-067 additive-only. Manual diff check in 9.2 |
| Normalizer data complexity → UI mapping hata | MEDIUM | MEDIUM | GPT review 9.6 sonrası |
| Stale data visual distinction zayıf | HIGH | MEDIUM | 6-state distinct render forced in 9.4 acceptance criteria |
| Large telemetry response (no pagination backend) | MEDIUM | HIGH | Frontend-side virtual scroll / limit |
| CORS issue dev server → API | LOW | LOW | Vite proxy bypass |

---

## Section 8: Sprint 10 Downstream Impact

| Sprint 9 Output | Sprint 10 Consumer |
|-----------------|-------------------|
| `usePolling` hook | Replace with `useSSE` hook |
| `client.ts` API functions | SSE event handling alongside REST |
| Polling indicator in header | Replace with "Live" / "Disconnected" indicator |
| Per-panel ErrorBoundary | SSE reconnect error handling |

---

*Sprint 9 Task Breakdown — OpenClaw Mission Control Center React UI*
*Date: 2026-03-25*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Decisions Frozen: D-081 (Tailwind), D-082 (Manual TS types), D-083 (Global 30s polling), D-084 (Per-panel ErrorBoundary)*
