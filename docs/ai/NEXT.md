# Next Steps — Vezir Platform

**Last updated:** 2026-04-06
**Current:** Phase 9 active. Sprint 71 closed. S72 session protocol enforcement next.

---

## Sprint 71 — Intake Gate + Workflow Writer Enforcement (CLOSED)

**Model:** A (full closure) | **Class:** Governance
**Scope:** D-142 intake gate tool, issue-from-plan writer contract, project-auto-add field init (code-ready, blocked by PAT credential), governance patch
**Issues:** #350 (parent), #351-#355 (tasks)
**Milestone:** Sprint 71
**Tests:** 1555 backend + 217 frontend + 13 Playwright + 102 root = 1887 total (+40 root new)
**New files:** `tools/task-intake.py`, `tests/test_task_intake.py`
**Modified:** `.github/workflows/issue-from-plan.yml`, `.github/workflows/project-auto-add.yml`, `docs/ai/GOVERNANCE.md`, `docs/ai/state/open-items.md`
**PRs:** #356 (implementation)
**Review:** GPT PASS (R8)
**Evidence:** `evidence/sprint-71/`

---

## Sprint 70 — Validator/Closer Drift Hardening (CLOSED)

**Model:** A (full closure) | **Class:** Governance
**Scope:** Validator fail-closed derivation, closer exact merge evidence, doc/state hygiene
**Issues:** #347
**Milestone:** Sprint 70
**Tests:** 1555 backend + 217 frontend + 13 Playwright + 60 root = 1845 total (+21 root new)
**New files:** `tests/test_close_merged_issues.py`
**Modified:** `tools/project-validator.py`, `tools/close-merged-issues.py`, `tests/test_project_validator.py`, `docs/sprints/sprint-70/plan.yaml`, `config/capabilities.json`
**PRs:** #348 (implementation), #349 (GPT review patches)
**Review:** GPT PASS (R4)
**Evidence:** `evidence/sprint-70/`

---

## Sprint 69 — Operating Model Freeze + State Drift Guard (CLOSED)

**Model:** A (full closure) | **Class:** Governance
**Scope:** D-142 intake-to-sprint operating model freeze, state-sync --check governed doc consistency
**Issues:** #346
**Milestone:** Sprint 69
**Tests:** 1555 backend + 217 frontend + 13 Playwright + 10 state-sync = 1795 total
**New files:** `docs/decisions/D-142-intake-to-sprint-operating-model.md`, `tests/test_state_sync.py`, `docs/sprints/sprint-{69,70,71,72}/plan.yaml`
**Modified:** `tools/state-sync.py` (--check mode), `docs/ai/DECISIONS.md`, `docs/ai/STATE.md`, `docs/ai/NEXT.md`, `docs/ai/handoffs/current.md`, `docs/ai/state/open-items.md`
**Decision:** D-142 frozen
**Review:** Claude Code PASS, GPT PASS (R3)
**Evidence:** `evidence/sprint-69/`

---

## Sprint 67 — Enforcement Chain Doc + Mission Replay CLI (CLOSED)

**Model:** B (lightweight closure) | **Class:** Documentation + DevEx
**Scope:** B-145 enforcement chain documentation, B-146 mission replay CLI tool
**Issues:** #333, #334
**Milestone:** S67
**Tests:** 1555 backend + 217 frontend + 13 Playwright = 1785 total (no change — Model B)
**New files:** `docs/shared/ENFORCEMENT-CHAIN.md`, `tools/replay-mission.py`
**Modified:** `docs/ai/GOVERNANCE.md` (section 15 enforcement chain cross-ref)
**Review:** Claude Code PASS, GPT PASS (R3)
**Evidence:** `evidence/sprint-67/`

---

## Sprint 65 — Mission Startup Recovery + Plugin Mutation Auth Boundary (CLOSED)

**Model:** A (full closure) | **Class:** Architecture + Security
**Scope:** B-141 mission startup recovery, B-142 plugin mutation auth boundary
**Issues:** #329, #330
**Milestone:** S65
**Sequence:** 65.1 (startup recovery) → G1 → 65.2 (plugin auth) → G2 → RETRO → CLOSURE
**Evidence:** `evidence/sprint-65/`

---

## Sprint 64 — Controller Extraction Phase 1 + Hard Budget Enforcement (CLOSED)

**Model:** A (full closure) | **Class:** Product + Security
**Scope:** B-139 controller extraction phase 1, B-140 hard per-mission budget enforcement
**Tests:** 1494 backend + 217 frontend + 13 Playwright = 1724 total
**Issues:** #327, #328
**New tests:** +40 (persistence 11, recovery 8, budget 21)
**New files:** `agent/mission/persistence_adapter.py`, `agent/mission/recovery_engine.py`, `config/policies/token-budget-exceeded.yaml`, `config/policies/token-budget-warning.yaml`, `agent/tests/test_persistence_adapter.py`, `agent/tests/test_recovery_engine.py`, `agent/tests/test_budget_enforcement.py`
**Modified:** `agent/mission/controller.py` (delegation), `agent/mission/policy_context.py` (budget fields), `agent/mission/policy_engine.py` (budget conditions), `agent/api/schemas.py` (budget in API), `agent/api/normalizer.py`
**Review:** Claude Code PASS, GPT PASS (R2)
**Evidence:** `docs/evidence/sprint-64/`

---

## Sprint 63 — Controller Decomposition Boundary + Budget Ownership (CLOSED)

**Model:** A (full closure) | **Class:** Architecture (design-only)
**Scope:** B-137 controller decomposition boundary freeze, B-138 budget enforcement ownership design
**Tests:** 1454 backend + 217 frontend + 13 Playwright = 1684 total (unchanged, design sprint)
**Issues:** #325, #326
**New tests:** 0 (design-only)
**New files:** `docs/sprints/sprint-63/responsibility-map.md`, `docs/sprints/sprint-63/D-139-controller-decomposition.md`, `docs/sprints/sprint-63/budget-data-flow.md`, `docs/sprints/sprint-63/budget-enforcement-draft.yaml`
**Modified:** `docs/ai/DECISIONS.md` (D-139 added)
**Decision:** D-139 frozen
**Review:** Claude Code PASS, GPT PASS (R2)

---

## Sprint 62 — Approval FSM Wiring + Decision Drift + Auth Quarantine (CLOSED)

**Model:** A (full closure) | **Class:** Product
**Scope:** B-134 approval FSM controller wiring, B-135 decision drift cleanup, B-136 auth session quarantine
**Tests:** 1454 backend + 217 frontend + 13 Playwright = 1684 total
**Issues:** #322, #323, #324
**New tests:** +28
**Review:** Claude Code PASS, GPT PASS (R1)

---

## Sprint 61 — Approval Timeout=Deny + Escalation FSM (CLOSED)

**Model:** A (full closure) | **Class:** Governance
**Scope:** D-138 Approval timeout=deny semantics + escalation FSM
**Tests:** 1426 backend + 217 frontend + 13 Playwright = 1656 total (0 TS errors)
**Issues:** #321
**New tests:** +31
**New files:** `agent/tests/test_approval_fsm.py`, `docs/decisions/D-138-approval-timeout-escalation-fsm.md`
**Modified:** `agent/services/approval_store.py` (canonical FSM, escalation, persist-on-decide)
**Decision:** D-138 frozen
**Review:** Claude Code PASS, GPT PASS (R2)

---

## Sprint 60 — WSL2 <-> PowerShell Bridge Contract (CLOSED)

**Model:** A (full closure) | **Class:** Security
**Scope:** D-137 WSL2 <-> PowerShell bridge contract freeze + enforcement
**Tests:** 1395 backend + 217 frontend + 13 Playwright = 1625 total (0 TS errors) (D-131)
**Issues:** #320
**New tests:** +19
**New files:** `agent/tests/test_bridge_contract.py`, `docs/decisions/D-137-wsl2-powershell-bridge-contract.md`
**Modified:** `agent/services/approval_service.py`, `agent/telegram_bot.py`, `agent/api/health_api.py` (legacy WSL fallbacks removed)
**Decision:** D-137 frozen (WSL2 <-> PowerShell bridge contract)
**Review:** Claude Code PASS, GPT PASS (R1)

---

## Sprint 59 — Plugin Marketplace / Discovery (CLOSED)

**Model:** A (full closure) | **Class:** Product
**Scope:** B-118 plugin marketplace store + discovery, plugin lifecycle API, plugin installer + hot-reload (D-136)
**Tests:** 1376 backend + 217 frontend + 13 Playwright = 1606 total (0 TS errors) (D-131)
**Issues:** #317, #318, #319
**New tests:** +76
**New files:** `agent/services/plugin_marketplace.py`, `agent/services/plugin_installer.py`, `agent/api/plugins_api.py`, `agent/tests/test_plugin_marketplace.py`
**Modified:** `agent/api/server.py` (+1 router: plugins)
**Decision:** D-136 frozen (plugin marketplace + installer contract)
**Review:** Claude Code PASS, GPT Pending

---

## Sprint 58 — Knowledge Layer + Multi-tenant + WMCP Cred (CLOSED)

**Model:** A (full closure) | **Class:** Product + Security
**Scope:** B-114 knowledge/connector input layer, B-116 multi-tenant isolation, B-010 WMCP credential replacement
**Tests:** 1300 backend + 217 frontend + 13 Playwright = 1530 total (0 TS errors) (D-131)
**Issues:** #314, #315, #316
**New tests:** +90
**New files:** `agent/services/knowledge_store.py`, `agent/api/knowledge_api.py`, `agent/auth/tenant.py`, `agent/api/tenant_api.py`, `agent/services/wmcp_credential_manager.py`, `agent/api/wmcp_credential_api.py`
**Modified:** `agent/api/server.py` (+3 routers: knowledge, tenant, wmcp-credential)
**Review:** Claude Code PASS

---

## Sprint 57 — Secret Rotation + Allowlist + Grafana Pack (CLOSED)

**Model:** A (full closure) | **Class:** Security + Operations
**Scope:** B-007 automatic secret rotation, B-009 multi-source allowlist, B-117 Grafana dashboard pack
**Tests:** 1210 backend + 217 frontend + 13 Playwright = 1440 total (0 TS errors) (D-131)
**Issues:** #311, #312, #313
**New tests:** +82
**New files:** `agent/services/secret_rotation.py`, `agent/api/secret_rotation_api.py`, `agent/services/allowlist_store.py`, `agent/api/allowlist_api.py`, `agent/api/metrics_api.py`, `config/grafana/*.json`, `tools/grafana_setup.py`
**Modified:** `agent/api/server.py` (+3 routers: secret_rotation, allowlist, metrics)
**Review:** Claude Code PASS

---

## Sprint 56 — Task Dir Retention + .bak Cleanup + Intent Mapping (CLOSED)

**Model:** A (full closure) | **Class:** Cleanup + Product
**Scope:** B-027 task directory retention, B-028 stale .bak file cleanup, B-019 intent mapping refinement
**Tests:** 1128 backend + 217 frontend + 13 Playwright = 1358 total (0 TS errors) (D-131)
**Issues:** #308, #309, #310
**New tests:** +71
**New files:** `agent/persistence/mission_retention.py`, `agent/api/retention_api.py`, `tools/cleanup_bak.py`, `agent/mission/intent_mapper.py`
**Modified:** `agent/api/server.py` (+retention router)
**Review:** Claude Code PASS

---

## Sprint 55 — Audit Export + Dynamic Source + Heredoc Cleanup (CLOSED)

**Model:** A (full closure) | **Class:** Operations + DevEx + Cleanup
**Scope:** B-115 audit export/compliance bundle, B-018 dynamic sourceUserId (D-134), B-025 bootstrap heredoc reduction
**Tests:** 1057 backend + 217 frontend + 13 Playwright = 1287 total (0 TS errors) (D-131)
**Issues:** #305, #306, #307
**New tests:** +65
**New files:** `tools/audit_export.py`, `agent/api/audit_export_api.py`, `agent/auth/source_user_resolver.py`, `tools/helpers/policy_check.py`, `docs/decisions/D-134-source-user-identity.md`
**Modified:** `agent/api/mission_create_api.py` (D-134 resolver), `agent/api/server.py` (+audit router), `tools/sprint-finalize.sh` (heredoc removed)
**Review:** Claude Code PASS + GPT PASS (5 rounds)

---

## Sprint 54 — Audit Export + Dynamic Source + Heredoc Cleanup (DEFERRED)

**Not implemented. All 3 tasks carried forward to Sprint 55 (#305, #306, #307).**
**Issues:** #302, #303, #304 (closed as deferred)
**Milestone:** Sprint 54 (#29, closed)

---

## Sprint 53 — Docs-as-Product + Policy Context + Timeout Contract (CLOSED)

**Model:** A (full closure) | **Class:** DevEx + Operations
**Scope:** B-113 docs-as-product pack, B-013 richer policyContext, B-014 timeoutSeconds in contract
**Tests:** 992 backend + 217 frontend + 13 Playwright = 1222 total (0 TS errors) (D-131)
**Issues:** #299, #300, #301
**New tests:** +75
**New files:** `tools/generate_docs.py`, `docs/generated/api-reference.md`, `docs/generated/architecture.md`, `docs/generated/onboarding.md`, `agent/tests/test_generate_docs.py`, `agent/tests/test_timeout_contract.py`
**Modified:** `agent/mission/policy_context.py` (+CallerIdentity, resourceTags, environment), `agent/mission/policy_engine.py` (+3 condition types), `agent/api/policy_api.py` (+context-schema), `agent/api/mission_create_api.py` (+timeout fields), `agent/api/schemas.py` (+timeoutConfig), `agent/api/normalizer.py`
**Review:** Claude Code GO + GPT submitted

## Sprint 52 — Recovery + Replay + Seed Demo (CLOSED)

**Model:** A (full closure) | **Class:** DevEx + Operations
**Scope:** B-023 corrupted runtime recovery, B-111 mission replay/fixture runner, B-112 local dev sandbox/seeded demo
**Tests:** 917 backend + 217 frontend + 13 Playwright = 1147 total (0 TS errors) (D-131)
**Issues:** #296, #297, #298
**New tests:** +46
**New files:** `tools/recovery.py`, `tools/replay.py`, `tools/seed_demo.py`, `agent/api/recovery_api.py`, `agent/api/replay_api.py`
**Modified:** `agent/api/server.py` (2 new routers), `docs/api/openapi.json` (82 endpoints)

## Sprint 51 — Contract Testing + Data Safety + Artifact Access (CLOSED)

**Model:** A (full closure) | **Class:** DevEx + Operations
**Scope:** B-110 contract test pack, B-022 backup/restore, B-016 artifact access API
**Tests:** 871 backend + 217 frontend + 13 Playwright = 1101 total (0 TS errors) (D-131)
**Issues:** #293, #294, #295
**New tests:** +50
**New files:** `tools/contract_check.py`, `tools/backup.py`, `tools/restore.py`, `agent/api/backup_api.py`, `agent/api/artifacts_api.py`, `docs/api/openapi-baseline.json`
**Modified:** `agent/api/server.py` (2 new routers), `docs/api/openapi.json` (76 endpoints)

## Sprint 50 — API Hardening + DevEx + Governance Debt (CLOSED)

**Model:** A (full closure) | **Class:** API + DevEx + Governance
**Scope:** Policy write API, B-109 scaffolding CLI, D-132 folder migration, RFC 9457 error envelope
**Tests:** 821 backend + 217 frontend + 13 Playwright = 1051 total (0 TS errors) (D-131)
**Issues:** #289, #290, #291, #292
**Decisions:** D-132 now frozen (folder migration)
**New tests:** +33

## Sprint 49 — Policy Engine + Operational Hygiene (CLOSED)

**Model:** A (full closure) | **Class:** Product + Operational Hygiene
**Scope:** B-107 policy engine implementation (D-133), B-026 DLQ retention policy, B-119 alert namespace scoping
**Tests:** 788 backend + 217 frontend + 13 Playwright = 1018 total (0 TS errors) (D-131)
**Issues:** #286, #287, #288
**New files:** `agent/mission/policy_engine.py`, `agent/api/policy_api.py`, `config/policies/*.yaml` (5 files), 3 test files
**Modified:** `controller.py` (pre-stage hook), `dlq_store.py` (retention), `alert_engine.py` (user_id scoping), `server.py` (policy router)
**Review:** GPT PASS + Claude Chat GO

## Sprint 48 — Debt-First Hybrid (CLOSED)

**Model:** A (full closure) | **Class:** Governance + Runtime Contract + Data Normalization
**Scope:** Cleanup gate (open-items, D-131, doc path audit, decision merge), runtime contract (B-013 policyContext, B-014 timeout), normalizer consolidation, OTel attribute contract, preflight alignment, D-133 policy engine contract
**Tests:** 736 backend + 217 frontend + 13 Playwright = 966 total (0 TS errors) (D-131)
**Issues:** #276-#284
**Decisions:** D-131 (test reporting), D-133 (policy engine contract), D-132 deferred

## Sprint 47 — Frontend Quality & UX Hardening (CLOSED)

**Model:** A (implementation) | **Class:** Governance/Quality
**Scope:** 12 issues — accessibility, responsive, state badge, templates, toast, stale cleanup, telemetry, format utils, URL sync, health API
**Tests:** 705 backend + 217 frontend + 13 Playwright = 935 total (0 TS errors) (D-131)
**Issues:** #264-#275

## Sprint 46 — B-105 Cost Dashboard + B-108 Agent Health (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Cost/outcome dashboard API (3 endpoints), Agent health/capability API (4 endpoints), 2 new frontend pages, sidebar nav
**Tests:** +23 backend (705 total), +20 frontend (215 total)
**Issues:** #160, #163

## Sprint 45 — B-104 Template Parameter UI (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Frontend template UI — API client, TemplatesPage, ParameterForm, RunTemplateModal
**Commits:** `ac4c90c`
**Tests:** +27 frontend (195 total)
**Issue:** #259

## Sprint 44 — CI/CD & Repo Quality (CLOSED)

**Model:** A (implementation) | **Class:** Governance/Quality
**Scope:** CI fix, security findings, coverage, PR template, dependabot
**Commits:** `ca6ebac`, `db0249e`, `101e2ef`, `3c9dcdf`, `1e99524`, `5d3ef32`, `68e4dcc`, `2026ebe`, `6f8350d`, `c967198`, `d671ea8`, `805f853`, `42b73b2`, `52549b4`, `2d4e37c`

## Sprint 43 — Tech Debt Eritme (CLOSED)

**Model:** A (implementation) | **Class:** Governance/Quality
**Scope:** Pydantic V2 compat, bare pass cleanup, frontend tests, branch prune, CONTEXT_ISOLATION flag
**Commits:** `bd8e591`, `64c3de8`, `05bb074`, `7cc272c`
**Tests:** +99 new (863 total: 682+168+13)
**Issue:** #234
**Review:** GPT conversation `69c9984b`

## Sprint 42 — Runner Resilience (B-106) (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** DLQ, exponential backoff, circuit breaker, poison pill detection, auto-resume
**Commits:** `cae2bfa`, `4ab8ceb`, `6ca6af5`
**Tests:** +51 new (669 total)
**Review:** PASS (2nd round) — GPT conversation `69c97bad`

## Sprint 41 — Integrity Hardening / Source-of-Truth Stabilization (CLOSED)

**Model:** A (implementation) | **Class:** Governance
**Scope:** D-071 atomic write remediation, DECISIONS.md index repair, closure drift checker
**Review:** PASS — `docs/ai/reviews/S41-REVIEW.md`
**Commits:** `685acaf`, `1e69d84`, `f39562a`, `e36d192`

## Sprint 40 — Multi-user Isolation + Auth Boundaries (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Backend isolation (D-102), multi-user auth boundary (D-104/D-108), frontend isolation tests
**Review:** PASS (2nd round) — `docs/ai/reviews/S40-REVIEW.md`
**Commits:** `855613f`

## Sprint 39 — Approval Inbox + Live E2E + CI + Benchmark (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** B-102 approval inbox, live mission E2E, Playwright CI, benchmark gate D-109
**Review:** PASS (2nd round) — `docs/ai/reviews/S39-REVIEW.md`
**Commits:** `9b23d4a`, `5cf3817`, `38364b2`, `d1e01ac`, `1628642`

## Sprint 38 — Telegram Fix + Scheduled Missions + Presets (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Telegram bridge fix, B-101 scheduled execution, B-103 presets/quick-run
**Review:** PASS (2nd round) — `docs/ai/reviews/S38-REVIEW.md`
**Tests:** +69 new (21 telegram + 34 schedules + 14 presets)

## Carry-Forward

| Item | Source | Status |
|------|--------|--------|
| PROJECT_TOKEN rotation | S23 retro | AKCA-owned |
| Frontend Vitest component tests | S16 | Ongoing quality lane |
| CONTEXT_ISOLATION feature flag | D-102 | Unassigned |
| D-102 validation criteria 3-8 | D-102 | Unassigned |
| Alert namespace scoping | S16 | Done (S49, B-119) |
| Multi-user auth | D-104/D-108 | Unassigned |
| Jaeger deployment | S16 | Unassigned |
| UIOverview + WindowList tools | D-102 | Unassigned |
| Docker dev environment | S14B | Unassigned |
| Backend physical restructure | S14A/14B | Unassigned |

## Decision Debt

- D-021→D-058 extraction (AKCA-assigned, non-blocking)
