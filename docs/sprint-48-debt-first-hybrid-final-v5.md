# Sprint 48 — Debt-First Hybrid Scope (Final v5)

**Tarih:** 2026-03-30
**Kaynak:** Claude cross-review v1 → GPT HOLD v2 → Claude v3 → GPT retro v3 → Claude v4 → GPT HOLD v4 + GPT karşılaştırma + Claude mimari rapor cross-check → **Claude final v5**
**Model:** A (full closure — sprint-time evidence, all gates, no waivers)
**Class:** Governance + Runtime Contract + Data Normalization (hybrid)
**Phase:** 7
**Predecessor:** Sprint 47 closed (Session 20, 2026-03-30)
**Closure model:** Model A — D-105 compliant.

---

## Review Trail

| Round | Actor | Verdict | Key Delta |
|-------|-------|---------|-----------|
| 1 | Claude | Initial cross-review + task list | 28 task, 6 tier |
| 2 | GPT | HOLD — 5 blocking findings | Stale audit, blanket archive, runtime hot-path missing |
| 3 | Claude | Patched v3 — hybrid scope | Verification pack, normalizer consolidation, preflight |
| 4 | GPT | v3 retro-informed update | Read-model #1, schema normalization gap, B-107 coupling |
| 5 | Claude | v4 — schema normalization, D-133 strengthened | Anti-scope-creep, risks, dependencies, exit criteria |
| 6 | GPT | HOLD v4 — 3 blocking findings | Non-scope vs B-119, T-3 exit vs migration yasağı |
| 7 | GPT | Karşılaştırma analizi | OTel contract, RFC 9457, .pre-commit, security gap |
| 8 | Claude | Mimari rapor cross-validation | Python 3.14/React 19 repo reality check |
| 9 | Claude | **This document (v5)** | All 3 reviews integrated |

---

## Sprint 48 Goal

Canonical read-model consolidation, runtime contract hardening (policy context + timeout), field schema normalization, OTel telemetry attribute contract, local CI preflight alignment, ve policy engine contract freeze. Yeni feature yok — debt-first closure.

---

## Non-Scope (Anti-Scope-Creep)

Bu sprint'te aşağıdakiler **kesinlikle kapsam dışıdır:**

- B-107 policy engine **implementation** (sadece D-133 contract freeze — code yok)
- Yeni UI sayfası veya frontend feature
- Yeni backlog item **oluşturma veya close etme** (mevcut #168 ve #169 tüketimi hariç)
- B-026 DLQ retention, B-022 backup/restore, B-023 corrupted runtime recovery
- B-110 contract test pack, B-111 replay runner, B-112 dev sandbox
- Multi-user auth genişletme
- OpenAPI schema breaking change (additive-only per D-067)
- Sprint folder **path migration** (D-132 freeze/defer only — actual file rename/moves S49)
- Product feature (B-101→B-118 backlog item'ları)
- RFC 9457 error envelope implementation (audit only — carry-forward)
- MCP+A2A protocol desteği (roadmap item, S48 scope dışı)
- Hexagonal architecture / backend restructure (D-115: no restructure needed)
- React 19 migration (repo React 18.3.1, RSC kullanmıyor, acil risk yok)

**Scope creep detection rule:** G1'de normalizer dışı yeni file reader eklenmişse veya yeni API endpoint oluşturulmuşsa → scope creep, HOLD.

---

## Blocking Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| 1 | **48.3 XL effort patlaması** — normalizer consolidation + field normalization + OTel attribute contract 3 API refactor | G2 evidence eksik, sprint uzar | G1'de scope check: field normalization veya OTel attribute freeze kısmı S49'a defer edilebilir. Read-model consolidation öncelikli. |
| 2 | **Field normalization frontend breaking change** — `specialist→role`, `tool_call_count→toolCalls` değişimi frontend render kırabilir | Dashboard sayfaları boş render | `generated.ts` regenerate + vitest regression zorunlu. 5+ frontend test kırılırsa scope daralt. |
| 3 | **D-133 contract scope yetersizliği** — S49'da B-107 başlayınca amendment gerekebilir | S49 kickoff blocker | 48.5'te D-133'ü GPT cross-review'a gönder. Review PASS olmadan freeze etme. |
| 4 | **policyContext schema controller regression** — yeni field'lar mevcut logic bozabilir | Mission execution failure | Yeni field'lar optional + default değerli. Happy-path regression test dahil. |
| 5 | **Decision directory merge path drift** — `decisions/` → `docs/decisions/` taşıması DECISIONS.md referanslarını kırabilir | Stale reference'lar | Merge öncesi grep-based path audit zorunlu. Merge sonrası `check-stale-refs.py` çalıştır. |

---

## Dependencies

| Type | Dependency | Status |
|------|-----------|--------|
| Internal | Sprint 47 closed | ✅ Closed (Session 20) |
| Internal | D-128 risk classification (48.1 input) | ✅ Frozen (S35) |
| Internal | D-065 MissionNormalizer (48.3 base) | ✅ Frozen (S8), operational |
| Internal | D-106 JSON file store (48.5 storage model) | ✅ Frozen (S16) |
| Internal | D-067 schema freeze / additive-only (48.3 constraint) | ✅ Frozen (S8) |
| Internal | Sprint 15 OTel foundation (48.3c input) | ✅ 28/28 events, 17 metrics |
| Internal | `.pre-commit-config.yaml` (48.4 base) | ✅ Exists in repo (ruff, tsc, pytest) |
| Tooling | ruff, tsc, vitest, playwright | ✅ All installed |

---

## 48.0 — Verification + Cleanup Gate

Sprint 48 implementation başlamadan önce bu gate kapanmalı. Kickoff precondition.

### T-1: open-items.md Reconciliation

Her carry-forward item'ı current-main evidence ile doğrula:

| Item | Evidence | Status | Aksiyon |
|------|----------|--------|---------|
| Backend physical restructure | D-115 (S26): "no restructure needed" — frozen | **Superseded** | SİL |
| Docker dev environment | D-116 (S26): Dockerfile + compose frozen; S28 Jaeger/Grafana | **Partially resolved** | Güncelle: "Docker compose operational (D-116). Remaining: production image optimization" |
| UIOverview + WindowList tools | D-102 scope. CONTEXT_ISOLATION S43'te kapandı. | **Needs reaudit** | Repo grep → retire veya keep |
| D-102 validation criteria 3-8 | S40 multi-user isolation yapıldı | **Needs reaudit** | S40 scope'tan kalan criteria'yı çıkar |
| Alert "any" namespace scoping | S16'dan beri. Backlog issue yok. | **Still open** | `still_open / needs_backlog` etiketi bırak. Issue oluşturma S49'a defer. |
| Jaeger deployment | S28 docker-compose'a Jaeger eklendi | **Needs reaudit** | docker-compose.yml kontrol → güncelle |
| Multi-user auth | S40 partial. D-117 operational. | **Partially resolved** | Güncelle: "D-117 operational. Remaining: SSO, external auth, full RBAC" |
| PROJECT_TOKEN rotation/docs | AKCA-owned | **Still open** | Keep, owner=AKCA |

**Not:** B-119 issue oluşturma Sprint 48 scope'unda **değil** (non-scope ile tutarlı). Alert namespace scoping open-items.md'de `still_open / needs_backlog` olarak kalır, issue oluşturma S49'a defer.

**Exit criteria:** open-items.md'de superseded item yok. Her item etiketli. Resolved olanlar silinmiş. Non-scope ile çelişki yok.

### T-2: Test Count Reporting Contract — D-131

**Problem:** Handoff 935 (BE+FE+Playwright), NEXT.md 922 (BE+FE only), CLAUDE.md stale.

**Decision (D-131):**
- Canonical test total = backend + frontend + Playwright (3 bileşen)
- Format: `XXX backend + YYY frontend + ZZZ Playwright = NNN total`
- Tüm canonical doc'lar (handoff, STATE.md, NEXT.md, CLAUDE.md) bu formatı kullanır
- Sprint closure evidence'ında 3 ayrı satır: pytest, vitest, playwright

**Deliverable:** D-131 frozen + STATE.md / NEXT.md / CLAUDE.md tek seferlik güncelleme.

### T-3: Sprint Doc Path Audit (audit + cleanup only — NO broad migration)

**Problem:** Üç farklı sprint doc path:
1. `docs/sprints/sprint-{N}/` — S23-S32
2. `docs/sprint{N}/` — S33-S47
3. `docs/archive/sprints/sprint-{N}/` — S12-S22

**Task (strictly audit + duplicate cleanup):**
1. `docs/sprints/sprint-{23..32}/` ile `docs/archive/sprints/` arasında çakışma audit
2. Zaten archive'da olan **verified duplicate'ları** `docs/sprints/` altından sil
3. Non-duplicate path variants'ı document et (hangi path'te ne var)
4. D-132 naming standard kararı: freeze **veya** "defer to S49" olarak explicit kaydet

**Explicit constraint:** Bu task **path rename/migration yapmaz.** `docs/sprint{N}/` → `docs/sprints/sprint-{N}/` dönüşümü S49 scope'u. S48'de sadece duplicate temizliği ve durum tespiti.

**Exit criteria:**
- Verified duplicate'lar silinmiş
- Non-duplicate path variants documented
- D-132 frozen veya explicitly deferred
- **No broad path migration executed**

### T-8: Doc Fixes (grep-validated, not "minor")

**A) Decision directory merge:**
1. **Önce:** `grep -r "decisions/" docs/ tools/ .github/ CLAUDE.md` ile tüm referansları listele
2. Root `decisions/` → `docs/decisions/` merge
3. **Sonra:** `python tools/check-stale-refs.py` ile kırık referans kontrolü
4. Kırık referanslar varsa düzelt

**B) Missing formal records:**
- D-111/D-112/D-113/D-114 formal record dosyaları oluştur (compact format)

**C) D-126 gap:**
- DECISIONS.md'ye D-126 skip reason ekle (1 satır: "Reserved, not used — number gap between S33 and S34")

**Exit criteria:** Tek decision directory. `check-stale-refs.py` PASS. 4 formal record mevcut. D-126 açıklaması DECISIONS.md'de.

### 48.0 Gate Exit

Tüm T-1, T-2, T-3, T-8 DONE. Implementation track'ler başlayabilir.

---

## Track 1: Runtime Contract Hardening

### 48.1 — B-013 Richer policyContext (#168)

**Problem:** Mission controller'a giden policy context sığ. WMCP ulaşılamazlığı mission failure'ların ana nedeni olmuş (Session 20 retro) — degradation state policyContext'te yoksa policy engine bunu değerlendiremez.

**Scope:**
- policyContext schema genişletme:
  - `dependency_state`: per-dependency availability (MCP reachable/degraded/unreachable)
  - `source_freshness`: per-source age (normalizer metadata)
  - `risk_level`: D-128'den (computed at creation)
  - `retryability`: mission/stage retry eligibility
  - `interactive_capability`: tool/UI availability state
  - `tenant_limits`: guardrail thresholds (S30 D-121)
- Controller inject noktası: pre-stage evaluation hook
- Yeni field'lar **optional**, default değerli (mevcut mission'lar kırılmaz)
- Test: policyContext'in mission state + telemetry'ye yansıması + happy-path regression

**Backlog ref:** #168
**Decision dependency:** D-128 (frozen), D-133 (48.5'te freeze)

### 48.2 — B-014 timeoutSeconds in contract (#169)

**Problem:** Timeout konfigürasyonu dağınık. Per-mission, per-stage, per-tool timeout contract'ı yok.

**Scope:**
- Timeout hierarchy: global default → mission config → stage override → tool timeout
- Schema: `timeoutSeconds` field (mission + stage + tool level)
- Enforcement: controller'da stage-başı timeout check
- Default values: mission=3600s, stage=600s, tool=120s (configurable)
- Timeout exceed → `timed_out` state transition (S47 stale detector'ı formalize eder)
- Test: timeout exceed → doğru state transition + telemetry event

**Backlog ref:** #169

---

## 48.G1 — Mid Review Gate

**Checks:**
- 48.0 cleanup gate closed
- 48.1 policyContext tests green
- 48.2 timeout contract tests green
- No scope creep (no new file readers outside normalizer, no new endpoints)
- D-065 bypass audit: normalizer dışı `_load_file_missions` count (48.3 input)

---

## Track 2: Data Source Normalization + Observability Contract

### 48.3 — Canonical Mission Read-Model + Field Normalization + OTel Attribute Contract

**Bu task 3 sub-part içerir. G1'de scope check: eğer XL patlarsa Part B veya Part C S49'a defer edilebilir. Part A öncelikli.**

**Part A — Read-model consolidation (öncelikli):**

**Problem:** `cost_api.py`, `dashboard_api.py`, `agents_api.py` her biri kendi `_load_file_missions()` yazıyor. Bu D-065 ihlali.

1. Normalizer'a `list_missions_enriched()` method: cost, token, duration, stage detail dahil
2. `cost_api.py._load_file_missions()` → normalizer call
3. `dashboard_api.py._load_file_missions()` → normalizer call
4. `agents_api.py` provider/role data → normalizer veya config
5. MissionStore + file fallback logic'i normalizer'da tek yerde
6. Source precedence test: MissionStore populated → wins; empty → file fallback

**Part B — Field naming normalization:**

**Problem:** Controller/summary `specialist/tool_call_count/duration_ms` vs API `role/toolCalls/durationMs`.

1. Normalizer'da canonical field mapping:
   - `specialist` → `role`
   - `tool_call_count` → `toolCalls`
   - `duration_ms` → `durationMs`
   - `is_rework` → `isRework`
2. Mapping tek yerde: `normalizer.py`
3. Backend test: normalizer output always camelCase
4. Frontend: `generated.ts` regenerate + vitest regression

**Part C — OTel telemetry attribute contract (GPT karşılaştırma bulgusu):**

**Problem:** Sprint 15'te 28/28 event trace + 17 metrics delivered. Ama OTel attribute naming standardize değil. Yeni API'ler (cost, agent, health) kendi telemetry field'larını yazıyor. OTel GenAI Semantic Conventions (2025-02) ile alignment eksik.

1. Mevcut OTel attribute'ları audit: `agent/observability/` altındaki event/metric adları listele
2. Canonical attribute contract tanımla (internal doc, not full OTel GenAI migration):
   - Mission attributes: `vezir.mission.id`, `vezir.mission.status`, `vezir.mission.risk_level`
   - Stage attributes: `vezir.stage.role`, `vezir.stage.tool_calls`, `vezir.stage.duration_ms`
   - Provider attributes: `vezir.provider.name`, `vezir.provider.model`
3. Yeni API'lerdeki (cost/agent/health) telemetry event'lerini contract'a hizala
4. **Full OTel GenAI Semantic Conventions migration S49+** — S48'de sadece internal naming standardize

**Exit criteria:**
- `grep -r "_load_file_missions" agent/api/` → 0 outside normalizer
- `grep -r "tool_call_count\|duration_ms\|specialist" agent/api/` → only normalizer mapping
- OTel attribute contract document committed
- API response regression test PASS

### 48.4 — Local Preflight Alignment + Verification Strategy

**Problem (preflight):** `.pre-commit-config.yaml` repo'da **zaten var** (ruff-check, tsc-check, pytest-quick). Ama Sprint 48 debt scope'unda gereken ek check'ler (OpenAPI drift, import order) mevcut hook set'te yok.

**Problem (verification):** Browser automation kopmaları primary evidence'ı bloke etmemeli.

**Scope:**

**A) Mevcut pre-commit hook set'i genişlet:**
1. `.pre-commit-config.yaml`'a OpenAPI export drift check ekle:
   ```yaml
   - id: openapi-drift
     name: OpenAPI spec drift check
     entry: bash -c 'python tools/export_openapi.py && git diff --exit-code docs/api/openapi.json'
     language: system
     pass_filenames: false
   ```
2. `tools/preflight.sh` standalone script (CI'sız local kullanım için):
   ```
   ruff check agent/
   cd frontend && npx tsc --noEmit
   python tools/export_openapi.py && git diff --exit-code docs/api/openapi.json
   cd frontend && npx vitest run --reporter=dot
   ```
3. CLAUDE.md'ye preflight komutu ekle

**B) Verification strategy default:**
1. Sprint closure evidence primary = pytest + vitest + playwright + API raw output
2. Browser/UI manual test = supplementary, not blocking
3. GOVERNANCE.md'ye 1 paragraf ekle

**Exit criteria:** `bash tools/preflight.sh` exit 0. Pre-commit hook set Sprint 48 contract'ına hizalı. Verification default documented.

---

## Track 3: Policy Engine Contract

### 48.5 — Policy Engine Contract Freeze — D-133

**Sadece decision freeze — implementation yok.**

**D-133 scope (B-013 + B-014 + B-107 tightly coupled):**

1. **Architecture:** Rule-based, config-driven, fail-closed
2. **Evaluation point:** Controller, pre-stage (before specialist invocation)
3. **Input contract:**
   - `policyContext` (48.1): dependency state, risk level, source freshness, tenant limits
   - `timeoutConfig` (48.2): mission/stage/tool timeout hierarchy
   - `missionConfig`: goal, complexity, specialist list
   - `toolRequest`: requested tool + target + parameters
4. **Output contract:** `allow | deny | escalate | degrade`
   - `deny` → stage skip / mission abort (configurable)
   - `degrade` → fallback tool/provider
   - `escalate` → approval_wait state
5. **Rule format:** YAML-based, file-persisted (D-106 consistent)
6. **Default rules:**
   - WMCP unreachable → degrade
   - Risk=critical + no approval → escalate
   - Stage timeout exceed → timed_out
   - Budget exceed → deny new stages
7. **Storage:** `config/policies/` directory, rule-per-file
8. **S49 boundary:** D-133 = contract only. S49 = engine code + rule CRUD API + tests

**Exit criteria:** D-133 frozen. policyContext (48.1) + timeout (48.2) D-133 input contract ile uyumlu.

---

## Sprint-Level Acceptance Criteria

1. open-items.md'de superseded/stale carry-forward item sıfır
2. Tüm canonical doc'larda test count formatı `XXX BE + YYY FE + ZZZ Playwright = NNN total`
3. `agent/api/` altında normalizer dışı `_load_file_missions()` sıfır
4. Stage field naming tutarsızlığı normalizer mapping'de tek yerde çözülmüş
5. OTel attribute contract document committed
6. `tools/preflight.sh` exit 0 on clean repo
7. policyContext schema dependency state + risk level + timeout config taşıyor
8. Timeout hierarchy (mission/stage/tool) controller'da enforced
9. D-131, D-133 frozen; D-132 frozen veya explicit deferred
10. Verification strategy default documented

## Sprint-Level Exit Criteria

1. All acceptance criteria met with evidence
2. Full test suite green: 945+ total (935 baseline + new tests)
3. CI green (all workflows)
4. `tools/preflight.sh` exit 0
5. Evidence packet complete in `evidence/sprint-48/`
6. Retrospective committed with concrete output
7. GPT final review PASS

## Verification Commands

```bash
# Backend tests
cd agent && python -m pytest tests/ -v

# Frontend tests
cd frontend && npx vitest run

# TypeScript check
cd frontend && npx tsc --noEmit

# Lint
cd agent && python -m ruff check .

# Playwright
cd frontend && npx playwright test

# Preflight (all-in-one)
bash tools/preflight.sh

# Normalizer consolidation evidence
grep -r "_load_file_missions" agent/api/
grep -r "tool_call_count\|duration_ms\|specialist" agent/api/ --include="*.py"

# Decision directory merge validation
python tools/check-stale-refs.py
ls docs/decisions/D-{111,112,113,114,131,133}*.md

# Open-items cleanup
git diff docs/ai/state/open-items.md

# OTel attribute audit
grep -r "vezir\." agent/observability/ --include="*.py"
```

---

## Gates + Closure

### 48.G2 — Final Review Gate

| # | Evidence | Source |
|---|----------|--------|
| 1 | open-items.md diff (T-1) | `git diff docs/ai/state/open-items.md` |
| 2 | D-131 frozen (T-2) | `docs/decisions/D-131-test-reporting.md` |
| 3 | Doc path audit log (T-3) | `evidence/sprint-48/doc-path-audit.txt` |
| 4 | Decision directory merge + stale ref check (T-8) | `python tools/check-stale-refs.py` |
| 5 | policyContext tests (48.1) | `evidence/sprint-48/pytest-output.txt` |
| 6 | timeout contract tests (48.2) | `evidence/sprint-48/pytest-output.txt` |
| 7 | Normalizer consolidation (48.3a) | `grep -r "_load_file_missions" agent/api/` → 0 outside normalizer |
| 8 | Field mapping (48.3b) | `grep -r "tool_call_count\|duration_ms" agent/api/` → only normalizer |
| 9 | OTel attribute contract (48.3c) | `docs/shared/OTEL-ATTRIBUTE-CONTRACT.md` committed |
| 10 | Preflight script (48.4) | `evidence/sprint-48/preflight-output.txt` |
| 11 | D-133 frozen (48.5) | `docs/decisions/D-133-policy-engine.md` |
| 12 | Full test suite | Target: 945+ total |
| 13 | CI green | All workflows pass |

### 48.RETRO — Retrospective

Key questions:
1. open-items.md cleanup kaç resolved item ortaya çıkardı?
2. Normalizer consolidation sonrası API response regression var mı?
3. Field normalization frontend breaking change yarattı mı?
4. D-133 contract B-107 implementation'a yeterli mi?
5. OTel attribute contract GenAI conventions ile ne kadar uyumlu? Full migration ne zaman?
6. Local preflight developer adoption barrier var mı?

### 48.CLOSURE — Sprint Closure

---

## Decision Delta

| ID | Topic | When | Status |
|----|-------|------|--------|
| D-131 | Test count reporting contract | 48.0 (kickoff gate) | Proposed |
| D-132 | Sprint folder naming standard | 48.0: freeze or defer | Proposed (optional) |
| D-133 | Policy engine contract | 48.5 (before G2) | Proposed |

Max 3 decision. D-132 defer edilirse 2.

---

## Task Summary

| Task | Track | Tip | Effort | Backlog | Owner |
|------|-------|-----|--------|---------|-------|
| 48.0 T-1 | Cleanup Gate | housekeeping | M | — | Claude Code |
| 48.0 T-2 | Cleanup Gate | decision (D-131) | S | — | Claude (architect) |
| 48.0 T-3 | Cleanup Gate | audit + duplicate cleanup | M | — | Claude Code |
| 48.0 T-8 | Cleanup Gate | docs + grep-validated merge | M | — | Claude Code |
| 48.1 | Track 1: Runtime | feature | L | #168 | Claude Code |
| 48.2 | Track 1: Runtime | feature | M | #169 | Claude Code |
| 48.G1 | Gate | review | — | — | GPT (cross-review) |
| 48.3 | Track 2: Data+OTel | remediation + normalization | XL | — | Claude Code |
| 48.4 | Track 2: Quality | hook alignment + docs | S | — | Claude Code |
| 48.5 | Track 3: Policy | decision (D-133) | M | — | Claude (architect) + GPT |
| 48.G2 | Gate | review | — | — | GPT (cross-review) |
| 48.RETRO | Process | retro | — | — | Claude Code |
| 48.CLOSURE | Process | closure | — | — | Operator (AKCA) |

**Toplam:** 7 implementation/decision task + 6 gate/process = 13 item
**48.3 XL risk:** G1'de scope check — Part B (field) veya Part C (OTel) defer edilebilir.

**sprint-policy.yml entry:**
```yaml
48:
  forced_model: "A"
  reason: "Debt-first hybrid: governance cleanup + runtime contract + data normalization + OTel contract"
  require_previous_sprint_closed: true
  require_mid_review_task: true
  require_final_review_task: true
  max_open_decisions: 3
  require_evidence_checklist: true
  require_acceptance_criteria: true
  require_exit_criteria: true
```

---

## Execution Sequence

```
48.0 (T-1 → T-2 → T-3 → T-8)  ← cleanup gate, kickoff precondition
       ↓
48.1 (policyContext) ─┐
48.2 (timeout)       ─┤── parallel Track 1
       ↓              │
48.G1 ←───────────────┘
       ↓
48.3a (normalizer consolidation) ─┐
48.3b (field normalization)       ├── Track 2 (serial: a→b→c)
48.3c (OTel attribute contract)   │   [b or c deferrable at G1]
48.4  (preflight + verification)  ─┤── parallel with 48.3
48.5  (D-133 policy contract)    ─┘
       ↓
48.G2
       ↓
48.RETRO → 48.CLOSURE
```

---

## Output Files

| Task | Output |
|------|--------|
| T-1 | `docs/ai/state/open-items.md` (cleaned) |
| T-2 | `docs/decisions/D-131-test-reporting.md`, STATE.md, NEXT.md, CLAUDE.md |
| T-3 | `evidence/sprint-48/doc-path-audit.txt`, duplicate removals |
| T-8 | `docs/decisions/D-111-*.md` thru `D-114-*.md`, DECISIONS.md D-126 note, directory merge, stale-ref check |
| 48.1 | policyContext schema + controller hook + tests |
| 48.2 | timeout hierarchy + controller enforcement + tests |
| 48.3a | `agent/api/normalizer.py` (enriched), cost_api/dashboard_api/agents_api refactor |
| 48.3b | normalizer field mapping, `generated.ts` regenerate |
| 48.3c | `docs/shared/OTEL-ATTRIBUTE-CONTRACT.md` |
| 48.4 | `.pre-commit-config.yaml` (updated), `tools/preflight.sh`, GOVERNANCE.md update |
| 48.5 | `docs/decisions/D-133-policy-engine.md` |

---

## Carry-Forward (Sprint 49+)

| Item | Target | Priority | Source |
|------|--------|----------|--------|
| B-107 Policy engine implementation (D-133) | S49 | P2 | Backlog #162 |
| B-026 Dead-letter retention policy | S49-50 | P2 | Backlog #167 |
| B-022 Backup / restore | S50+ | P2 | Backlog #165 |
| B-023 Corrupted runtime recovery | S50+ | P2 | Backlog #166 |
| B-016 Task result artifact access | S50+ | P2 | Backlog #164 |
| B-110 Contract test pack | S50+ | P2 | Backlog #171 |
| B-111 Mission replay / fixture runner | S50+ | P2 | Backlog #172 |
| Sprint folder naming migration (if D-132 deferred) | S49 | P3 | T-3 defer |
| DECISIONS.md format normalization (### vs * style) | S49 | P3 | S37 audit F-07 |
| RFC 9457 error envelope standardization | S49 | P2 | GPT karşılaştırma |
| OTel GenAI Semantic Conventions full migration | S50+ | P3 | Claude mimari rapor |
| MCP+A2A interoperability roadmap | S50+ | P3 | Claude mimari rapor |
| Alert "any" namespace scoping (B-119 adayı) | S49 | P2 | open-items.md |
| CODEOWNERS + module boundary enforcement | S50+ | P3 | Claude mimari rapor |
| Security hardening: tool whitelisting, egress filtering | S50+ | P2 | Claude mimari rapor |

---

## Claude Mimari Rapor Cross-Validation

| Claude Bulgusu | Repo Reality | Sprint 48 Durumu |
|----------------|-------------|------------------|
| Python 3.14 P1 risk | `requires-python >=3.12`, `py312` config. Stable since Oct 2025. | **Acil değil** — dependency audit carry-forward |
| React 19 RCE P0 | React 18.3.1, RSC kullanmıyor | **Geçerli değil** — no RSC, no vulnerability |
| TypeScript strict mode P1 | `strict: true`, `noUncheckedIndexedAccess` zaten açık | **Zaten çözülmüş** |
| Pydantic v2 migration P1 | S43'te Pydantic V2 compat çalışması yapıldı | **Zaten çözülmüş** |
| Hexagonal architecture P1 | D-115 "no restructure needed" frozen (S26) | **Karar alınmış — restructure yok** |
| OTel GenAI conventions P1 | Sprint 15: 28/28 events, 17 metrics. GenAI naming yok. | **48.3c internal contract** + full migration carry-forward |
| MCP+A2A P1 | WMCP operational, A2A yok | **Carry-forward** — roadmap item |
| CODEOWNERS P2 | Yok | **Carry-forward** |
| RFC 9457 P2 | `APIError` schema var ama RFC 9457 compliant değil | **Carry-forward** — S49 audit |
| Module boundary enforcement P2 | Yok | **Carry-forward** |
| Security hardening (DASF) | D-128 risk, D-129 secret, D-130 TLS, D-117 auth | **Kısmen çözülmüş** — advanced items carry-forward |

---

## GPT Review Criteria Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Task listesi current-main ile doğrulanmış | ✅ T-1 verify/retire tablosu |
| 2 | Carry-forward maddeleri etiketli | ✅ T-1 tablosu |
| 3 | Governance-only değil, runtime debt içeren hibrit | ✅ Track 1 + Track 2 + Track 3 |
| 4 | open-items.md D-115/D-116 ile çelişmeyecek | ✅ T-1 explicit retire/update |
| 5 | Test count reporting contract | ✅ T-2 (D-131) |
| 6 | Read-model / normalizer explicit | ✅ 48.3a |
| 7 | Local preflight explicit | ✅ 48.4 (mevcut hook set genişletme) |
| 8 | Schema normalization covered | ✅ 48.3b |
| 9 | Policy engine coupling addressed | ✅ 48.5 D-133 genişletilmiş |
| 10 | Verification strategy documented | ✅ 48.4 Part B |
| 11 | Non-scope vs T-1 çelişki çözülmüş (GPT HOLD B1) | ✅ B-119 issue creation deferred, non-scope tutarlı |
| 12 | T-3 exit criteria non-scope ile uyumlu (GPT HOLD B2) | ✅ "No broad path migration" explicit |
| 13 | T-3 audit-only, not aggressive (GPT HOLD B3) | ✅ "Audit + duplicate cleanup only" |
| 14 | OTel attribute contract (GPT karşılaştırma) | ✅ 48.3c |
| 15 | .pre-commit zaten var — alignment not creation (GPT karşılaştırma) | ✅ 48.4 "mevcut hook set genişlet" |
| 16 | Decision directory merge risk addressed (GPT karşılaştırma) | ✅ T-8 grep-validated |
| 17 | Claude mimari rapor cross-validated | ✅ Cross-validation tablosu |
| 18 | Closure model declared (D-105) | ✅ Header |
| 19 | Output files per task | ✅ Output Files tablosu |
| 20 | Carry-forward with sources | ✅ 15 items with target + source |
