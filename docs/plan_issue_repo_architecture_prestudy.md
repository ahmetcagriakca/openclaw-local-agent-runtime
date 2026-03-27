# Ön Çalışma — Plan→Issue Otomasyonu + Repo/Dokümantasyon Standardizasyonu

**Tarih:** 2026-03-27  
**Amaç:**  
1. Plan freeze sonrası repoda otomatik issue oluşması  
2. Gereksiz dosya/doküman kalabalığının azaltılması  
3. Daha global-standard bir repo/workflow yapısına geçiş

---

## 1) Net öneri

En iyi mimari:

**GitHub-native work management + machine-readable plan metadata + minimal canonical docs**

Yani:

- **Plan** repoda yaşar ama makine-okunur hale getirilir
- **Issue/Sub-issue/Project tracking** GitHub üzerinde yaşar
- **Kalıcı bilgi** `docs/` altında yaşar
- **Geçici sprint planları / closure paketleri / raw evidence** aktif repoyu şişirmez
- **Eski sprint narrative ve raw evidence** archive repo veya artifact store’a gider

Bu yapı en dengeli çözüm:
- standarda yakın
- otomasyona açık
- repo kalabalığını azaltıyor
- issue ve sprint arasında iz sürmeyi kolaylaştırıyor

---

## 2) Hedef mimari

### A. Work Tracking Layer (GitHub)
Burada yaşamalı:
- parent issue
- sub-issues
- labels
- milestones
- project fields
- status lifecycle

### B. Plan Metadata Layer (Repo)
Burada yaşamalı:
- sprint plan metadata (`plan.yaml`)
- insan okuyacağı kısa kickoff özeti (`kickoff.md`)

### C. Canonical Knowledge Layer (Repo `docs/`)
Burada yaşamalı:
- architecture
- ADR / decision records
- runbook / how-to
- reference
- explanation
- current state

### D. Historical Archive Layer
Burada yaşamalı:
- eski sprint closure paketleri
- raw evidence
- stale handoffs
- old review packets
- process history / migration history
- completed sprint narrative’ler

---

## 3) Önerilen standart

Benim önerdiğim standard kombinasyonu:

### Work management
- GitHub Issues
- GitHub Sub-issues
- GitHub Projects automation
- Issue Forms

### Documentation taxonomy
- Divio style:
  - tutorials
  - how-to
  - reference
  - explanation

### Architecture decisions
- ADR style decision records
- kısa index + ayrı karar dosyaları

Bu kombinasyon pratik ve yaygın.
Tek başına çok akademik değil, çok da dağınık değil.

---

## 4) En iyi akış

## Akış: design -> freeze -> issue create -> implement -> verify -> close -> archive

### Step 1 — Plan hazırlanır
Repo içinde:
- `plans/sprint-18/plan.yaml`
- `plans/sprint-18/kickoff.md`

### Step 2 — Plan freeze edilir
- PR review
- D-XXX freeze gerekiyorsa tamamlanır
- scope netleşir

### Step 3 — Merge sonrası issue otomatik açılır
GitHub Action çalışır:
- parent sprint issue açar
- plan içindeki task’lardan sub-issue açar
- project’e ekler
- label/milestone atar
- issue body’ye repo plan linkini yazar

### Step 4 — Implementation issue üzerinden yürür
- progress GitHub issue/sub-issue tarafında akar
- repo içindeki sprint dosyası her küçük değişim için şişmez

### Step 5 — Closure
- review verdict
- evidence
- operator sign-off

### Step 6 — Archive
- sprint narrative / packet / raw evidence archive repo’ya veya artifact storage’a taşınır
- main repo’da sadece son aktif/son kapanan görünür

---

## 5) En kritik mimari kararı

## Karar:
**Markdown plan dosyasından otomatik parse etmeye çalışma.**

Brittle olur.

Onun yerine:

### İnsan için
- `kickoff.md`

### Makine için
- `plan.yaml`

Bu ayrım kritik.
Issue create otomasyonu YAML’den beslenmeli.
Markdown sadece okunur özet olmalı.

---

## 6) Önerilen repo yapısı

```text
.github/
  ISSUE_TEMPLATE/
    sprint-parent.yml
    sprint-task.yml
  workflows/
    issue-from-plan.yml
    sync-issue-links.yml
    close-sprint.yml

plans/
  sprint-18/
    plan.yaml
    kickoff.md
    review.md
    closure.md

docs/
  adr/
    ADR-109-benchmark-evidence-only.md
    ADR-110-doc-model.md
  explanation/
    architecture.md
    governance.md
  how-to/
    run-review.md
    create-sprint-plan.md
    operate-ci.md
  reference/
    state.md
    labels-and-status.md
    project-fields.md

archive/   # opsiyonel, ama tercihen ayrı repo
```

---

## 7) `plan.yaml` önerisi

```yaml
sprint: 18
phase: 6
title: "Phase 6 controlled continuation"
model: "A"
owner: "AKCA"
status:
  implementation_status: not_started
  closure_status: not_started

scope:
  in:
    - "Issue automation bootstrap"
    - "Project field standardization"
    - "Docs consolidation"
  out:
    - "New product feature expansion"

decisions:
  required:
    - "D-111"
  frozen: []

issue:
  parent_title: "Sprint 18 — Phase 6 controlled continuation"
  labels:
    - "sprint"
    - "phase-6"
    - "model-a"
  milestone: "Sprint 18"
  project: "Vezir Delivery"

tasks:
  - id: "T18-1"
    title: "Create issue automation workflow"
    type: "implementation"
    labels: ["automation", "github"]
    assignee: "ahmetcagriakca"
  - id: "T18-2"
    title: "Create project field schema"
    type: "design"
    labels: ["process", "projects"]
    assignee: "ahmetcagriakca"
  - id: "T18-G1"
    title: "Mid Review Gate"
    type: "review"
    labels: ["review", "gate"]

pass_criteria:
  - "Parent issue created automatically"
  - "Sub-issues created and linked"
  - "Project fields populated"
  - "Docs reduced to canonical set"
```

Bu format Markdown parse derdini bitirir.

---

## 8) GitHub issue mimarisi

### Parent issue
Her sprint için tek parent issue:
- amaç
- scope
- links
- checklist
- child issues

### Sub-issues
Task-level tracking issue olarak yaşar:
- T18-1
- T18-2
- T18-G1
- T18-G2

### Project fields
Önerilen minimum field set:
- Status: Todo / In Progress / In Review / Done / Blocked
- Type: Sprint / Task / Gate / Decision / Debt
- Sprint: 18
- Phase: 6
- Area: Docs / CI / Architecture / Tooling / Runtime / Frontend / Backend
- Model: A / B
- Priority: P0 / P1 / P2

### Labels
Önerilen minimum label set:
- `sprint`
- `gate`
- `review`
- `decision`
- `debt`
- `docs`
- `ci`
- `automation`
- `blocked`

---

## 9) Otomasyon önerisi

## Workflow 1 — `issue-from-plan.yml`
Trigger:
- `workflow_dispatch`
veya
- `push` on `plans/sprint-*/plan.yaml`

İş:
1. `plan.yaml` oku
2. parent issue oluştur
3. task’lar için issue/sub-issue oluştur
4. milestone/label/project ata
5. issue numaralarını bir output file’a yaz
6. opsiyonel: `kickoff.md` içine link ekle

### Teknik seçenekler
- GitHub CLI (`gh issue create`)
- REST API
- sub-issue API

Önerim:
- ilk sürümde `gh issue create`
- ikinci sürümde sub-issue API / project automation

---

## 10) Neden issue form da gerekli?

Plan→issue otomasyonu tek başına yeterli değil.

Ayrıca standart issue girişleri için:
- bug
- debt
- decision request
- task
- review request

şablonları da olmalı.

Böylece:
- plans automation başka bir kanal
- manual work intake başka bir kanal

ikisi de standart olur.

---

## 11) Doküman kalabalığını azaltmak için net kurallar

### Rule 1
`docs/` sadece kalıcı bilgi içinsin.

### Rule 2
Sprint narrative’leri sonsuza kadar main repo’da tutma.

### Rule 3
Raw evidence repo’ya gömülü birikmesin.
Tercih sırası:
1. CI artifact
2. archive repo
3. release asset
4. en son main repo

### Rule 4
Aynı truth iki dosyada yaşamamalı.

### Rule 5
Bir sprint için aktif repo’da tek canonical sprint paketi olsun.

### Rule 6
`STATE.md` ve `NEXT.md` kısa kalsın.
Bunlar history dump’a dönüşmemeli.

---

## 12) Archive repo tavsiyesi

Ayrı archive repo mantıklı.

### Main repo
- code
- active docs
- active plans
- ADR
- current state
- current sprint

### Archive repo
- old sprint packets
- old review packets
- raw evidence
- stale handoffs
- historical process docs
- completed phase bundles

Önerilen repo:
- `vezir-archive`

Bu repo:
- read-mostly
- write-rarely
- no active automation dependency

---

## 13) Global standard’a en yakın pratik model

Benim tavsiyem:

### Repo içinde
- code
- ADR
- Divio-style docs
- active sprint plan metadata

### GitHub içinde
- issues
- sub-issues
- projects
- automations
- labels
- milestones

### Archive repo’da
- history

Bu, bugünkü “docs everything” yaklaşımından daha standard.
Çünkü:
- work tracking GitHub-native
- docs docs olarak kalıyor
- plan otomasyonu korunuyor
- repo çöp olmuyor

---

## 14) Senin repo için özel öneri

Senin repo bugün zaten:
- sprint docs
- current state docs
- decisions
- review kültürü
- GitHub workflow’lar

barındırıyor.

Yani sıfırdan kurulum gerekmiyor.
Doğru hamle:
**rewrite değil, separation.**

### Koru
- STATE/NEXT/DECISIONS
- sprint review standardı
- operator close rule
- decision freeze disiplini

### Değiştir
- sprint metadata’yi YAML’ye taşı
- work tracking’i GitHub issue/sub-issue’ye taşı
- eski sprint narrative’leri archive repo’ya taşı
- docs’ı Divio/ADR yapısına ayır

---

## 15) Önerilen MVP

İlk iterasyonda sadece şunu yap:

### Sprint 18 MVP
1. `plans/sprint-18/plan.yaml`
2. `plans/sprint-18/kickoff.md`
3. `issue-from-plan.yml`
4. parent issue create
5. 2-3 sub-issue create
6. GitHub Project auto-add
7. label/milestone standardı
8. `docs/` cleanup phase-1

Bu yeter.
Bir anda full migration yapma.

---

## 16) Fazlandırma

### Phase A — Freeze
- canonical docs set
- label set
- project fields
- issue lifecycle
- archive boundary

### Phase B — Automate
- `plan.yaml`
- `issue-from-plan.yml`
- parent issue + sub-issues
- project auto-add

### Phase C — Clean
- docs consolidation
- archive repo
- old sprint packet moves
- evidence strategy

### Phase D — Normalize
- issue forms
- review request form
- decision request form
- docs taxonomy finalization

---

## 17) Karar

Benim net önerim bu:

### Hedef mimari
**Repo = source + canonical docs + active plans**  
**GitHub = execution tracking**  
**Archive repo = history**

### En iyi ilk adım
**Sprint 18 için `plan.yaml` + `issue-from-plan.yml` ile parent issue/sub-issue üretimi**

Bu en yüksek getirili hamle.
Çünkü aynı anda:
- standardizasyonu başlatır
- issue tabanlı takibi başlatır
- repo kalabalığını azaltacak zemini kurar

---

## 18) Çıktı

Bu ön çalışma sonunda önerilen implementasyon sırası:

1. plan metadata standardı
2. issue automation
3. project field standardı
4. docs cleanup
5. archive repo

Bu sıra doğru.
Tersi kaos üretir.
