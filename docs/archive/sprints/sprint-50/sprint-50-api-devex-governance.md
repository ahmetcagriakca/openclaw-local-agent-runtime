# Sprint 50 — API Hardening + DevEx + Governance Debt (v1)

**Tarih:** 2026-04-04
**Kaynak:** Claude Code (Opus) — cross-review pending (GPT + Claude Chat)
**Model:** A (full closure — sprint-time evidence, all gates, no waivers)
**Class:** Product + DevEx + Governance (hybrid)
**Phase:** 7
**Predecessor:** Sprint 49 closed (Session 24, 2026-04-04)
**Closure model:** Model A — D-105 compliant.

---

## Review Trail

| Round | Actor | Verdict | Key Delta |
|-------|-------|---------|-----------|
| 1 | Claude Code | Initial plan v1 | 4 scope items, 14 tasks |
| 2 | Claude Chat | **GO** (2 conditions) | +2 concurrency tests for T1, T3 merge first |
| 3 | GPT | GO (browser timeout, verdict accepted) | — |

---

## Sprint 50 Goal

Policy write API (S49 deferred), template/plugin scaffolding CLI (B-109), sprint folder migration (D-132), ve standardized error envelope (RFC 9457). API completeness + developer experience + governance debt closure.

---

## Policy Write API Contract

- CRUD writes go to `config/policies/*.yaml` via atomic write (D-071)
- Pydantic validation on write (reuse PolicyRuleModel from S49)
- Reload engine cache after write
- Mutation audit logging (structured log entry per write)
- No versioning/history (deferred — V2 scope)

---

## Scope

### T1: Policy Write API (Small-Medium)

S49 delivered read-only API. This sprint adds POST/PUT/DELETE.

**Tasks:**

| # | Task | Deliverable |
|---|------|-------------|
| 50.1 | POST /api/v1/policies | Create new YAML rule file, validate, reload engine |
| 50.2 | PUT /api/v1/policies/{name} | Update existing rule, atomic write, reload |
| 50.3 | DELETE /api/v1/policies/{name} | Remove rule file, reload |
| 50.4 | Mutation audit logging | Structured log for create/update/delete operations |
| 50.5 | Policy write API tests | CRUD operations, validation errors, reload verification (~10 tests) |

**Exit criteria:**
- POST/PUT/DELETE operational with Pydantic validation
- Atomic write per D-071
- Engine auto-reload after mutation
- Audit log emitted per mutation
- Tests pass

### T2: B-109 Template/Plugin Scaffolding CLI (Medium)

CLI tool to generate preset template JSON from command-line flags. 3 presets already exist in config/templates/.

**Tasks:**

| # | Task | Deliverable |
|---|------|-------------|
| 50.6 | Scaffold CLI tool | `tools/scaffold_template.py` — generate template JSON from --name, --specialist, --goal, --stages flags |
| 50.7 | Parameter validation | Validate specialist against role registry, goal template syntax, stage count limits |
| 50.8 | Plugin scaffold mode | --plugin flag generates plugin manifest with hooks + event subscriptions |
| 50.9 | Scaffolding tests | CLI output validation, parameter errors, generated file structure (~8 tests) |

**Exit criteria:**
- CLI generates valid preset JSON matching existing schema
- Validates against role registry
- Plugin mode generates manifest
- Tests pass

### T3: D-132 Sprint Folder Migration (Small)

Sprint folder structure has nested `docs/sprints/docs/sprints/` legacy path. Standardize to flat `docs/sprints/sprint-NN/`.

**Tasks:**

| # | Task | Deliverable |
|---|------|-------------|
| 50.10 | Flatten nested structure | Move `docs/sprints/docs/sprints/*` contents to `docs/sprints/` |
| 50.11 | Rename inconsistent folders | Ensure all sprint folders follow `sprint-NN` naming |
| 50.12 | Freeze D-132 decision | Write D-132 decision: canonical sprint folder path = `docs/sprints/sprint-NN/` |

**Exit criteria:**
- No nested `docs/sprints/docs/sprints/` path
- All sprint evidence in `docs/sprints/sprint-NN/`
- D-132 frozen

### T4: RFC 9457 Error Envelope (Small-Medium)

Standardize API error responses with structured error codes.

**Tasks:**

| # | Task | Deliverable |
|---|------|-------------|
| 50.13 | Error envelope model + global handler | `agent/api/error_envelope.py` — APIError with type, title, status, detail, instance fields |
| 50.14 | Error code enum | Standard codes: NOT_FOUND, VALIDATION_ERROR, RATE_LIMITED, CONFLICT, INTERNAL |
| 50.15 | Global exception handler | FastAPI exception_handler that wraps HTTPException → RFC 9457 envelope |
| 50.16 | Error envelope tests | Response format validation, all error codes, backward compat (~8 tests) |

**Exit criteria:**
- All API errors return RFC 9457 envelope
- Error codes are consistent across endpoints
- Backward compatible (existing clients still work)
- Tests pass

---

## Non-Scope (Anti-Scope-Creep)

- Policy versioning / history — V2 scope
- Complex rule combinators (AND/OR/NOT) — V2 scope
- Policy engine UI (frontend page)
- New frontend pages or components
- Template execution changes (only scaffolding)
- Multi-tenant isolation
- Authentication/RBAC changes

---

## Blocking Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | Policy write concurrency | Race condition on YAML files | File-level lock + atomic write (D-071) |
| R2 | Error envelope breaks clients | Frontend parsing errors | Backward compat: keep detail field, add envelope fields |
| R3 | D-132 migration breaks CI | Path references in workflows | Grep all `.github/workflows/` for sprint paths before migration |

---

## Dependencies

| Dependency | Status | Required By |
|------------|--------|-------------|
| Policy Engine (S49) | Done | T1 |
| D-071 Atomic Write | Done | T1 |
| Template Presets (S38) | Done | T2 |
| Role Registry (S14A) | Done | T2 |

---

## Test Plan

| Area | Expected New Tests |
|------|-------------------|
| Policy write API | ~10 (CRUD, validation, reload, audit) |
| Scaffolding CLI | ~8 (generation, validation, plugin mode) |
| Error envelope | ~8 (format, codes, handler, compat) |
| **Total** | **~26 new tests** |

---

## Acceptance Criteria

1. Policy CRUD API fully operational (POST/PUT/DELETE + read)
2. Atomic write + engine reload on every mutation
3. Mutation audit logging
4. Scaffold CLI generates valid template JSON
5. Plugin scaffold mode works
6. Sprint folders flattened, D-132 frozen
7. RFC 9457 error envelope on all API errors
8. All existing tests pass (1018+ total)
9. ~26 new tests added
10. Preflight green

## Exit Criteria

- All acceptance criteria met
- G1 self-review PASS
- G2 GPT review PASS
- All tests green (1044+ total)
- Sprint doc updated with evidence
- Handoff + open-items updated
- Git commit + push
- CI green

## Verification Commands

```bash
cd agent && py -m pytest tests/ -v
cd frontend && npx vitest run
cd frontend && npx playwright test
bash tools/preflight.sh
py tools/benchmark_api.py
```

## Task Execution Order

1. 50.1-50.5 Policy write API (builds on S49 engine)
2. 50.13-50.16 Error envelope (affects all API endpoints, do early)
3. 50.6-50.9 Scaffolding CLI (independent, can parallel)
4. 50.10-50.12 D-132 migration (last — folder changes)

## Issues

| Task Group | Issue Title | Backlog |
|------------|-------------|---------|
| T1 | Policy write API | NEW |
| T2 | [B-109] Template/plugin scaffolding CLI | #170 |
| T3 | D-132 Sprint folder migration | NEW |
| T4 | RFC 9457 Error envelope | NEW |
