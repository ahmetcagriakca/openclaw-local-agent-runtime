# open-items.md — Active State Tracker

**Last updated:** 2026-04-06
**Updated by:** Claude Code (Session 49 — S73)

---

## Active Blockers

| # | Item | Owner | Sprint |
|---|------|-------|--------|
| — | *(none)* | — | — |

---

## Carry-Forward (Phase 7)

| Item | Source | Status |
|------|--------|--------|
| PROJECT_TOKEN rotation/docs | S23 retro | AKCA-owned, non-blocking |
| Docker dev environment | D-116 (S26) | Partially resolved: docker-compose operational (D-116, Jaeger included S28). Remaining: production image optimization |
| ~~Alert "any" namespace scoping~~ | S16 P-16.2 | Done: S49 B-119 (#288) |
| Multi-user auth | D-104/D-108/D-117 | Partially resolved: D-117 operational (S27), backend isolation (S40). Remaining: SSO, external auth, full RBAC |

### Retired (Sprint 48 T-1 Reconciliation)

| Item | Source | Reason |
|------|--------|--------|
| Backend physical restructure | S14A/14B | Superseded by D-115 (S26): "no restructure needed" — frozen decision |
| UIOverview + WindowList tools | D-102 | D-102 CONTEXT_ISOLATION closed (S43). Tools exist only in observability test stubs — no production implementation planned |
| D-102 validation criteria 3-8 | D-102 amendment | S40 multi-user isolation addressed remaining criteria. CONTEXT_ISOLATION feature flag done (S43). No open criteria remain. |
| Jaeger deployment | S16 deferred | Resolved: Jaeger in docker-compose.yml (S28). Deployment operational. |
| Telegram bridge fix | S33+ deferred | Done: S38 task 38.1 |
| B-101 Scheduled mission execution | Backlog P1 | Done: S38 task 38.2 |
| B-103 Mission presets / quick-run | Backlog P1 | Done: S38 task 38.3 |
| B-102 Full approval inbox UI | Backlog P1 | Done: S39 task 39.1 |
| Live mission E2E | S14A waiver | Done: S39 task 39.2 |
| Playwright live API test in CI | S22 retro | Done: S39 task 39.3 |
| Benchmark regression gate D-109 | S22 retro | Done: S39 task 39.4 |
| Feature flag CONTEXT_ISOLATION_ENABLED | D-102 | Done: S43 task 43.5 |
| Frontend Vitest component tests | S16 P-16.3 | Done: S43 (+86), S46 (+20), S47 (+2) = 217 total |
| Stale running missions | S47 audit | Done: S47 normalizer stale detector (>1h → timed_out) |
| WMCP hard-fail on missions | S47 root cause | Done: S46 fix — graceful MCP degradation |

---

## Decision Debt

| Item | Since | Priority |
|------|-------|---------|
| D-021→D-058 extraction to DECISIONS.md (38 Phase 4 decisions) | Sprint 8 kickoff | AKCA-assigned, non-blocking |

---

## Completed This Phase

| Sprint | Scope | Status |
|--------|-------|--------|
| Sprint 42 | B-106 Runner Resilience (DLQ, backoff, circuit breaker, auto-resume) | CLOSED (G2 PASS) |
| Sprint 43 | Tech Debt Eritme (Pydantic, bare pass, frontend tests, feature flag) | CLOSED |
| Sprint 44 | CI/CD & Repo Quality | CLOSED |
| Sprint 45 | B-104 Template Parameter UI (last P1) | CLOSED |
| Sprint 46 | B-105 Cost Dashboard + B-108 Agent Health View + 4 bugfixes | CLOSED |
| Sprint 47 | Frontend Quality & UX Hardening (12 issues: a11y, responsive, toast, stale, format) | CLOSED |
| Sprint 48 | Debt-First Hybrid (governance + runtime contract + data normalization + OTel) | CLOSED |
| Sprint 49 | Policy Engine + Operational Hygiene (B-107, B-026, B-119) | CLOSED |
| Sprint 50 | API Hardening + DevEx + Governance Debt (policy write API, B-109, D-132, RFC 9457) | CLOSED |
| Sprint 51 | Contract Testing + Data Safety + Artifact Access (B-110, B-022, B-016) | CLOSED |
| Sprint 52 | Recovery + Replay + Seed Demo (B-023, B-111, B-112) | CLOSED |
| Sprint 53 | Docs-as-Product + Policy Context + Timeout Contract (B-113, B-013, B-014) | CLOSED |
| Sprint 54 | Audit Export + Dynamic Source + Heredoc Cleanup (B-115, B-018, B-025) | DEFERRED (not implemented, tasks → S55) |
| Sprint 55 | Audit Export + Dynamic Source + Heredoc Cleanup (B-115, B-018, B-025) | CLOSED |
| Sprint 56 | Task Dir Retention + .bak Cleanup + Intent Mapping (B-027, B-028, B-019) | CLOSED |
| Sprint 57 | Secret Rotation + Allowlist + Grafana Pack (B-007, B-009, B-117) | CLOSED |

| Sprint 58 | Knowledge Layer + Multi-tenant + WMCP Cred (B-114, B-116, B-010) | CLOSED |
| Sprint 59 | Plugin Marketplace / Discovery (B-118, D-136) | CLOSED |
| Sprint 60 | WSL2 <-> PowerShell Bridge Contract (D-137) | CLOSED |
| Sprint 61 | Approval Timeout=Deny + Escalation FSM (D-138) | CLOSED |
| Sprint 62 | Approval FSM Wiring + Decision Drift + Auth Quarantine (B-134, B-135, B-136) | CLOSED |
| Sprint 63 | Controller Decomposition Boundary + Budget Ownership Design (B-137, B-138, D-139) | CLOSED |
| Sprint 64 | Controller Extraction Phase 1 + Hard Budget Enforcement (B-139, B-140) | CLOSED |
| Sprint 65 | Mission Startup Recovery + Plugin Mutation Auth Boundary (B-141, B-142) | CLOSED |
| Sprint 66 | Persistence Boundary ADR + Tool Reversibility Metadata (B-143, B-144, D-140) | CLOSED |
| Sprint 67 | Enforcement Chain Doc + Mission Replay CLI (B-145, B-146) | CLOSED |
| Sprint 68 | Patch/Apply Contract Design (B-147, D-141) — Phase 8C | CLOSED |
| Sprint 69 | Operating Model Freeze + State Drift Guard (D-142) — Phase 9 | CLOSED |
| Sprint 70 | Validator/Closer Drift Hardening — Phase 9 | CLOSED |
| Sprint 71 | Intake Gate + Workflow Writer Enforcement — Phase 9 | CLOSED |
| Sprint 72 | Session Protocol Enforcement — Phase 9 | CLOSED |
| Sprint 73 | Project Entity + CRUD (D-144, Phase 10 Faz 1) + D-146 Anti-Loop | CLOSED (operator override) |
| Sprint 74 | Workspace + Artifacts (D-145, Phase 10 Faz 2A) | CLOSED (operator override) |
| Sprint 75 | Rollup + SSE + Dashboard (D-145, Phase 10 Faz 2B) | CLOSED |
| Sprint 76 | Governance Contract Hardening (Security + EventBus + Audit) | CLOSED |
| Sprint 78 | Router Bypass Fix + Browser Analysis Contract (D-149) | CLOSED |

## Next Sprint

S78 closed: Router Bypass Fix + Browser Analysis Contract (D-149). PR #415 merged. S79 next: scope TBD (UX remediation candidate).

### Carry-Forward
| Item | Source | Status |
|------|--------|--------|
| S74+ impl/test separate commits | S73 retro | Required — prevents GPT review gate-timing loop |
| PROJECT_TOKEN rotation/docs | S23 retro | AKCA-owned, non-blocking |
| Docker prod image optimization | D-116 (S26) | Partial — docker-compose done, prod image remaining |
| SSO/RBAC (full external auth) | D-104/D-108/D-117 | Partial — D-117 + backend isolation done. SSO + full RBAC remaining |
| UX findings remediation (UX-001→UX-007) | S78 D-149 audit | 7 findings open (3 high, 4 medium) — S79 candidate |
| UX report B3: screenshot PNGs | GPT UX review | Capture actual PNGs (Playwright or manual export) |
| UX report B4: root cause verify | GPT UX review | Inspect frontend/src/api/client.ts for double-read bug |
| UX report B5: remediation task map | GPT UX review | Finding→task/owner/component/sprint mapping |
| D-150 Capability Routing Transition | S77 proposed | Needs operator review |
