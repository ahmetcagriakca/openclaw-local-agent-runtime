# Stash Platform — Documentation & Governance Bootstrap Prompt

> **Bu dokümanı Claude Opus'a ver. Tüm kurguyu sıfırdan kuracak.**
> **Dil:** Türkçe konuşma, İngilizce teknik terimler.

---

## Görev

Sen bir yazılım mimarısın. Stash platformunun **governance, sprint tracking, task tracking ve dokümantasyon altyapısını sıfırdan kuracaksın**. Platform 44 farklı repo ve bunları yöneten 1 ana repo'dan oluşuyor.

**Çalışma modelin:**
- Otonom çalış, her milestone'da commit at
- Her task somut output üretmeli — sohbet-only yasak
- Blocker'ları önce çöz
- "Sonra netleştirilecek" bırakma — her şey şimdi netleşsin
- Mevcut mimariyi "clean rewrite" ile değiştirme

---

## FAZA 0 — Keşif ve Analiz (İLK YAPILACAK)

### 0.1 — Repo Envanteri

Ana repo'daki tüm referansları tara. Her repo için:

```markdown
| # | Repo Adı | Dil/Framework | Son Commit | Test Var mı | CI/CD Var mı | README | Durum |
```

**Aksiyonlar:**
1. Ana repo'da submodule, config, manifest, docker-compose, package.json, build dosyalarını tara — 44 repo'nun listesini çıkar
2. Her repo'ya git clone/fetch ile son commit tarihini al
3. Her repoda test dosyası var mı kontrol et (pytest, jest, vitest, go test, vb.)
4. CI/CD pipeline var mı kontrol et (.github/workflows/, .gitlab-ci.yml, Jenkinsfile, vb.)
5. README.md var mı ve ne kadar güncel

**Output:** `docs/ai/REPO-INVENTORY.md` — 44 satırlık tablo + özet istatistikler

### 0.2 — Quick-Win Analizi

Repo envanterinden şunları belirle:

1. **Düşük asılı meyveler:** README eksik, CI yok, test yok, lint yok — 1 sprint'te düzeltilebilir
2. **Kritik riskler:** Son 6 ayda commit almamış repolar, bağımlılık güvenlik açıkları, kırık build'ler
3. **Standartlaştırma fırsatları:** Ortak pattern'ler (logging, error handling, config) eksik olan repolar
4. **Bağımlılık haritası:** Hangi repo hangisine bağımlı (import/dependency graph)

**Output:** `docs/ai/QUICK-WIN-ANALYSIS.md` — kategorize edilmiş, önceliklendirilmiş liste

### 0.3 — Teknoloji Matrisi

```markdown
| Dil/Framework | Repo Sayısı | Repolar | Build Tool | Test Framework |
```

**Output:** `docs/ai/TECH-MATRIX.md`

---

## FAZA 1 — Dokümantasyon Altyapısı Kurulumu

Ana repo'da şu yapıyı oluştur:

```
docs/
├── ai/
│   ├── STATE.md              # Canonical system state (tek kaynak)
│   ├── NEXT.md               # Roadmap + carry-forward
│   ├── DECISIONS.md          # Frozen architectural decisions (D-XXX format)
│   ├── GOVERNANCE.md         # Sprint governance kuralları
│   ├── BACKLOG.md            # Fazlara ayrılmış açık iş listesi
│   ├── REPO-INVENTORY.md     # Faza 0'dan gelen envanter
│   ├── QUICK-WIN-ANALYSIS.md # Faza 0'dan gelen analiz
│   ├── TECH-MATRIX.md        # Teknoloji matrisi
│   ├── handoffs/
│   │   └── current.md        # Session-to-session context transfer
│   ├── state/
│   │   └── open-items.md     # Active blockers + carry-forward tracker
│   └── reviews/
│       └── README.md         # Review process kuralları
├── shared/
│   ├── BRANCH-CONTRACT.md    # Branch naming convention
│   └── GOVERNANCE.md         # Cross-sprint shared rules
├── sprints/
│   └── sprint-1/             # İlk sprint klasörü (kickoff'ta oluşur)
└── archive/
    └── sprints/              # Kapatılan sprintler buraya taşınır
```

### 1.1 — STATE.md (Canonical System State)

```markdown
# Current State

**Last updated:** {tarih}
**Active phase:** Sprint 0 — Discovery
**Doc model:** Bu dosya system state için tek kaynaktır. Session context `docs/ai/handoffs/current.md`'de.

---

## System Status

| Component | Repo | Status | Notes |
|-----------|------|--------|-------|
(44 repo + ana repo satırları)

## Completed Phases

| Phase | Scope | Status |
|-------|-------|--------|

## Test Evidence

| Sprint | Tests | Notes |
|--------|-------|-------|

## Architectural Decisions

X frozen decisions (D-001→D-XXX). See `docs/ai/DECISIONS.md`.
```

**Kurallar:**
- Her sprint kapanışında güncellenir
- Source precedence: code > raw evidence > frozen decisions > task breakdown > narrative

### 1.2 — DECISIONS.md (Frozen Decisions)

```markdown
# Architectural Decisions

| ID | Phase | Status | Decision |
|----|-------|--------|----------|
| D-001 | 0 | Frozen | {ilk karar} |
```

**Kurallar:**
- Her karar `D-XXX` formatında, sıralı numara
- Frozen = değiştirilemez (reopening için: evidence + operator onayı gerekli)
- Silent drift yasak — her değişiklik burada kayıt altında

**İlk kararlar (bootstrap sırasında freeze et):**
- D-001: Ana repo governance hub'dır, 44 repo bağımsız deploy edilir
- D-002: Sprint tracking ana repo'da yapılır
- D-003: Türkçe konuşma, İngilizce teknik terimler
- D-004: Her task somut output üretir, chat-only yasak
- D-005: Branch-per-task zorunlu, main korumalı
- (Keşif sırasında çıkan kararları da ekle)

### 1.3 — GOVERNANCE.md (Sprint Kuralları)

```markdown
# Sprint Governance

## Status Model

Her sprint iki eksende takip edilir:
- `implementation_status`: not_started | in_progress | done
- `closure_status`: not_started | evidence_pending | review_pending | closed

## Source Hierarchy

1. Repo code (git log, dosyalar)
2. Raw evidence (test output, CI log)
3. Frozen decisions (DECISIONS.md)
4. Task breakdown (SPRINT-N-TASK-BREAKDOWN.md)
5. Sprint report / narrative
6. Chat summary (en düşük)

## Closure Models

### Model A — Full Evidence (implementation sprint'leri)
- Her task: code committed + tests passing + evidence produced
- Waiver yok
- Mid-review + final review zorunlu

### Model B — Lightweight (docs-only veya analiz sprint'leri)
- Retroactive evidence kabul edilir
- Waiver'lar dokümante edilir
- Max 2 ardışık Model B sprint

## Task DONE Definition

5/5 kriter karşılanmalı:
1. Code committed (veya doc committed)
2. Tests passing (varsa)
3. Evidence produced (artifact)
4. Implementation notes updated
5. File manifest updated

## Review Protocol

- Pre-sprint → Mid-sprint → Final review (3 gate)
- Verdict: PASS | HOLD | FAIL
- HOLD = patch gerekli, tekrar review
- FAIL = re-scope gerekli
- closure_status=closed yalnızca operator tarafından set edilir

## Commit Rules

- 1 task = minimum 1 commit
- Format: "Sprint N Task X.Y: <description>"
- Mega-commit yasak
- Her sprint commit + push ile biter

## Retrospective

- Her sprint sonunda RETRO zorunlu
- Eksik retro = closure engeli
```

### 1.4 — BACKLOG.md

```markdown
# Backlog

## Phase 1 — Quick Wins (keşiften gelen)

| ID | Item | Repo(s) | Notes |
|----|------|---------|-------|
| B-001 | ... | ... | ... |

## Phase 2 — Standardization

| ID | Item | Repo(s) | Notes |
|----|------|---------|-------|

## Phase 3 — Deep Improvements

| ID | Item | Repo(s) | Notes |
|----|------|---------|-------|

## Cleanup (phase gate yok)

| ID | Item | Notes |
|----|------|-------|
```

### 1.5 — open-items.md

```markdown
# open-items.md — Active State Tracker

**Last updated:** {tarih}

## Active Blockers

| # | Item | Owner | Sprint |
|---|------|-------|--------|

## Carry-Forward

| Item | Source | Decision |
|------|--------|----------|

## Active Hard Rules

1. ...

## Decision Debt

| Item | Since | Priority |
|------|-------|---------|

## Next Sprint

**Sprint 1 — {scope}**
- Status: NOT STARTED
- Kickoff gate: OPEN
```

### 1.6 — handoffs/current.md

```markdown
# Session Handoff — {tarih} (Session 1)

**Platform:** Stash Platform
**Operator:** AKCA

## Session Summary

{Faza 0 keşif özeti}

## Current State

- Phase: 0 (Discovery)
- Last closed sprint: —
- Decisions: X frozen
- Sprint 1: NOT STARTED

## Open Items

{Keşiften gelen açık maddeler}
```

### 1.7 — reviews/README.md

```markdown
# Review Process

## File Naming

- `S{N}-REVIEW.md` — Sprint closure review
- `S{N}-KICKOFF-REVIEW.md` — Sprint kickoff gate

## Verdict Definitions

- **PASS:** Closure'a uygun. Blocker yok.
- **HOLD:** Patch gerekli. Patch sonrası tekrar review.
- **FAIL:** Re-scope gerekli. Sprint bu haliyle kapatılamaz.

## Flow

1. Evidence topla → review packet oluştur
2. Review verdict al (PASS/HOLD/FAIL)
3. HOLD ise patch uygula, tekrar review'a gönder
4. PASS sonrası operator closure onayı
5. closure_status=closed yalnızca operator set eder
```

### 1.8 — BRANCH-CONTRACT.md

```markdown
# Branch Naming Contract

**Effective:** Sprint 1+
**Owner:** AKCA (Operator)

## Pattern

```
sprint-N/tN.M-slug
```

- `N` = sprint numarası
- `M` = task numarası
- `slug` = kebab-case kısa açıklama

## Rules

1. Branch-per-task zorunlu (implementation task'ları için)
2. Main'e direkt commit yasak — tüm değişiklikler PR ile
3. Gate task'ları (G1, G2, RETRO, CLOSURE) branch-exempt
4. Merge: gate PASS sonrası, operator onaylı
5. Force push yasak
```

### 1.9 — CLAUDE.md (Root Level)

```markdown
# CLAUDE.md — Stash Platform

## Project

Stash — 44 repo'lu multi-repo platform.
1 ana governance repo + 44 servis/kütüphane repo'su.

## Key Files

| File | Purpose |
|------|---------|
| `docs/ai/STATE.md` | Canonical system state |
| `docs/ai/NEXT.md` | Roadmap + carry-forward |
| `docs/ai/DECISIONS.md` | Frozen decisions (D-XXX format) |
| `docs/ai/GOVERNANCE.md` | Sprint governance kuralları |
| `docs/ai/BACKLOG.md` | Open backlog items |
| `docs/ai/REPO-INVENTORY.md` | 44 repo envanteri |
| `docs/ai/handoffs/current.md` | Session context |
| `docs/ai/state/open-items.md` | Active blockers + carry-forward |
| `docs/ai/reviews/` | Review verdicts |
| `docs/shared/BRANCH-CONTRACT.md` | Branch naming convention |
| `docs/shared/GOVERNANCE.md` | Cross-sprint shared rules |

## Build & Test

(Keşif sonrası doldurulacak — her repo'nun build/test komutu)

## Hard Rules

- Türkçe konuşma, İngilizce teknik terimler
- Her task somut output üretir. Chat-only yasak.
- Blocker'lar önce çözülür.
- Frozen decision'lar D-XXX formatında.
- Her sprint commit + push ile biter.
- closure_status=closed = yalnızca operator.
- Mevcut mimariyi "clean rewrite" ile değiştirme.

## Session Protocol

1. `docs/ai/handoffs/current.md` + `docs/ai/state/open-items.md` oku
2. Otonom çalış, milestone'larda commit at
3. Session sonunda handoff + open-items güncelle

## Do Not

- Mevcut mimariyi "clean rewrite" ile değiştirme
- "Done" deme, verification evidence olmadan
- "Sonra netleştirilecek" bırakma
- 44 repo'yu tek seferde değiştirmeye çalışma — sprint bazlı ilerle
```

---

## FAZA 2 — Sprint Altyapısı

### 2.1 — Sprint Klasör Yapısı

Her sprint için:

```
docs/sprints/sprint-N/
├── SPRINT-N-TASK-BREAKDOWN.md    # Task'ların canonical kaynağı
├── plan.yaml                      # Automation index
├── issues.json                    # Task → Issue → PR mapping (auto-generated)
├── S{N}-KICKOFF.md               # Kickoff review notu
├── S{N}-FINAL-REVIEW.md          # Final review verdict
├── S{N}-RETROSPECTIVE.md         # Sprint retro (closure şartı)
└── artifacts/                     # Evidence dosyaları
    └── closure-check-output.txt
```

### 2.2 — plan.yaml Şeması

```yaml
sprint: 1
phase: 1
title: "Quick Wins — Batch 1"
model: "A"

authority:
  source_of_truth: "SPRINT-1-TASK-BREAKDOWN.md"
  automation_index: "plan.yaml"
  generated_files:
    - "issues.json"

issue:
  parent_title: "[S1] Quick Wins — Batch 1"
  labels: ["sprint", "sprint-1"]
  milestone: "Sprint 1"

tasks:
  - id: "1.1"
    title: "Task açıklaması"
    type: "implementation"
    track: 1
    branch_name: "sprint-1/t1.1-slug"
    labels: []
  - id: "1.G1"
    title: "Gate 1 — Mid Review"
    type: "gate"
    track: 1
    branch_exempt: true
  - id: "1.G2"
    title: "Gate 2 — Final Review"
    type: "gate"
    track: 1
    branch_exempt: true
  - id: "1.RETRO"
    title: "Retrospective"
    type: "process"
    track: 1
    branch_exempt: true
  - id: "1.CLOSURE"
    title: "Sprint Closure"
    type: "process"
    track: 1
    branch_exempt: true
```

### 2.3 — TASK-BREAKDOWN.md Şeması

```markdown
# Sprint N — {Başlık}

**Model:** A/B
**Phase:** {faz numarası}
**Status:** implementation_status=not_started, closure_status=not_started

## Metadata

| Field | Value |
|-------|-------|
| Sprint | N |
| Task Count | X impl + 4 gates |
| Branch Pattern | sprint-N/tN.M-slug |

## Track 1 — {Track Adı}

### Task N.1 — {Başlık}
- **Type:** implementation
- **Branch:** sprint-N/tN.1-slug
- **Acceptance Criteria:**
  1. ...
  2. ...
- **Output:** {somut artifact}

### Task N.2 — {Başlık}
...

## Gates

### G1 — Mid Review
- Tüm Track 1 task'ları tamamlandığında
- Review packet oluştur, verdict al

### G2 — Final Review
- Tüm task'lar ve G1 patches tamamlandığında
- Final verdict: PASS gerekli

### RETRO — Retrospective
- Ne iyi gitti, ne kötü gitti, ne değişmeli
- Eksik retro = closure engeli

### CLOSURE — Sprint Closure
- closure_status=closed (yalnızca operator)
- Commit + push zorunlu
```

---

## FAZA 3 — İlk Sprint Kickoff

Faza 0 keşif ve Faza 1 altyapı tamamlandıktan sonra:

1. `QUICK-WIN-ANALYSIS.md`'den en yüksek impact/effort oranına sahip 3-5 item seç
2. `SPRINT-1-TASK-BREAKDOWN.md` oluştur
3. `plan.yaml` oluştur
4. `S1-KICKOFF.md` yaz
5. İlk decision'ları freeze et (D-001→D-00X)
6. `STATE.md`, `NEXT.md`, `open-items.md`, `handoffs/current.md` güncelle
7. Commit + push

---

## Execution Sırası (ZORUNLU)

```
FAZA 0: Keşif
  ├── 0.1: Repo envanteri (REPO-INVENTORY.md)
  ├── 0.2: Quick-win analizi (QUICK-WIN-ANALYSIS.md)
  └── 0.3: Teknoloji matrisi (TECH-MATRIX.md)
  → Commit: "Phase 0: Discovery — repo inventory + quick-win analysis"

FAZA 1: Altyapı
  ├── 1.1: STATE.md
  ├── 1.2: DECISIONS.md (ilk kararlarla)
  ├── 1.3: GOVERNANCE.md
  ├── 1.4: BACKLOG.md (keşiften populate)
  ├── 1.5: open-items.md
  ├── 1.6: handoffs/current.md
  ├── 1.7: reviews/README.md
  ├── 1.8: BRANCH-CONTRACT.md
  ├── 1.9: CLAUDE.md
  └── 1.10: docs/shared/GOVERNANCE.md
  → Commit: "Phase 1: Documentation infrastructure bootstrap"

FAZA 2: Sprint altyapısı
  ├── 2.1: Sprint klasör yapısı (docs/sprints/)
  ├── 2.2: Sprint 1 plan.yaml
  └── 2.3: Sprint 1 task breakdown
  → Commit: "Phase 2: Sprint 1 kickoff — {scope}"

FAZA 3: Sprint 1 execution
  ├── Task'ları sırayla yap
  ├── Her task sonrası commit
  ├── G1 mid-review
  ├── G2 final review
  ├── RETRO
  └── CLOSURE
  → Commit: "Sprint 1 closed — {verdict}"
```

---

## Multi-Repo Özel Kurallar

44 repo'lu bir platformda ek kurallar:

1. **Ana repo = governance hub.** Sprint tracking, decisions, state hep ana repo'da.
2. **Repo bazlı task'lar.** Her task hangi repo(lar)da çalışılacağını belirtir.
3. **Cross-repo değişiklikler** tek sprint'te max 5 repo. Daha fazlası = sprint split.
4. **Her repo'nun kendi README'si** olmalı — ana repo'dan link verilir.
5. **Dependency graph** güncel tutulmalı — hangi repo hangisine bağımlı.
6. **Repo health dashboard** STATE.md'de — her repo'nun son durumu tek tabloda.
7. **Repo grupları** tanımlanabilir (frontend, backend, infra, libs, vb.) — sprint scope bu gruplara göre daraltılabilir.
8. **44 repo'yu aynı anda değiştirme** — sprint bazlı, max 5 repo/sprint.

---

## Kritik Hatırlatmalar

- **Otonom çalış.** Her adımda onay bekleme, milestone'larda commit at.
- **Her commit'te push.** Sprint commit + push ile biter.
- **Evidence-first.** "Done" demek için test output, CI log, veya artifact göster.
- **Keşif önce.** Analiz etmeden optimizasyon yapma.
- **Incremental.** 44 repo'yu tek seferde değil, sprint bazlı ele al.
- **Handoff her zaman güncel.** Session sonunda `handoffs/current.md` güncelle.
- **Decision'lar frozen.** Bir karar verildiğinde DECISIONS.md'ye yaz, D-XXX formatında.
