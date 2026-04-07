# Session Handoff — 2026-04-07 (Session 52 — Sprint 77 + Post-Sprint Fixes)

**Platform:** Vezir Platform
**Operator:** Claude Code (Opus) — AKCA delegated

---

## Session Summary

Session 52: Sprint 77 closed + post-sprint project/mission UX + Azure routing fixes.

### S77 — Azure OpenAI Provider Foundation (D-148) — CLOSED
- D-148 frozen: Azure OpenAI = default primary provider, deterministic fallback
- AzureOpenAIProvider: Responses API adapter (input-based), error mapping (401/404/429/timeout)
- Canonical contract: TaskRequest/ProviderResponse in base.py, AgentProvider.execute() canonical entrypoint
- ProviderRoutingPolicy: Azure-first, kill switch, capability-based reroute, fallback chain
- AzureHealthCheck: endpoint probe + retirement guard (30-day warning)
- ProviderSelectionTelemetry: every routing decision logged
- 89 new tests. GPT R1 HOLD → R2 HOLD → R3 PASS. PR #410 merged.

### Post-Sprint Fixes (direct to main)
- **Azure routing wired to runtime**: MissionController.__init__ + _select_agent_for_role() use ProviderRoutingPolicy. All stages now show azure-general.
- **Role preference override removed**: preferredModel no longer bypasses Azure-first routing (D-148).
- **Frontend port 3000→4000**: vite.config.ts, CORS, CSRF, all docs updated. Port 3000 occupied by Open WebUI.
- **Project create UI**: ProjectsPage "+ New Project" button + form (name, description, local_path).
- **Project edit UI**: ProjectDetailPage "Edit" button + inline form (name, description, local_path).
- **Mission from project**: ProjectDetailPage "+ New Mission" creates mission linked to project via project_id.
- **Project local_path**: Projects can have a local directory path. Workspace uses this path directly.
- **ProjectStore.update fix**: allowed_fields now includes local_path, workspace_root.
- **CORS/CSRF**: PATCH, PUT, DELETE methods added to CORS allow_methods and CSRF middleware.
- **API client**: createProject, updateProject, linkMission, unlinkMission, apiPatchJson added.

## Current State

- **Phase:** 10 active — S77 closed
- **Last closed sprint:** 77
- **Sprint 77 status:** closure_status=closed, PR #410 merged
- **Decisions:** 145 frozen + 2 superseded (D-001 → D-148)
- **Tests:** 1866 backend + 239 frontend + 13 Playwright + 139 root = 2257 total
- **CI:** Green on main
- **Port map:** API :8003, Frontend :4000, WMCP :8001
- **Security:** 0 CodeQL open, 2 dependabot (pre-existing)
- **Open issues:** B-148 PAT (pre-existing)
- **Blockers:** None

## Review History

| Sprint | Claude Code | GPT |
|--------|-------------|-----|
| S75 | — | PASS (R4) |
| S76 | — | PASS (R2) |
| S77 | — | HOLD R1 → HOLD R2 → PASS R3 (targeted scope) |

## Phase 10 Status

| Sprint | Scope | Status |
|--------|-------|--------|
| S73 | Project Entity + CRUD (D-144, Faz 1) | Closed |
| S74 | Workspace + Artifacts (D-145, Faz 2A) | Closed |
| S75 | Rollup + SSE + Dashboard (D-145, Faz 2B) | Closed |
| S76 | Governance Contract Hardening | Closed |
| S77 | Azure OpenAI Provider Foundation (D-148) | Closed |
| S78 | TBD | Not started |

## Carry-Forward

| Item | Source | Status |
|------|--------|--------|
| PROJECT_TOKEN rotation | S23 retro | AKCA-owned, non-blocking |
| Docker prod image optimization | D-116 | Partial — docker-compose done |
| SSO/RBAC (full external auth) | D-104/D-108/D-117 | Partial — D-117 + isolation done |
| D-021→D-058 extraction | S8 | AKCA-assigned decision debt |
| Planner/summary router bypass | S77 GPT R3 note | _plan_mission, _generate_summary still direct create_provider |
| D-149 Browser Analysis Contract | Proposed (S78) | From s77.zip — needs operator review |
| D-150 Capability Routing Transition | Proposed (S79) | From s77.zip — needs operator review |
| eslint 9→10 migration | Dependabot | Deferred |
| vite 6→8 + plugin-react 6 | Dependabot | Deferred |
| B-148 PAT-backed Project V2 | S71 | Blocked by GITHUB_TOKEN limitation |
| EventBus production wiring | D-147 | Future sprint — currently test-only |

## GPT Memo

Session 52 (S77+post-sprint): S77 Azure OpenAI Provider Foundation closed. D-148 frozen. AzureOpenAIProvider (Responses API), ProviderRoutingPolicy (capability routing, kill switch, fallback), AzureHealthCheck (retirement guard), ProviderSelectionTelemetry. 89 new tests (1866 BE). GPT R1 HOLD → R2 HOLD → R3 PASS. PR #410 merged. Post-sprint: Azure routing wired to controller runtime. Frontend port 3000→4000. Project create/edit UI with local_path. Mission-from-project linking. ProjectStore update fix for local_path. CORS/CSRF PATCH support. Total: 1866 BE + 239 FE + 13 PW + 139 root = 2257. 145 frozen + 2 superseded decisions.
