# Sprint 13 — Phase 5.5: Stabilization + Structural Hardening

**Repo path:** `docs/sprints/sprint-13/README.md`
**implementation_status:** not_started
**closure_status:** not_started
**Owner:** AKCA (operator)
**Implementer:** Claude Code
**Reviewers:** GPT (review gates), Claude (mid + final assessment)

---

## Goal

Zero technical debt (49 items). Event-driven token governance. Industry-standard monorepo. Reproducible dev environment. No new features.

## Scope

- **Critical:** Agent context window fix (D-102) — EventBus + L1/L2 + enforcement + monitoring
- **Bugs:** Token report ID mismatch, WSL naming, rework limiter (D-103)
- **Backend:** Flat → layered FastAPI (app/core, api/v1, models, schemas, services, events, handlers)
- **Frontend:** Flat → feature-based React (features/, components/ui/, api/, hooks/, types/)
- **Legacy:** Dashboard code removal (D-097)
- **Docs:** Archive 28+ stale files, Turkish cleanup, sprint README backfill, templates
- **Tooling:** Pre-commit, coverage, Docker, dev scripts, type sync, .editorconfig
- **Monorepo:** CONTRIBUTING.md, ports.md, runtime/telegram/wsl READMEs

## Out of Scope

Browser E2E (Phase 6), approval changes (Phase 6), OpenAPI→TS SDK (Phase 6), CI/CD pipeline (Phase 6), structured logging (Phase 6), security hardening (Phase 6+), runtime script relocation (OD-17=A).

## Dependencies

| Dependency | Status | Blocker? |
|-----------|--------|----------|
| Sprint 12 closure_status=closed | ⬜ Pending | Yes |
| D-102 frozen | ✅ Done | — |
| D-103 proposed (rework limiter) | ⬜ Sprint 13 Task 13.3 | No |
| OD-17→OD-20 pre-resolved | ✅ Done | — |

## Blocking Risks

| Risk | Mitigation |
|------|-----------|
| Context fix strips needed info | Artifacts are handoff docs. Tier A=5K chars. Feature flag rollback. |
| Backend import migration breaks tests | pytest before AND after. Atomic commits per layer. |
| Frontend restructure breaks build | npm run build + tsc --noEmit after every move. |
| Docker doesn't match local | Same ports. Tested in 13.18. |
| Sprint too large (30 tasks) | Tracks independent after mid-gate. Track 5 can partially ship. |

## Acceptance Criteria (28 items)

See SPRINT-13-TASK-BREAKDOWN.md for full list. Key highlights:
1. Developer stage ≤ 30K tokens on complex mission
2. EventBus with 13 handlers, 28 event types, bypass impossible
3. Backend layered with create_app() factory, API v1, RFC 7807
4. Frontend feature-based with api/ layer, ErrorBoundary, @/ alias
5. docker-compose starts 4 services
6. Decision debt zero: D-001→D-103
7. 49/49 debt items closed

## Exit Criteria

- closure_status=closed by operator
- 30 evidence files in evidence/sprint-13/
- Closure script ELIGIBLE
- Retrospective with ≥ 1 actionable output

## Files

| File | Purpose | Status |
|------|---------|--------|
| README.md | Sprint home (this) | Active |
| SPRINT-13-TASK-BREAKDOWN.md | Full plan, 30 tasks | Active |
| SPRINT-13-KICKOFF-GATE.md | Gate checklist | Active |
| SPRINT-13-MID-REVIEW.md | Mid-review | Not yet |
| SPRINT-13-FINAL-REVIEW.md | Final review | Not yet |
| SPRINT-13-RETROSPECTIVE.md | Retrospective | Not yet |
| SPRINT-13-CLOSURE-SUMMARY.md | Closure | Not yet |

## Evidence Location

`evidence/sprint-13/` — 30 mandatory files.

## Port Map (Post-Sprint 13)

| Port | Service | Status |
|------|---------|--------|
| 8001 | WMCP | Operational |
| 8002 | Legacy Dashboard | Retired (code removed) |
| 8003 | Vezir API | Operational, 11 components |
| 3000 | Vezir UI | Operational |
| 9000 | Math Service | Operational |
