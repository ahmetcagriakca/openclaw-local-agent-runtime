# Sprint 17 Kickoff — Phase 6 Controlled Start

## Metadata

| Field | Value |
|-------|-------|
| Sprint | 17 |
| Phase | 6 |
| Model | **A** (forced — D-105: max 2 consecutive Model B, S13-S16 were Model B) |
| implementation_status | not_started |
| closure_status | not_started |
| Owner | AKCA |
| Date | 2026-03-27 |

---

## Goal

Phase 6'nın ilk kontrollü sprint'i. CI pipeline'daki bozuk benchmark akışını düzeltmek, doc model ambiguity'yi gidermek ve carry-forward item'lardan ilk batch'i scope'a almak.

## Scope — IN

| # | Task | Deliverable |
|---|------|-------------|
| T17-1 | Benchmark workflow fix | `.github/workflows/benchmark.yml` — working path + evidence upload |
| T17-2 | CI evidence workflow modernize | `evidence.yml` sprint-17 uyumlu |
| T17-3 | Source-of-truth doc alignment | STATE.md + NEXT.md canonical marker, handoff rolü netleştirilmiş |
| T17-4 | Sprint 17 task freeze + evidence plan | Bu doküman, frozen |
| T17-G1 | Mid Review Gate | Contract/CI/doc drift check |
| T17-G2 | Final Review Gate | Evidence bundle + closure recommendation |

## Scope — OUT

- Yeni Phase 6 feature implementation (backend restructure, Docker, Playwright vb.)
- Parallel architecture expansion
- D-021→D-058 extraction (AKCA-assigned, non-blocking)
- Jaeger deployment

---

## Decisions

### D-109 (OPEN → freeze in this sprint)
**Problem:** Benchmark evidence-only mi, yoksa gerçek regression gate mi olacak?
**Current state:** `benchmark_api.py` sadece `benchmark.txt` üretiyor, JSON baseline yok, compare chain sahte.
**Recommendation:** Evidence-only olarak sabitle. Regression gate için JSON baseline + threshold mekanizması Phase 6'da ayrı sprint'te yapılsın.
**Owner:** Operator
**Deadline:** T17-1 tamamlanmadan

### D-110 (OPEN → freeze in this sprint)
**Problem:** Doc model — STATE.md/NEXT.md mi canonical, repo-native packet workflow mu?
**Current state:** STATE.md/NEXT.md = system state (canonical). handoffs/current.md = session context (supplementary). sprint-plan.sh/sprint-finalize.sh = tooling (available, not mandatory).
**Recommendation:** Dual model: STATE.md/NEXT.md canonical for system state, handoffs/current.md canonical for session continuity. Araçlar opsiyonel.
**Owner:** Operator
**Deadline:** T17-3 öncesi

---

## Task Breakdown

### T17-1: Benchmark Workflow Fix

**Goal:** CI benchmark job'u gerçekten çalışır hale getir.

**Changes:**
1. `cd agent &&` prefix kaldır — `benchmark_api.py` repo root `tools/` altında
2. Sahte `compare_benchmark.py` step'ini komple çıkar
3. Evidence verify step ekle: `test -f evidence/sprint-12/benchmark.txt`
4. Artifact upload step ekle

**Acceptance criteria:**
- [ ] `python tools/benchmark_api.py` repo root'tan çalışır
- [ ] `evidence/sprint-12/benchmark.txt` üretilir
- [ ] Compare step yok (D-109 freeze'e kadar)
- [ ] Artifact upload step mevcut

**Verification:**
```bash
python tools/benchmark_api.py
test -f evidence/sprint-12/benchmark.txt && echo "PASS" || echo "FAIL"
```

### T17-2: Evidence Workflow Modernize

**Goal:** evidence.yml'i Sprint 17+ uyumlu yap.

**Changes:**
1. Benchmark step ekle (evidence collection'a dahil)
2. Sprint parametresi ile evidence dizini oluşturma doğrula

**Acceptance criteria:**
- [ ] evidence.yml benchmark evidence toplar
- [ ] Sprint parametresi doğru çalışır

### T17-3: Source-of-Truth Doc Alignment

**Goal:** Canonical doc rollerini netleştir, çatışma kaldır.

**Changes:**
1. STATE.md'ye Sprint 17 entry ekle
2. NEXT.md'ye Sprint 17 status ekle
3. Her iki dosyada doc model rolünü açıkça belirt

**Acceptance criteria:**
- [ ] STATE.md Sprint 17'yi yansıtıyor
- [ ] NEXT.md Phase 6 Sprint 17 listeliyor
- [ ] Doc hierarchy net: STATE.md (system) > handoffs/current.md (session)

### T17-4: Sprint Plan + Evidence Freeze

**Goal:** Bu dokümanı freeze et, evidence checklist kesinleştir.

**Acceptance criteria:**
- [ ] Kickoff doc committed
- [ ] Evidence checklist complete
- [ ] Review gates embedded

---

## Mid Review Gate (T17-G1)

**Required checks:**
- [ ] benchmark.yml fix committed ve lokal test geçiyor
- [ ] D-109 frozen (benchmark strategy)
- [ ] D-110 frozen (doc model)
- [ ] CI truth = claimed truth (no false green)

**Exit rule:** T17-3 ve T17-4 bu gate pass etmeden başlamaz.

---

## Final Review Gate (T17-G2)

**Required checks:**
- [ ] Tüm T17 task'ları acceptance criteria PASS
- [ ] Evidence bundle complete (aşağıdaki checklist)
- [ ] STATE.md ve NEXT.md güncel
- [ ] Handoff current.md güncel
- [ ] No open blockers

**Exit rule:** Bu gate olmadan `closure_status` closed olamaz.

---

## Evidence Checklist

| # | Evidence | Command / Location | Status |
|---|----------|--------------------|--------|
| 1 | Benchmark lokal çalışıyor | `python tools/benchmark_api.py` | [ ] |
| 2 | benchmark.yml diff | `git diff .github/workflows/benchmark.yml` | [ ] |
| 3 | Evidence file üretildi | `test -f evidence/sprint-12/benchmark.txt` | [ ] |
| 4 | D-109 frozen | `docs/decisions/D-109-*` | [ ] |
| 5 | D-110 frozen | `docs/decisions/D-110-*` | [ ] |
| 6 | STATE.md updated | `docs/ai/STATE.md` | [ ] |
| 7 | NEXT.md updated | `docs/ai/NEXT.md` | [ ] |
| 8 | Kickoff doc committed | This file | [ ] |
| 9 | Backend tests pass | `cd agent && python -m pytest tests/ -v` | [ ] |
| 10 | Frontend tests pass | `cd frontend && npx vitest run` | [ ] |

---

## Exit Criteria

Sprint 17 complete only if:
1. All T17 tasks acceptance criteria PASS
2. D-109 and D-110 frozen
3. Evidence checklist 10/10
4. Mid + Final review gates PASS
5. Backend 458+ tests pass, Frontend 29+ tests pass
6. Commit + push done

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
