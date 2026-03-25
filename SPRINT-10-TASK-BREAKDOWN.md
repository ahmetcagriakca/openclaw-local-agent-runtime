# Sprint 10 — Phase 5B: SSE Live Updates — Task Breakdown

**Date:** 2026-03-25
**Status:** COMPLETE
**Author:** Operator (AKCA) + Claude Opus 4.6
**Prerequisite:** Sprint 9 CLOSED (COMPLETE — 34/34 checklist, 18/18 test, evidence bundle mevcut)
**Risk Level:** MEDIUM-HIGH — backend+frontend değişiklik, real-time complexity
**Estimated Duration:** 3-5 gün

---

## Section 1: Sprint Hedefi

Dashboard'u polling-based'den SSE push-based'e geçir. Dosya değişiklikleri backend'de algılanır, SSE stream ile frontend'e push edilir. Polling fallback korunur. "Live" indicator gerçek bağlantı durumunu yansıtır — fake live yasak.

**Definition of Done:**
- Backend SSE endpoint: `GET /api/v1/events/stream`
- File watcher: mission/state/summary/telemetry/capabilities dosya değişikliklerini algılıyor
- Frontend `useSSE` hook: `usePolling`'i replace ediyor (fallback preserved)
- "Live" / "Reconnecting" / "Polling" indicator header'da
- Reconnect: otomatik, exponential backoff
- Multi-tab: birden fazla bağlantı destekleniyor
- Event debouncing: rapid file changes → tek event
- 0 TypeScript error, 0 lint error
- Backend test suite regression: 170+ test, 0 failure
- Frontend test: SSE hook + indicator tests
- GPT cross-review tamamlanmış

---

## Section 2: Frozen Decisions (Sprint 10)

### D-085: File Watcher — Polling-based (cross-platform)

**Phase:** 5B | **Status:** Frozen

`watchfiles` (Python) veya manual mtime polling (1s interval) kullanılacak. `inotify` Linux-only — WSL2'de çalışsa da Windows FS üzerindeki dosyalar için güvenilmez. Cross-platform polling daha güvenli.

**Trade-off:** inotify daha hızlı ama platform-bağımlı. Polling 1s delay ekler ama her yerde çalışır. 1s delay kabul edilebilir — mevcut polling 30s'ydi.

### D-086: SSE Event Granularity — Per-Entity Change

**Phase:** 5B | **Status:** Frozen

Her event bir entity değişikliğini temsil eder (`mission_updated`, `health_changed`, `telemetry_new`). Per-field change tracking yok — karmaşıklık/fayda oranı düşük. Frontend entity-level invalidation yapacak.

### D-087: SSE Auth — Localhost-only (D-070 extension)

**Phase:** 5B | **Status:** Frozen

SSE endpoint D-070 localhost security'ye tabi. Ek token yok. Sebep: `:8003` zaten `127.0.0.1` bind + Host validation. Browser `:3000`'den Vite proxy üzerinden bağlanıyor.

### D-088: SSE Reconnect — Exponential Backoff + Polling Fallback

**Phase:** 5B | **Status:** Frozen

Bağlantı kesilirse: 1s → 2s → 4s → 8s → 16s → max 30s backoff ile reconnect. 3 ardışık başarısız reconnect → polling fallback (30s, mevcut `usePolling` hook). SSE tekrar bağlanınca polling durur.

---

## Section 3: Event Tipleri

| Event Type | Trigger | Data | Frontend Action |
|-----------|---------|------|-----------------|
| `mission_updated` | Mission/state/summary file mtime changed | `{ missionId, updatedAt }` | Invalidate mission detail + list |
| `mission_list_changed` | New mission dir created veya mission count changed | `{ count, updatedAt }` | Refetch mission list |
| `health_changed` | Health-related file changed | `{ updatedAt }` | Refetch health |
| `telemetry_new` | policy-telemetry.jsonl mtime changed | `{ updatedAt }` | Refetch telemetry |
| `capability_changed` | capabilities.json mtime changed | `{ updatedAt }` | Refetch capabilities |
| `approval_changed` | Approval store file changed | `{ updatedAt }` | Refetch approvals |
| `heartbeat` | Her 30s (connection alive proof) | `{ serverTime }` | Update "Live" indicator |
| `connected` | İlk bağlantı | `{ serverTime, version }` | Set "Live" state |

**D-086 uyumu:** Tüm event'ler entity-level. Frontend ilgili `apiGet()` fonksiyonunu çağırarak güncel veriyi alır — SSE event data değil, invalidation signal taşır.

---

## Section 4: Bağımlılık Grafiği

```
10.1 (watchfiles + file watcher)
  ↓
10.2 (SSE manager + event bus)
  ↓
10.3 (SSE endpoint + FastAPI integration)
  ↓
10.4 (useSSE hook — frontend)
  ↓
10.5 (Live/Reconnecting/Polling indicator)
  ↓
10.6 (Page integration — usePolling → useSSE migration)
  ↓
10.7 (Debouncing + multi-tab)
  ↓
10.8 (Test suite + GPT review)
```

**Önerilen sıra:** 10.1 → 10.2 → 10.3 → 10.4 → 10.5 → 10.6 → 10.7 → 10.8

**GPT review checkpoint:** 10.3 sonrası (backend SSE contract doğrulaması)

---

## Section 5: Task Kartları

---

### Task 10.1 — File Watcher Service

| Alan | Değer |
|------|-------|
| ID | 10.1 |
| Dosya | `agent/api/file_watcher.py` |
| Efor | M |
| Bağımlılık | Sprint 9 CLOSED |
| Bağımlı | 10.2 |

#### Scope

- `FileWatcher` class: belirtilen dizin/dosyaları mtime polling ile izler
- Konfigürasyon:

| Watch Target | Path Pattern | Event Type |
|-------------|-------------|------------|
| Mission dirs | `logs/missions/*/` | `mission_updated` |
| Mission list | `logs/missions/` (dir count) | `mission_list_changed` |
| Telemetry | `logs/policy-telemetry.jsonl` | `telemetry_new` |
| Capabilities | `config/capabilities.json` | `capability_changed` |
| Health | `logs/services.json` | `health_changed` |
| Approvals | Approval store path | `approval_changed` |

- Poll interval: 1s (D-085)
- mtime cache: `{path: last_mtime}` dict — değişiklik = mtime farklı
- Mission-level: her mission dir'ın içindeki `*-state.json`, `mission-*.json`, `*-summary.json` dosyalarının max mtime'ı → mission-level event
- Thread-safe: `asyncio.Queue` ile event'leri SSE manager'a iletir
- Graceful shutdown: lifespan event'te stop

#### Kapsam Dışı

- inotify / fsevents (D-085: cross-platform polling)
- Dosya içeriği parse etme (sadece mtime kontrol)
- Event dedup (10.7'de)

#### Kabul Kriterleri

1. `FileWatcher` başlatılıyor, 1s interval'le dosyaları tarıyor
2. Dosya mtime değişince event üretiyor
3. Yeni mission dir oluşunca `mission_list_changed` event
4. Dosya silinse crash olmuyor (graceful skip)
5. `asyncio.Queue`'ya event push ediyor
6. Stop çağrısıyla temiz kapanıyor

#### Verification

```bash
# Unit test: mock filesystem + mtime change → event produced
pytest tests/test_file_watcher.py -v
```

---

### Task 10.2 — SSE Event Manager

| Alan | Değer |
|------|-------|
| ID | 10.2 |
| Dosya | `agent/api/sse_manager.py` |
| Efor | M |
| Bağımlılık | 10.1 |
| Bağımlı | 10.3 |

#### Scope

- `SSEManager` class: event'leri connected client'lara dağıtır
- Client registry: `set[asyncio.Queue]` — her SSE bağlantısı bir queue
- `subscribe() → asyncio.Queue`: yeni client ekler
- `unsubscribe(queue)`: client çıkarır
- `broadcast(event)`: tüm client queue'larına push
- Event format (SSE spec):
  ```
  event: mission_updated
  data: {"missionId": "abc-123", "updatedAt": "2026-03-25T12:00:00Z"}
  id: evt-1234567890
  
  ```
- Heartbeat: 30s interval, `event: heartbeat` — connection alive proof
- Event ID: monotonic counter (reconnect için `Last-Event-ID` support)
- Max clients: 10 (abuse prevention)

#### Kabul Kriterleri

1. `subscribe()` → queue döner
2. `broadcast(event)` → tüm subscriber queue'larına yazılır
3. Subscriber disconnect → otomatik cleanup
4. Heartbeat 30s interval çalışıyor
5. Event ID monotonic artıyor
6. 11. client bağlanmaya çalışırsa reject (max 10)

---

### Task 10.3 — SSE Endpoint + FastAPI Integration

| Alan | Değer |
|------|-------|
| ID | 10.3 |
| Dosya | `agent/api/sse_api.py`, `agent/api/server.py` (modification) |
| Efor | M |
| Bağımlılık | 10.2 |
| Bağımlı | 10.4 |

#### Scope

**SSE Endpoint:**
- `GET /api/v1/events/stream` → `StreamingResponse(media_type="text/event-stream")`
- D-087: localhost security (Host validation middleware — existing)
- CORS: mevcut config yeterli (`:3000` allowed)
- `Last-Event-ID` header support: reconnect'te kaçırılan event'leri gönder (buffer: son 100 event)
- Connection lifecycle: subscribe → stream → heartbeat → unsubscribe on disconnect

**Server Integration (`server.py` modification):**
- Lifespan'a ekle: FileWatcher start + SSEManager init
- FileWatcher → SSEManager bridge: watcher event → manager broadcast
- Graceful shutdown: watcher stop + manager cleanup

#### Kabul Kriterleri

1. `curl -N http://127.0.0.1:8003/api/v1/events/stream` → SSE stream başlıyor
2. `event: connected` ilk event olarak geliyor
3. Dosya değişikliği → `event: mission_updated` stream'de görünüyor
4. 30s içinde `event: heartbeat` geliyor
5. `Host: evil.com` → 403 (D-070)
6. Client disconnect → server-side cleanup (no leak)
7. `Last-Event-ID` ile reconnect → kaçırılan event'ler replay

#### Verification

```bash
# Terminal 1: backend
cd agent && python -m agent.api.server

# Terminal 2: SSE test
curl -N -H "Accept: text/event-stream" http://127.0.0.1:8003/api/v1/events/stream

# Terminal 3: trigger event
touch logs/missions/some-mission/some-mission-state.json

# Terminal 2'de event görünmeli
```

---

### Task 10.4 — useSSE Hook (Frontend)

| Alan | Değer |
|------|-------|
| ID | 10.4 |
| Dosya | `frontend/src/hooks/useSSE.ts` |
| Efor | L |
| Bağımlılık | 10.3 |
| Bağımlı | 10.5, 10.6 |

#### Scope

```typescript
useSSE(options: {
  onEvent: (type: string, data: any) => void;
  fallbackIntervalMs?: number; // default 30_000
}): {
  status: 'connecting' | 'connected' | 'reconnecting' | 'polling';
  lastEventAt: Date | null;
}
```

- `EventSource` API kullanır: `/api/v1/events/stream`
- Connection states:
  - `connecting`: ilk bağlantı kuruluyor
  - `connected`: SSE stream aktif, event'ler geliyor
  - `reconnecting`: bağlantı kesildi, backoff ile tekrar deneniyor (D-088)
  - `polling`: 3 ardışık reconnect başarısız → polling fallback
- Exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s max (D-088)
- Polling fallback: mevcut `usePolling` pattern — 30s interval, tüm endpoint'leri fetch
- SSE reconnect başarılı → polling durur, `connected` state'e geri döner
- Page Visibility: tab hidden → SSE connection kapanır (bandwidth), tab visible → reconnect
- `Last-Event-ID`: reconnect'te kaçırılan event'leri al

#### Kabul Kriterleri

1. SSE bağlantısı kuruluyor, `connected` state'e geçiyor
2. `heartbeat` event → `lastEventAt` güncelleniyor
3. Server stop → `reconnecting` state, backoff başlıyor
4. 3 başarısız reconnect → `polling` state, 30s fetch cycle
5. Server tekrar gelince → `connected` state'e geri dönüş
6. Tab hidden → connection kapanıyor
7. Tab visible → reconnect
8. Unmount → cleanup (EventSource close, interval clear)

---

### Task 10.5 — Connection Status Indicator

| Alan | Değer |
|------|-------|
| ID | 10.5 |
| Dosya | `frontend/src/components/ConnectionIndicator.tsx`, `frontend/src/components/Layout.tsx` (modification) |
| Efor | S |
| Bağımlılık | 10.4 |
| Bağımlı | 10.6 |

#### Scope

Mevcut "Polling 30s" indicator'ı replace et:

| Status | Visual | Label |
|--------|--------|-------|
| `connecting` | Sarı dot, pulse animation | Connecting… |
| `connected` | Yeşil dot | Live |
| `reconnecting` | Turuncu dot, pulse animation | Reconnecting… |
| `polling` | Gri dot | Polling 30s |

- `lastEventAt` → "Last event Xs ago" tooltip
- No fake live: "Live" yalnızca gerçek SSE bağlantısı varken (D-060 prensibi)

#### Kabul Kriterleri

1. 4 state → 4 farklı visual (renk + label)
2. "Live" yalnızca `connected` state'te görünür
3. Tooltip `lastEventAt` gösteriyor
4. Transition: connecting → connected → reconnecting → polling smooth

---

### Task 10.6 — Page Integration (usePolling → useSSE Migration)

| Alan | Değer |
|------|-------|
| ID | 10.6 |
| Dosya | Tüm page dosyaları (modification) |
| Efor | L |
| Bağımlılık | 10.4, 10.5 |
| Bağımlı | 10.7 |

#### Scope

Her page'in polling'ini SSE-driven invalidation'a geçir:

**Pattern:**
```typescript
// ESKİ (Sprint 9):
const { data, error, loading, refresh } = usePolling(getMissions, 30_000);

// YENİ (Sprint 10):
const { data, error, loading, refresh } = usePolling(getMissions, 30_000);
// + SSE invalidation:
useSSEInvalidation('mission_list_changed', refresh);
useSSEInvalidation('mission_updated', refresh);
```

`usePolling` kaldırılmıyor — fallback olarak korunuyor (D-088). SSE event gelince `refresh()` çağırılarak immediate fetch tetikleniyor. SSE connected iken polling interval uzatılıyor (300s) veya duruyor.

| Page | SSE Event(ler) | Action |
|------|---------------|--------|
| MissionListPage | `mission_list_changed`, `mission_updated` | `refresh()` |
| MissionDetailPage | `mission_updated` (filtered by missionId) | `refresh()` |
| HealthPage | `health_changed`, `capability_changed` | `refresh()` |
| ApprovalsPage | `approval_changed` | `refresh()` |
| TelemetryPage | `telemetry_new` | `refresh()` |

**Polling interval adjustment:**
- SSE connected → polling interval 300s (emergency fallback)
- SSE disconnected → polling interval 30s (original)

#### Kabul Kriterleri

1. SSE event → ilgili page anında refresh (polling 30s beklemez)
2. SSE disconnected → 30s polling devam eder (Sprint 9 behavior preserved)
3. MissionDetailPage: sadece kendi missionId'li event'lere tepki verir
4. Tüm 5 page'de SSE integration çalışıyor
5. `usePolling` hâlâ import edilebilir ve çalışır (removed değil)

---

### Task 10.7 — Debouncing + Multi-Tab

| Alan | Değer |
|------|-------|
| ID | 10.7 |
| Dosya | `agent/api/file_watcher.py` (modification), `frontend/src/hooks/useSSE.ts` (modification) |
| Efor | M |
| Bağımlılık | 10.6 |
| Bağımlı | 10.8 |

#### Scope

**Backend debouncing:**
- Mission dosyaları hızlı değişebilir (stage execution sırasında state + mission + summary art arda yazılır)
- Debounce: aynı mission için 500ms window — window içindeki tüm değişiklikler tek `mission_updated` event'e birleşir
- Telemetry: JSONL append sık olabilir — 2s debounce

**Frontend:**
- SSE event burst → `refresh()` çağrılarını debounce (300ms)
- Aynı entity için rapid invalidation → tek fetch
- Multi-tab: her tab kendi SSE bağlantısını kurar (backend max 10 client)

#### Kabul Kriterleri

1. 3 dosya 100ms arayla değişir → tek `mission_updated` event
2. Frontend'de 3 rapid event → tek `refresh()` call
3. 2 tab açık → 2 SSE bağlantısı, ikisi de event alıyor
4. 11. tab → reject (max 10 backend)

---

### Task 10.8 — Test Suite + GPT Review

| Alan | Değer |
|------|-------|
| ID | 10.8 |
| Dosya | `agent/tests/test_sse.py`, `frontend/src/__tests__/useSSE.test.tsx`, `frontend/src/__tests__/ConnectionIndicator.test.tsx` |
| Efor | M |
| Bağımlılık | 10.7 |
| Bağımlı | — |

#### Scope

**Backend tests (`test_sse.py`):**
- FileWatcher: mtime change → event, missing file → no crash, debounce
- SSEManager: subscribe/unsubscribe, broadcast, heartbeat, max clients
- SSE endpoint: stream response, `Last-Event-ID` replay, Host attack → 403

**Frontend tests:**
- `useSSE.test.tsx`: connect, reconnect, backoff, polling fallback, cleanup
- `ConnectionIndicator.test.tsx`: 4 state → 4 visual

**Evidence bundle:**
```bash
# Backend
cd agent && pytest tests/ -v 2>&1 | tee ../evidence/sprint-10/pytest-output.txt

# Frontend
cd frontend && npx vitest run 2>&1 | tee ../evidence/sprint-10/vitest-output.txt
cd frontend && npx tsc --noEmit 2>&1 | tee ../evidence/sprint-10/tsc-output.txt
cd frontend && npm run lint 2>&1 | tee ../evidence/sprint-10/lint-output.txt
cd frontend && npm run build 2>&1 | tee ../evidence/sprint-10/build-output.txt

# Validator
python tools/validate_sprint_docs.py --sprint 10 2>&1 | tee evidence/sprint-10/validator-output.txt

# Live SSE test
curl -N http://127.0.0.1:8003/api/v1/events/stream | head -20 > evidence/sprint-10/sse-stream.txt
```

**GPT cross-review:**
- SSE contract: event format, reconnect protocol, fallback behavior
- Backend: watcher reliability, event ordering, memory leak check
- Frontend: hook lifecycle, cleanup, state transitions

#### Kabul Kriterleri

1. Backend: 170+ legacy + ~15 SSE tests, 0 failure
2. Frontend: 18 legacy + ~8 SSE tests, 0 failure
3. `npx tsc --noEmit` → 0 error
4. `npm run lint` → 0 error
5. `npm run build` → success
6. GPT review: 0 blocking finding
7. `validate_sprint_docs.py --sprint 10` → all PASS
8. Live SSE curl test: event stream görünüyor

---

## Section 6: Sprint Exit Criteria

| # | Criterion | Task |
|---|----------|------|
| 1 | SSE endpoint stream edebiliyor | 10.3 |
| 2 | FileWatcher dosya değişikliği algılıyor | 10.1 |
| 3 | Debounce çalışıyor (rapid changes → tek event) | 10.7 |
| 4 | Frontend SSE bağlantısı kuruluyor | 10.4 |
| 5 | "Live" indicator yalnızca gerçek SSE bağlantısında | 10.5 |
| 6 | SSE event → ilgili page anında refresh | 10.6 |
| 7 | Server stop → reconnecting → backoff → polling fallback | 10.4 |
| 8 | Server tekrar gelince → SSE reconnect | 10.4 |
| 9 | Tab hidden → SSE kapanıyor, visible → reconnect | 10.4 |
| 10 | `Last-Event-ID` ile missed event replay | 10.3 |
| 11 | Heartbeat 30s | 10.2 |
| 12 | Max 10 SSE client | 10.2 |
| 13 | Multi-tab çalışıyor | 10.7 |
| 14 | `usePolling` fallback korunuyor | 10.6 |
| 15 | Backend 170+ tests, 0 failure | 10.8 |
| 16 | Frontend tests all pass | 10.8 |
| 17 | 0 TypeScript error | 10.8 |
| 18 | 0 lint error | 10.8 |
| 19 | Production build success | 10.8 |
| 20 | GPT review 0 blocking | 10.8 |
| 21 | `validate_sprint_docs.py --sprint 10` all PASS | 10.8 |

---

## Section 7: Files Created/Modified

| File | Type | Task |
|------|------|------|
| `agent/api/file_watcher.py` | Created | 10.1 |
| `agent/api/sse_manager.py` | Created | 10.2 |
| `agent/api/sse_api.py` | Created | 10.3 |
| `agent/api/server.py` | Modified | 10.3 (lifespan + watcher + SSE) |
| `agent/tests/test_sse.py` | Created | 10.8 |
| `frontend/src/hooks/useSSE.ts` | Created | 10.4 |
| `frontend/src/components/ConnectionIndicator.tsx` | Created | 10.5 |
| `frontend/src/components/Layout.tsx` | Modified | 10.5 (indicator swap) |
| `frontend/src/pages/MissionListPage.tsx` | Modified | 10.6 |
| `frontend/src/pages/MissionDetailPage.tsx` | Modified | 10.6 |
| `frontend/src/pages/HealthPage.tsx` | Modified | 10.6 |
| `frontend/src/pages/ApprovalsPage.tsx` | Modified | 10.6 |
| `frontend/src/pages/TelemetryPage.tsx` | Modified | 10.6 |
| `frontend/src/hooks/usePolling.ts` | Modified | 10.6 (interval adjustment) |
| `frontend/src/__tests__/useSSE.test.tsx` | Created | 10.8 |
| `frontend/src/__tests__/ConnectionIndicator.test.tsx` | Created | 10.8 |

**Total:** 8 created, 8 modified.

---

## Section 8: Riskler ve Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| WSL2 FS mtime reliability | HIGH | MEDIUM | D-085 polling-based (inotify bypass). 1s poll yeterli |
| SSE memory leak (abandoned connections) | HIGH | MEDIUM | Max 10 client + heartbeat timeout + unsubscribe cleanup |
| Rapid file changes during mission execution | MEDIUM | HIGH | Debounce 500ms (mission), 2s (telemetry) |
| EventSource browser compatibility | LOW | LOW | Modern browsers all support. Fallback to polling |
| Race condition: SSE event before data written | MEDIUM | MEDIUM | Event = invalidation signal, frontend fetches fresh data |

---

## Section 9: Downstream Impact (Sprint 11)

| Sprint 10 Output | Sprint 11 Consumer |
|-----------------|-------------------|
| SSE infrastructure | Mutation confirmation via SSE push |
| `useSSE` hook | Optimistic UI + SSE confirmation pattern |
| ConnectionIndicator | Extended with mutation-in-progress state |
| FileWatcher | Approval store change → `approval_changed` event |

---

*Sprint 10 Task Breakdown — OpenClaw Mission Control Center SSE Live Updates*
*Date: 2026-03-25*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Decisions Frozen: D-085 (polling-based watcher), D-086 (per-entity events), D-087 (localhost-only SSE), D-088 (exponential backoff + polling fallback)*
