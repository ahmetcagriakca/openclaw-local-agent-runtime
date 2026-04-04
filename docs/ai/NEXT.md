# Next Steps — Vezir Platform

**Last updated:** 2026-04-04
**Current:** Phase 7 active. Sprint 58 closed. Sprint 59 pending.

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
