# Sprint 17 Kickoff — Phase 6 Controlled Start

## Metadata

| Field | Value |
|-------|-------|
| Sprint | 17 |
| Phase | 6 |
| Model | **A** (forced — D-105: max 2 consecutive Model B, S13-S16 were Model B) |
| implementation_status | done |
| closure_status | closed |
| Owner | AKCA |
| Date | 2026-03-27 |

---

## Goal

Phase 6'nin ilk kontrollü sprint'i. CI pipeline'daki bozuk benchmark akisini düzeltmek, eksik dependency'leri eklemek, doc model ambiguity'yi gidermek ve carry-forward item'lardan ilk batch'i scope'a almak.

## Scope — IN

| # | Task | Deliverable | Status |
|---|------|-------------|--------|
| T17-1 | Benchmark workflow fix | `.github/workflows/benchmark.yml` — working path + evidence upload | Done |
| T17-2 | CI dependency fix | `requirements.txt` + `package-lock.json` — missing deps added | Done |
| T17-3 | Benchmark summary fix | `tools/benchmark_api.py` — hardcoded false summary replaced with computed values | Done |
| T17-4 | Source-of-truth doc alignment | STATE.md + NEXT.md canonical marker, D-109 alignment | Done |
| T17-5 | Decision freeze (D-109, D-110) | Decision records + DECISIONS.md index | Done |
| T17-6 | Sprint plan + evidence plan | This document | Done |
| T17-G1 | Mid Review Gate | Contract/CI/doc drift check — 6/6 PASS | Done |
| T17-G2 | Final Review Gate | Evidence bundle + closure recommendation | Done |
| T17-G3 | GPT Review | S17-REVIEW.md — HOLD, 4 patches | Done |
| T17-G4 | HOLD Patch Application | Fix HOLD-1→HOLD-4 + re-review | In Progress |

### Scope Delta (Implementation Note)

Original kickoff scope had T17-1 through T17-4 + gates. During implementation:
- **T17-2 added:** `requirements.txt` was missing fastapi/uvicorn/pydantic/httpx and `package-lock.json` had picomatch mismatch — discovered when CI failed after initial push.
- **T17-3 added:** GPT review (HOLD-1) identified that `benchmark_api.py` summary was hardcoded and did not reflect actual measurements. Fixed to compute from real data.
- **T17-G3/G4 added:** GPT review returned HOLD with 4 patches required.

## Scope — OUT

- Yeni Phase 6 feature implementation (backend restructure, Docker, Playwright vb.)
- Parallel architecture expansion
- D-021→D-058 extraction (AKCA-assigned, non-blocking)
- Jaeger deployment
- Benchmark regression gate (deferred per D-109)

---

## Decisions

### D-109 — Frozen
**Problem:** Benchmark evidence-only mi, yoksa gerçek regression gate mi olacak?
**Decision:** Evidence-only. Regression gate icin JSON baseline + threshold mekanizmasi Phase 6'da ayri sprint'te yapilsin.
**Record:** `docs/decisions/D-109-BENCHMARK-STRATEGY.md`

### D-110 — Frozen
**Problem:** Doc model — STATE.md/NEXT.md mi canonical, repo-native packet workflow mu?
**Decision:** Dual model: STATE.md/NEXT.md canonical for system state, handoffs/current.md canonical for session continuity. Araclar opsiyonel.
**Record:** `docs/decisions/D-110-DOC-MODEL.md`

---

## Task Breakdown

### T17-1: Benchmark Workflow Fix

**Goal:** CI benchmark job'u gercekten calisir hale getir.

**Changes:**
1. `cd agent &&` prefix kaldirildi — `benchmark_api.py` repo root `tools/` altinda
2. Sahte `compare_benchmark.py` step'i komple cikarildi
3. Evidence verify step eklendi: `test -f evidence/sprint-12/benchmark.txt`
4. Artifact upload step eklendi

**Acceptance criteria:**
- [x] `python tools/benchmark_api.py` repo root'tan calisiyor
- [x] `evidence/sprint-12/benchmark.txt` uretiliyor
- [x] Compare step yok (D-109)
- [x] Artifact upload step mevcut

### T17-2: CI Dependency Fix

**Goal:** CI'da eksik Python ve Node dependency'leri duzeltmek.

**Changes:**
1. `agent/requirements.txt` — fastapi, uvicorn, pydantic, httpx eklendi
2. `frontend/package-lock.json` — picomatch version mismatch duzeltildi (npm install)

**Acceptance criteria:**
- [x] CI backend job pass (no ModuleNotFoundError)
- [x] CI frontend job pass (npm ci succeeds)
- [x] All 3 workflows green

### T17-3: Benchmark Summary Fix

**Goal:** benchmark_api.py'daki hardcoded false summary'yi gercek olcumlerden hesaplanan degerlerle degistir.

**Changes:**
1. Summary artik `statistics.mean()` ve `max()` ile hesaplaniyor
2. "All GET < 50ms" gibi hardcoded claim'ler kaldirildi
3. Evidence dosyasi yeniden uretildi

**Acceptance criteria:**
- [x] Summary gercek olcum degerlerini yansitir
- [x] Hardcoded false claim yok
- [x] evidence/sprint-12/benchmark.txt yeniden uretildi

### T17-4: Source-of-Truth Doc Alignment

**Goal:** Canonical doc rollerini netlestir, D-109 ile catisma kaldir.

**Changes:**
1. STATE.md'ye Sprint 17 entry eklendi
2. NEXT.md'ye Sprint 17 status eklendi
3. Doc model marker'lar eklendi
4. STATE.md'de benchmark "regression gate" → "evidence-only (D-109)" duzeltildi

**Acceptance criteria:**
- [x] STATE.md Sprint 17'yi yansitiyor
- [x] NEXT.md Phase 6 Sprint 17 listeliyor
- [x] Doc hierarchy net: STATE.md (system) > handoffs/current.md (session)
- [x] STATE.md CI/CD wording D-109 ile uyumlu

### T17-5: Decision Freeze

**Acceptance criteria:**
- [x] D-109 frozen + record + DECISIONS.md index
- [x] D-110 frozen + record + DECISIONS.md index

### T17-6: Sprint Plan + Evidence Freeze

**Acceptance criteria:**
- [x] Kickoff doc committed
- [x] Evidence checklist complete
- [x] Review gates embedded

---

## Mid Review Gate (T17-G1) — PASS

**Results:**
- [x] benchmark.yml fix committed ve lokal test geciyor
- [x] D-109 frozen (benchmark strategy)
- [x] D-110 frozen (doc model)
- [x] CI truth = claimed truth (no false green)

---

## Final Review Gate (T17-G2) — PASS

**Results:**
- [x] Tum T17 task'lari acceptance criteria PASS
- [x] Evidence bundle complete
- [x] STATE.md ve NEXT.md guncel
- [x] Handoff current.md guncel
- [x] No open blockers

---

## GPT Review (T17-G3) — HOLD → Patching

**Verdict:** HOLD — 4 patches required
**Record:** `docs/ai/reviews/S17-REVIEW.md`

| # | Finding | Patch | Status |
|---|---------|-------|--------|
| HOLD-1 | Benchmark summary internally false | Fix benchmark_api.py summary computation | Done |
| HOLD-2 | STATE.md conflicts with D-109 | Update "regression gate" → "evidence-only" | Done |
| HOLD-3 | Kickoff doc stale | Update this document | Done |
| HOLD-4 | Scope drift not formalized | Add scope delta section | Done |

---

## Evidence Checklist

| # | Evidence | Command / Location | Status |
|---|----------|--------------------|--------|
| 1 | Benchmark lokal calisiyor | `python tools/benchmark_api.py` | [x] |
| 2 | benchmark.yml diff | `git diff .github/workflows/benchmark.yml` | [x] |
| 3 | Evidence file uretildi | `test -f evidence/sprint-12/benchmark.txt` | [x] |
| 4 | D-109 frozen | `docs/decisions/D-109-*` | [x] |
| 5 | D-110 frozen | `docs/decisions/D-110-*` | [x] |
| 6 | STATE.md updated | `docs/ai/STATE.md` | [x] |
| 7 | NEXT.md updated | `docs/ai/NEXT.md` | [x] |
| 8 | Kickoff doc committed | This file | [x] |
| 9 | Backend tests pass (458) | `cd agent && python -m pytest tests/ -v` | [x] |
| 10 | Frontend tests pass (29) | `cd frontend && npx vitest run` | [x] |
| 11 | CI 3/3 green | GitHub Actions | [x] |
| 12 | Benchmark summary truthful | No hardcoded false claims | [x] |
| 13 | GPT review recorded | `docs/ai/reviews/S17-REVIEW.md` | [x] |

---

## Exit Criteria

Sprint 17 complete only if:
1. All T17 tasks acceptance criteria PASS
2. D-109 and D-110 frozen
3. Evidence checklist 13/13
4. Mid + Final review gates PASS
5. GPT review HOLD patches applied
6. Backend 458+ tests pass, Frontend 29+ tests pass
7. Commit + push done

---

## Carry-Forward (not in Sprint 17 scope)

| Item | Source | Target |
|------|--------|--------|
| Backend physical restructure | S14A/14B | Sprint 18+ |
| Docker dev environment | S14B | Sprint 18+ |
| Live mission E2E | S14A waiver | Sprint 18+ |
| UIOverview + WindowList tools | D-102 | Sprint 18+ |
| Feature flag CONTEXT_ISOLATION_ENABLED | D-102 | Sprint 18+ |
| Live API + Telegram E2E | S16 WAIVER-1 | Sprint 18+ |
| Frontend Vitest component tests | S16 P-16.3 | Sprint 18+ |
| Alert "any" rule namespace scoping | S16 P-16.2 | Sprint 18+ |
| Jaeger deployment | S16 deferred | Sprint 18+ |
| Multi-user auth | D-104/D-108 | Sprint 18+ |
| Benchmark regression gate | D-109 deferred | Sprint 18+ |
