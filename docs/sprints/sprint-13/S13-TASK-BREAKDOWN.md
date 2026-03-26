# Sprint 13 — Task Breakdown (Phase 5.5: Stabilization + Structural Hardening) v5

**Repo path:** `docs/sprints/sprint-13/SPRINT-13-TASK-BREAKDOWN.md`
**Date:** 2026-03-26 (v5 — revised for Vezir Platform actual state)
**Phase:** 5.5 — Post-Phase 5 Stabilization
**Goal:** Zero technical debt (49 items), event-driven token governance, industry-standard monorepo.
**implementation_status:** not_started
**closure_status:** not_started
**Owner:** AKCA (operator)

---

## Current State (Post Session Report 2026-03-26)

| Component | State |
|-----------|-------|
| Vezir API (:8003) | Operational, 11 health components, 233 backend tests |
| Vezir UI (:3000) | Operational, rebrand complete, 29 frontend tests |
| Math Service (:9000) | Operational, 5 endpoints, 11 tests |
| Telegram Bot | Operational, @newbieakcabot |
| WMCP (:8001) | Operational, 18 tools |
| D-102 L3/L4/L5 | ✅ Inline — observability, budget, permissions working |
| D-102 L1/L2/EventBus | ⬜ Not done — Sprint 13 scope |

---

## Debt Registry (49 items, 0 deferred)

| Category | Items | Tasks |
|----------|-------|-------|
| D-102 EventBus + L1/L2 (critical) | 2 | 13.0 |
| Known issues (token ID, WSL, rework) | 3 | 13.1-13.3 |
| Doc structure (stale files, Turkish, backlog, protocol, READMEs, templates) | 9 | 13.4-13.5, 13.16 |
| Backend flat → layered | 7 | 13.6-13.9 |
| Frontend flat → feature-based | 10 | 13.10-13.13 |
| Runtime docs (bin, telegram, wsl, manifest) | 4 | 13.2, 13.14 |
| Monorepo (README, CONTRIBUTING, scripts, editorconfig, ports) | 6 | 13.15-13.16 |
| Tooling (pre-commit, coverage, RFC 7807, type sync, Docker, deps) | 7 | 13.9, 13.13, 13.17-13.18 |
| Legacy dashboard code removal | 1 | 13.4 |

---

## Task Table — 7 Tracks, 30 Tasks

### Track 0: Event-Driven Refactor (BLOCKER)

| Task | Description | Size |
|------|-------------|------|
| **13.0** | **EventBus + extract inline L3/L4/L5 into handlers + implement L1/L2 + enforcement + monitoring** | **XL** |

24 subtasks:
- 13.0.1-13.0.3: EventBus core, event catalog (28 types), correlation IDs
- 13.0.4: Token estimation utility
- 13.0.5-13.0.9: Handlers — AuditTrail, TokenLogger (extract), BypassDetector, ToolPermissions (extract), BudgetEnforcer (extract)
- 13.0.10-13.0.11: ApprovalGate, ToolExecutor (gated execution)
- 13.0.12-13.0.13: LLMExecutor (gated), ReportCollector (extract)
- 13.0.14-13.0.15: AnomalyDetector, MetricsExporter
- 13.0.16-13.0.17: **L1 StageResult isolation + L2 Tiered ContextAssembler**
- 13.0.18-13.0.19: StageTransitionHandler, ContextAssembler as handler
- 13.0.20: AgentRunner refactor — replace inline with bus.emit()
- 13.0.21: UIOverview + WindowList lightweight tools
- 13.0.22: Feature flags
- 13.0.23-13.0.24: Unit tests (all 13 handlers) + E2E validation (3 complex + 3 simple)

**Gate:** Developer stage ≤ 30K tokens. No bypass possible. All other tasks blocked until done.

### Track 1: Known Issues Fix

| Task | Description | Size |
|------|-------------|------|
| 13.1 | Token report ID mismatch — normalizer in mission_api.py | S |
| 13.2 | WSL naming: openclaw → vezir (dir rename + symlink + grep) | M |
| 13.3 | Rework limiter: complexity-based max (D-103) | M |

### Track 2: Doc Migration + Legacy Removal

| Task | Description | Size |
|------|-------------|------|
| 13.4 | Legacy dashboard code removal (D-097) + Turkish cleanup | M |
| 13.5 | Archive stale docs (28+ files) + telegram debug files | M |

### Track 3: Backend Restructure

| Task | Description | Size |
|------|-------------|------|
| 13.6 | Create backend/app/ package: core/, api/v1/, models/, schemas/, services/, middleware/, events/, handlers/, pipeline/, tools/ | L |
| 13.7 | create_app() factory + BaseSettings + lifespan + RFC 7807 | M |
| 13.8 | Migrate routes→api/v1/, logic→services/, types→models/+schemas/ | L |
| 13.9 | Monorepo integration: Math Service→backend/services/math/, Telegram Bot→backend/services/telegram/ | M |

### Mid-Review Gate

| Task | Description |
|------|-------------|
| 13.MID-REPORT | Mid-review report |
| 13.MID | GPT mid-review |
| 13.CLAUDE-MID | Claude mid-assessment |

Both PASS → Track 4+5 begin.

### Track 4: Frontend Restructure (after mid-gate)

| Task | Description | Size |
|------|-------------|------|
| 13.10 | Create feature structure: features/, components/ui/, api/, hooks/, types/, layouts/, lib/ | L |
| 13.11 | Migrate → features/ (dashboard, roles, approvals, missions) + barrel exports | L |
| 13.12 | API client layer + ErrorBoundary + @/ alias + vite proxy + generate-types.sh | M |
| 13.13 | Test cleanup + vitest coverage + Lighthouse regression + pre-commit hooks | M |

### Track 5: Tooling + Monorepo (after mid-gate)

| Task | Description | Size |
|------|-------------|------|
| 13.14 | Runtime/telegram/wsl/math READMEs + manifest.json path doc | S |
| 13.15 | Dev scripts: dev-backend, dev-frontend, dev-all, lint-all, test-all | M |
| 13.16 | Root README + CONTRIBUTING.md + .editorconfig + ports.md + sprint README backfill (7→12) + templates (5) + shared docs (2) | L |
| 13.17 | Backend test restructure: unit/+integration/+e2e/ + pyproject.toml + mypy + ruff + coverage | M |
| 13.18 | Dockerfile.dev + docker-compose.dev.yml (4 services: API, UI, Math, Telegram) | M |

### Track 6: Verification + Closure

| Task | Description | Size |
|------|-------------|------|
| 13.19 | Closure script update + full repo structure verify + ALL tests | M |
| 13.20 | Decision debt final: D-001→D-103, zero gaps | S |
| 13.REPORT | Final review report | S |
| 13.RETRO | Sprint retrospective | S |
| 13.FINAL | GPT final + Claude assessment | — |
| 13.CLOSURE | Closure summary + Phase 5.5 closure report | S |

**Implementation: 21 | Process: 8 | Known issues: 3 | Total: 30**

---

## Execution Timeline

```
Week 1:  Track 0 ████████████████ (13.0 EventBus — BLOCKER)
Week 2:  Track 1 ████ (13.1-13.3) + Track 2 ████ (13.4-13.5) + Track 3 ████████ (13.6-13.9)
         MID GATE ─────
Week 3:  Track 4 ████████████████ (13.10-13.13) + Track 5 ████████████████ (13.14-13.18)
Week 4:  Track 6 ████████████████ (13.19-13.CLOSURE)
```

---

## Evidence Checklist (30 mandatory)

| # | File | Task |
|---|------|------|
| 1 | eventbus-unit-tests.txt | 13.0 |
| 2 | handler-unit-tests.txt | 13.0 |
| 3 | enforcement-tests.txt | 13.0 |
| 4 | bypass-detection-test.txt | 13.0 |
| 5 | audit-trail-integrity.txt | 13.0 |
| 6 | token-count-before.txt | 13.0 |
| 7 | token-count-after.txt | 13.0 |
| 8 | complex-mission-runs.txt | 13.0 |
| 9 | simple-mission-runs.txt | 13.0 |
| 10 | correlation-id-trace.txt | 13.0 |
| 11 | token-report-id-fix.txt | 13.1 |
| 12 | wsl-rename-evidence.txt | 13.2 |
| 13 | rework-limiter-test.txt | 13.3 |
| 14 | turkish-scan.txt | 13.4 |
| 15 | archive-manifest.txt | 13.5 |
| 16 | backend-structure-before.txt | 13.6 |
| 17 | backend-structure-after.txt | 13.8 |
| 18 | backend-tests-after.txt | 13.17 |
| 19 | backend-coverage.txt | 13.17 |
| 20 | mypy-output.txt | 13.17 |
| 21 | ruff-output.txt | 13.17 |
| 22 | openapi-re-export.txt | 13.8 |
| 23 | frontend-structure-after.txt | 13.11 |
| 24 | frontend-tests-after.txt | 13.13 |
| 25 | frontend-coverage.txt | 13.13 |
| 26 | lighthouse-comparison.txt | 13.13 |
| 27 | docker-compose-test.txt | 13.18 |
| 28 | repo-structure-final.txt | 13.19 |
| 29 | decision-debt-final.txt | 13.20 |
| 30 | review-summary.md | 13.FINAL |

---

## Verification Commands

```bash
# EventBus + enforcement
grep "stage_input_tokens" logs/agent-runner.log | tail -5   # all ≤ 30K
grep "BYPASS" logs/audit-trail.jsonl                         # 0
python -m app.audit verify logs/audit-trail.jsonl            # chain intact

# Known issues
curl localhost:8003/api/missions/<id>/token-report | jq .status  # 200
ls /home/akca/.vezir/                                        # exists
grep "REWORK LIMIT" logs/agent-runner.log                    # appears if hit

# Backend
python -c "from app import create_app; print('OK')"
curl localhost:8003/api/v1/roles | jq length
pytest backend/tests/ -v --cov=app
mypy backend/app/ && ruff check backend/

# Frontend
find frontend/src/features/ -type d
npx tsc --noEmit && npx vitest run --coverage
grep -r "fetch(" frontend/src/features/ | grep -v api/ | wc -l  # 0

# Tooling
docker-compose -f docker-compose.dev.yml up -d && curl -sf localhost:8003/api/v1/health
bash scripts/test-all.sh
pre-commit run --all-files

# Decisions + structure
grep -c "^## D-" docs/ai/DECISIONS.md                       # 103
ls docs/ai/ | wc -l                                          # 3
find archive/stale/ -type f | wc -l                          # ≥ 28
bash tools/sprint-closure-check.sh 13
```

---

## Implementation Notes

| Task | Planned | Implemented | Why Different |
|------|---------|-------------|---------------|
| 13.0-13.20 | — | — | — |

## File Manifest

| File | Action | Task |
|------|--------|------|
| backend/app/events/ (bus, catalog, correlation) | Create | 13.0 |
| backend/app/handlers/ (13 handlers) | Create | 13.0 |
| backend/app/pipeline/ (runner, stage_result, context_assembler) | Create/Refactor | 13.0 |
| backend/app/tools/ (ui_overview, window_list) | Create | 13.0 |
| controller.py | Refactor (extract inline→handlers) | 13.0 |
| mission_api.py | Fix (token report ID) | 13.1 |
| WSL paths (~5 files) | Rename | 13.2 |
| docs/ai/DECISIONS.md | Modify (D-103) | 13.3 |
| Legacy dashboard files | Delete | 13.4 |
| archive/stale/ (28+ files) | Move | 13.5 |
| backend/app/ (layered tree) | Create | 13.6-13.8 |
| backend/services/math/ | Move | 13.9 |
| backend/services/telegram/ | Move | 13.9 |
| frontend/src/features/ | Create | 13.10-13.11 |
| frontend/src/api/*.ts | Create | 13.12 |
| .pre-commit-config.yaml | Create | 13.13 |
| scripts/ (5 dev scripts) | Create | 13.15 |
| CONTRIBUTING.md, .editorconfig | Create | 13.16 |
| docker-compose.dev.yml | Create | 13.18 |
| docs/templates/ (5 templates) | Create | 13.16 |
| docs/sprints/sprint-7..12/README.md (6 backfill) | Create | 13.16 |

---

## Next Step

**Produced:** SPRINT-13-TASK-BREAKDOWN v5
**Next actor:** Operator
**Action:** Sprint 12 kapat → D-102/D-103 confirm → GPT'ye kickoff packet gönder.
**Blocking:** Sprint 12 closure required.
