# Technical Debt Report — Vezir Platform

**Date:** 2026-04-09
**Auditor:** Claude Code (Opus) — 4 parallel analysis agent + manual verification
**Scope:** Full codebase — backend, frontend, infra, architecture
**Baseline:** S84 closed, 2497 tests, 147 decisions, Phase 10

---

## Executive Summary

| Kategori | HIGH | MEDIUM | LOW | Toplam |
|----------|------|--------|-----|--------|
| Backend Kod Kalitesi | 3 | 6 | 3 | 12 |
| Frontend | 1 | 6 | 2 | 9 |
| Altyapi & Config | 5 | 4 | 5 | 14 |
| Mimari | 5 | 5 | 1 | 11 |
| **Toplam** | **14** | **21** | **11** | **46** |

---

## 1. BACKEND KOD KALiTESi

### HIGH-1: controller.py God Object (2224 satir)

**Dosya:** `agent/mission/controller.py` (2224 LOC, 50+ method)
**Severity:** HIGH
**Etki:** Readability, testability, merge conflict riski

Orchestration, state transitions, tool execution, provider calls, quality gates, token budgeting, approval FSM, audit trails — hepsi tek dosyada. 39+ conditional/lazy import cagrimla circular dependency'den kacinilmaya calismis:

```python
def execute_mission(self, ...):
    from context.assembler import ContextAssembler      # line 819
    from context.expansion_broker import ExpansionBroker  # line 820
    from mission.role_registry import resolve_role        # line 821
```

S63/S64'te decomposition baslatildi (D-139, persistence_adapter.py, recovery_engine.py cikarildi) ama ana govde hala monolitik.

**Ek sorunlar:**
- Missing type hints: `__init__`, `_enrich_working_set_from_discovery`, `_create_rework_stages` (lines 31, 1185, 1649)
- Hardcoded magic numbers: `SEMANTIC_LIMITS = {"A": 5000, "B": 2000, "C": 500, "D": 1000}` (line 1115), token threshold `40000` (line 1156), truncation limits `2000, 3000` (lines 1244-1248)
- **Reverse dependency:** line 1494 imports `_get_store()` from `api/project_api.py` — API layer'a bagimlillik

**Oneri:** PlanningService, ExecutionService, RiskClassifier, TokenBudgetManager, ApprovalCoordinator olarak 5-6 module bolunmeli.

---

### HIGH-2: normalizer.py Exception Swallowing (787 satir, 19+ bare except)

**Dosya:** `agent/api/normalizer.py`
**Severity:** HIGH
**Etki:** Silent data corruption, debugging zorlugu

787 satirlik dosyada 19+ adet `except Exception:` + `pass` pattern'i var. Hatalar sessizce yutulup `None` veya bos deger donuyor. Normalizer data integrity icin kritik — swallowed exception'lar corrupted mission data'ya yol acabilir.

**Satirlar:** 88, 122, 144, 169, 209, 233, 243, 253, 292, 313, 334, 352, 395, 480, 482, 551, 615, 640, 768

**Ek sorun:** Stale detection (line 237-244) — dosya yasi 3600s threshold'u ile mission state'i `timed_out`'a cevirme mantigi, gercek state dosyasiyla yarisiyor.

**Oneri:** Minimum structured logging, critical path'lerde exception propagation, stale detection mantigi gozden gecirmeli.

---

### HIGH-3: Test Coverage Gap — 166 modül icin 106 test dosyasi (%64)

**Severity:** HIGH
**Etki:** Regression riski, refactoring guvensziligi

| Katman | Eksik Test | Onemli Ornekler |
|--------|------------|-----------------|
| API Layer | 44 dosya | `server.py`, `normalizer.py`, `mission_mutation_api.py`, `dashboard_api.py`, `health_api.py`, `csrf_middleware.py`, `circuit_breaker.py`, `throttle.py` |
| Mission Core | 11 dosya | `controller.py`, `mission_state.py`, `quality_gates.py`, `specialists.py`, `complexity_router.py`, `resilience.py` |
| Services | 14 dosya | `approval_service.py`, `tool_catalog.py`, `risk_engine.py`, `mcp_client.py`, `filesystem_guard.py` |
| Providers | 6 dosya | `azure_openai_provider.py`, `gpt_provider.py`, `claude_provider.py`, `ollama_provider.py`, `factory.py`, `mock_provider.py` |
| Observability | 6 dosya | `tracing.py`, `meters.py`, `alert_engine.py`, `structured_logging.py`, `otel_setup.py` |
| Context | 8 dosya | `assembler.py`, `working_set.py`, `token_budget.py`, `expansion_broker.py` |
| Persistence | 4 dosya | `mission_store.py`, `trace_store.py`, `metric_store.py`, `dlq_store.py` |

**Not:** Bazi moduller integration test'ler icinde dolayli test ediliyor, ama dedicated unit test'leri yok. Security-critical moduller (`csrf_middleware.py`, `circuit_breaker.py`, `throttle.py`) tamamen test edilmemis.

---

### MEDIUM-1: Bare `except Exception:` Pattern (22 dosyada 51+ occurrence)

**Codebase geneli.** normalizer.py disinda: `atomic_write.py` (2), `persistence_adapter.py` (4), `approval_service.py` (5), `analyze_telemetry.py` (5), `agents_api.py` (1), `health_api.py` (4+), `mission_mutation_api.py` (2).

---

### MEDIUM-2: Hardcoded localhost/Port References (50+ occurrence)

- `http://localhost:4000` — 8 dosyada (oauth_provider, telegram_bot, csrf_middleware, server.py)
- `http://localhost:8001` — 5 dosyada (health_api, mcp_client, tool_catalog)
- `http://localhost:8003` — 3 dosyada (telegram_bot)
- Magic numbers: token limit `40000`, context_budget `40000`, truncation `2000/3000`

**Oneri:** Merkezi `config/constants.py` veya env-based config.

---

### MEDIUM-3: controller.py Lazy Imports (39+ occurrence)

**Severity:** MEDIUM

39+ conditional import controller.py icinde. Hard to understand module dependencies, slower function calls, difficult to detect circular imports.

---

### MEDIUM-4: `type: ignore` Comments

**Dosya:** `agent/mission/policy_engine.py:370, 386`
**Sorun:** `return self.get_rule(model.name)  # type: ignore[return-value]` — `None` donebilen metod `PolicyRule` doner gibi isaretlenmis.

---

### MEDIUM-5: TODO/FIXME Comments

**Dosya:** `agent/tests/test_atomic_write_compliance.py:29`
**Icerik:** `TODO: Remove entries as each file is migrated to atomic_write_json.`

---

### MEDIUM-6: sys.path Manipulation

**Dosya:** `agent/api/retention_api.py:80-82`
```python
tools_dir = str(P(__file__).resolve().parent.parent.parent / "tools")
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)
```
Kirilgan path hesaplama, module isolation ihlali.

---

### LOW-1: `oc_agent_runner_lib.py` (481 satir) — Monolithic ama decompose edilmis.
### LOW-2: `tool_catalog.py` Inline PowerShell (687 satir) — Harici dosyalara tasinabilir.
### LOW-3: `analyze_telemetry.py` Error Handling (5 bare except) — Tool script, production degil.

---

## 2. FRONTEND

### HIGH-4: `generated.ts` Boyutu (8326 satir)

**Dosya:** `frontend/src/api/generated.ts`
**Severity:** HIGH

Auto-generated OpenAPI client. Her API degisikliginde tamami regenerate. IDE performansi ve review zorlugu.

**Oneri:** Domain bazli split (missions, projects, auth, admin).

---

### MEDIUM-7: Buyuk Page Component'ler (8 dosya 280+ satir)

| Dosya | Satir | Oneri |
|-------|-------|-------|
| `MissionDetailPage.tsx` | 477 | Custom hook + sub-component |
| `ApprovalsPage.tsx` | 449 | Custom hook + sub-component |
| `client.ts` | 377 | Domain split |
| `ProjectDetailPage.tsx` | 351 | Custom hook + sub-component |
| `HealthPage.tsx` | 312 | Utility extraction |
| `CostDashboardPage.tsx` | 302 | Chart sub-component |
| `MonitoringPage.tsx` | 284 | Data hook extraction |
| `StageCard.tsx` | 281 | Sub-component extraction |

---

### MEDIUM-8: Frontend Test Coverage Gaps

Test dosyasi olmayan buyuk component'ler:
- `MissionDetailPage.tsx` (477), `ApprovalsPage.tsx` (449), `HealthPage.tsx` (312), `MissionListPage.tsx` (249), `MonitoringPage.tsx` (284), `TelemetryPage.tsx` (192)
- Core altyapi: `SSEContext.tsx`, `ProtectedRoute.tsx`, `App.tsx`

---

### MEDIUM-9: SSEContext useEffect Dependency Eksikligi

**Dosya:** `frontend/src/hooks/SSEContext.tsx:33-35`
```typescript
useEffect(() => {
  callbackRef.current = callback
})  // ← Missing dependency array — runs every render
```

---

### MEDIUM-10: Hardcoded Timing Constants (8+ yer)

| Dosya | Deger | Aciklama |
|-------|-------|----------|
| `AuthContext.tsx:184` | `50 * 60 * 1000` | Token refresh (comment says "10 min before expiry") |
| `MissionDetailPage.tsx:41` | `10_000` | Polling interval |
| `HealthPage.tsx:26-28` | `10_000, 30_000, 15_000` | Multiple polling intervals |
| `RunTemplateModal.tsx:90` | `1500` | Hardcoded delay |
| `ApprovalsPage.tsx:85` | `5000` | Timeout |
| `ConnectionIndicator.tsx:33` | `5_000` | Update interval |
| `FreshnessIndicator.tsx:28` | `5_000` | Update interval |

**Oneri:** `src/config/timings.ts` constants dosyasi.

---

### MEDIUM-11: Inline Styles — Dynamic Width

**Dosya:** `HealthPage.tsx:102-155` — 7 adet `style={{ width: \`${...}%\` }}` pattern'i.
**Dosya:** `MissionDetailPage.tsx:383` — Ayni pattern.

**Oneri:** Utility function veya Tailwind CSS width utilities.

---

### MEDIUM-12: Accessibility Gaps

- 35 TSX dosyasinin sadece 10'unda aria attribute'lari var
- `Sidebar.tsx` — `aria-current="page"` eksik
- `Layout.tsx` — Skip-to-main-content link yok
- Keyboard navigation tam test edilmemis

---

### LOW-4: TypeScript `any` — **Sifir.** Temiz.
### LOW-5: TODO/FIXME — **Sifir.** Temiz.

---

## 3. ALTYAPI & CONFIG

### HIGH-5: CORS/Origin List Duplikasyonu + Inconsistency

**Dosyalar:** `server.py:234`, `csrf_middleware.py:15`, `server.py:262`
**Severity:** HIGH

3 ayri yerde origin listesi. CSRF middleware'de `http://localhost:8003` var ama CORS config'de yok. Birini degistirip digerini unutmak guvenlik acigi olusturur.

---

### HIGH-6: Docker Python Versiyon Uyumsuzlugu

- **Dockerfile.prod:** `python:3.12-slim`
- **Local dev:** Python 3.14
- Iki major versiyon farki.

---

### HIGH-7: CI Dependency Cache Eksik

**Dosya:** `.github/workflows/ci.yml`
**Severity:** HIGH
**Etki:** Her CI run tamamen from scratch install yapiyor

`actions/setup-python@v6` ve `actions/setup-node@v6` config'lerinde `cache: "pip"` ve `cache: "npm"` parametreleri yok. CI sureleri 2-3x uzuyor.

---

### HIGH-8: Dev Dockerfile Root Olarak Calisiyor

**Dosya:** `Dockerfile` (dev)
**Severity:** HIGH

`USER` directive yok — container root olarak calisiyor. `Dockerfile.prod` dogru sekilde `USER vezir` kullaniyor (line 57) ama dev Dockerfile'da bu eksik.

---

### HIGH-9: requirements.txt Upper Bound Yok

**Dosya:** `agent/requirements.txt`
**Severity:** HIGH

Dependencies `>=` operator kullaniyor ust sinir yok. `openai>=1.50.0` gibi — OpenAI 2.x breaking change geldiginde production kirilabilir.

**Oneri:** `~=` (compatible release) veya `>=X.Y,<X+1` pattern'i.

---

### MEDIUM-13: NEXT.md Staleness

`**Current:** Phase 10 active. Sprint 81 closed.` — S84 kapanmis ama NEXT.md S81 diyor. Carry-forward tablosu da stale.

---

### MEDIUM-14: open-items.md Duplicate Entry

Sprint 79 satirlari 97 ve 99'da iki kez listelenmis.

---

### MEDIUM-15: Env Var Sprawl (76 unique reads)

76 farkli env var, merkezi dokumantasyon yok.

---

### MEDIUM-16: CI Badge Force Push

**Dosya:** `.github/workflows/ci.yml:297`
`git push origin badges --force` — `--force-with-lease` kullanilmali. Concurrent workflow'larda race condition riski.

---

### LOW-6: Orphaned Root Files

| Dosya | Boyut | Aciklama |
|-------|-------|----------|
| `oc-task-runtime-bootstrap-v3.4.ps1` | 112KB | Eski bootstrap script, workflows'ta referansi yok |
| `bridge-stderr.log` | 330B | Eski bridge log dosyasi |
| `baseline/`, `bridge/`, `results/` | — | Bos/minimal kullanilan dizinler |

---

### LOW-7: Uncommitted Dosyalar

- `config/capabilities.json` — modified (unstaged)
- `docs/ai/reviews/S84-GPT-REVIEW.md` — untracked
- `.task_prompt` — staged

---

### LOW-8: Benchmark Self-Compare

**Dosya:** `.github/workflows/benchmark.yml:34`
Baseline dosyasini kendisiyle karsilastiriyor — regression detection fiilen devre disi.

---

### LOW-9: Stale Sprint References in Scripts

`tools/preflight.sh:3` — "Sprint 48 (48.4)" comment'i.
`tools/sprint-closure-check.sh:11` — "Sprint 11 specific" comment'i.

---

### LOW-10: Config Format Karmasikligi

JSON (capabilities, features, grafana) + YAML (policies) + example (env, webhooks) — format standardi yok.

---

## 4. MiMARi

### HIGH-10: Global Singleton Pattern (15+ API dosyasi)

**Pattern:**
```python
_store: Optional[ProjectStore] = None
def _get_store() -> ProjectStore:
    global _store
    if _store is None:
        _store = ProjectStore()  # No DI
    return _store
```

15+ API dosyasinda ayni pattern. Test isolation imkansiz, thread-safety garantisi yok, dependency injection yok.

**Ek:** `mission_create_api.py:61-80` background thread spawn ediyor, shared `MISSIONS_DIR`'e erisim — senkronizasyon yok.

---

### HIGH-11: API Router Sayisi (36 router, ~123 endpoint)

**Dosya:** `agent/api/server.py` (425 satir, 36 `include_router`)
**Monolitik API** — domain separation yok.

---

### HIGH-12: Validation Duplikasyonu (4 Farkli Pattern)

| Dosya | Pattern |
|-------|---------|
| `mission_api.py:25` | `_SAFE_ID_RE.match()` — basit regex |
| `mission_mutation_api.py:26-35` | `.resolve()` ile path traversal check |
| `project_api.py` | Pydantic validation only, ID check yok |
| `approval_mutation_api.py` | Baska bir validation pattern |

Inconsistent validation = security riski. Path traversal test edilmemis endpoint'ler olabilir.

---

### HIGH-13: VEZIR_AUTH_BYPASS Audit Eksikligi

**Dosya:** `agent/auth/keys.py:71-80`
`VEZIR_AUTH_BYPASS=1` ile tum auth devre disi kaliyor. Bypass aktifken middleware'de uyari log'u var ama server startup'ta acik uyari yok. Production'da unutulabilir.

---

### HIGH-14: Controller → API Reverse Dependency

**Dosya:** `agent/mission/controller.py:1494`
Controller, `api/project_api.py`'den `_get_store()` import ediyor. API layer'a bagimlillik — architecture violation. Controller business logic, API presentation — dependency akisi ters.

---

### MEDIUM-17: 3 Farkli Error Response Formati

1. `HTTPException`: `{"detail": "..."}`
2. RFC 9457 envelope: `{"type": "...", "title": "...", "detail": "..."}`
3. Custom APIError: `{"error": "...", "details": "..."}`

Frontend bu formatlari normalize etmek zorunda.

---

### MEDIUM-18: EventBus Pass-through Eksik (D-147)

S81'de EventBus production'a wire edildi ama controller-to-runner event propagation hala yok. Carry-forward.

---

### MEDIUM-19: Provider Abstraction Inconsistency

6 provider, hicbirinin dedicated test dosyasi yok. Farkli error handling yaklasimlari.

---

### MEDIUM-20: Configuration Loading — 4 Mekanizma

1. `os.environ.get()` — 76 key
2. JSON — `config/*.json`
3. YAML — `config/policies/*.yaml`
4. Python defaults — hardcoded fallback

Merkezi validation yok.

---

### MEDIUM-21: Layering Violations — Telegram Bot

**Dosya:** `agent/telegram_bot.py:160-178`
Dogrudan `http://localhost:8003` API'sine raw urllib call. Shared API client veya direct function import kullanilmali.

---

### LOW-11: D-021 → D-058 Decision Extraction

38 Phase 4 decision DECISIONS.md'ye extract edilmemis. AKCA-assigned, non-blocking. Sprint 8'den beri carry-forward.

---

## 5. ONERi MATRISI — Oncelikli Aksiyonlar

### S85 — Quick Win Sprint (Effort: S-M, 3-4 gun)

| # | Aksiyon | Severity | Effort |
|---|---------|----------|--------|
| 1 | normalizer.py exception handling fix (logging + propagation) | HIGH | S |
| 2 | CORS/Origin config centralization (tek kaynak) | HIGH | S |
| 3 | Docker Python 3.12→3.14 upgrade | HIGH | S |
| 4 | CI dependency cache ekleme (pip + npm) | HIGH | S |
| 5 | Dev Dockerfile USER directive | HIGH | XS |
| 6 | requirements.txt upper bounds | HIGH | S |
| 7 | NEXT.md + open-items.md stale fix | MEDIUM | XS |
| 8 | Validation pattern centralization | HIGH | S |

### S86 — Controller Decomposition Phase 2

| # | Aksiyon | Severity | Effort |
|---|---------|----------|--------|
| 9 | controller.py → 5-6 focused service | HIGH | L |
| 10 | Reverse dependency fix (controller→API) | HIGH | S |
| 11 | Global singleton → DI pattern | HIGH | M |
| 12 | Error response format unification (RFC 9457) | MEDIUM | M |

### S87-89 — Test Coverage + Frontend

| # | Aksiyon | Severity | Effort |
|---|---------|----------|--------|
| 13 | Test coverage: mission core + persistence | HIGH | L |
| 14 | Test coverage: security modules (CSRF, throttle, circuit breaker) | HIGH | M |
| 15 | generated.ts domain split | HIGH | M |
| 16 | Frontend page component extraction | MEDIUM | L |
| 17 | Frontend timing constants centralization | MEDIUM | S |
| 18 | Provider test coverage | MEDIUM | M |
| 19 | EventBus runner pass-through | MEDIUM | M |
| 20 | Pydantic Settings centralization | MEDIUM | M |

---

## 6. METRIKLERIN OZETI

| Metrik | Deger | Durum |
|--------|-------|-------|
| Backend modulleri | 166 | — |
| Test dosyalari | 106 | %64 coverage (dosya bazli) |
| Toplam test | 2497 | Yuksek |
| `except Exception: pass` | 51+ (22 dosyada) | Yuksek risk |
| TODO/FIXME (backend) | 1 | Temiz |
| TypeScript `any` (frontend) | 0 | Temiz |
| Frontend TODO/FIXME | 0 | Temiz |
| Env var reads | 76 unique | Config sprawl |
| API router | 36 (~123 endpoint) | Monolitik |
| En buyuk dosya | 2224 LOC (controller.py) | God object |
| Lazy imports (controller) | 39+ | Circular dependency workaround |
| CORS/Origin lists | 3 ayri yer + inconsistency | Drift + security riski |
| Docker Python | 3.12 vs local 3.14 | Version mismatch |
| CI cache | Yok (pip + npm) | Build yavasi |
| Validation patterns | 4 farkli implementasyon | Security inconsistency |
| Error response formats | 3 farkli format | Client confusion |
| Global singletons | 15+ API dosyasi | No DI, test isolation zor |
| Stale docs | 2 dosya (NEXT.md, open-items.md) | Guncellenmeli |
| Orphaned root files | 3 (112KB + 330B + dirs) | Temizlenmeli |
| CI Actions | Guncel (v6/v7) | Temiz |
| Security (CodeQL) | 0 open | Temiz |
| Auth bypass flag | `VEZIR_AUTH_BYPASS=1` | Audit eksik |

---

## 7. RISK DEGERLENDIRMESI

| Risk | Severity | Olasilik | Etki |
|------|----------|----------|------|
| Silent data corruption (normalizer) | HIGH | MEDIUM | Corrupted mission state |
| Path traversal (inconsistent validation) | HIGH | LOW | Unauthorized file access |
| Auth bypass in production | HIGH | LOW | Full auth skip |
| Breaking dep upgrade (no upper bound) | HIGH | MEDIUM | CI/production kirilmasi |
| CORS drift (duplicate config) | MEDIUM | HIGH | Security hole |
| Race condition (mission thread) | MEDIUM | LOW | Corrupted mission |
| Regression (low test coverage) | HIGH | HIGH | Undetected bugs |

---

**Rapor sonu.** 46 bulgu: 14 HIGH, 21 MEDIUM, 11 LOW.
S85 sprint onerisi: 8 quick-win aksiyonla HIGH severity item'larin cogu cozulebilir.
