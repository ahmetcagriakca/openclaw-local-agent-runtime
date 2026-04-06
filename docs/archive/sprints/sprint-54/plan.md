# Sprint 54 Plan — Audit Export + Dynamic Source + Heredoc Cleanup

**Phase:** 7
**Model:** A (full closure)
**Class:** Operations + DevEx + Cleanup
**Start:** 2026-04-04
**Priority tier:** P3 (all P1/P2 complete)
**Owner:** Claude Code (Opus) — AKCA delegated
**implementation_status:** not_started
**closure_status:** not_started

---

## Sprint-Level Acceptance Criteria

- All 3 tasks implemented with tests
- All existing tests continue to pass (no regression)
- CI green on push

## Sprint-Level Exit Criteria

- 18-step closure checklist (Rule 16) fully executed
- GPT final review PASS
- Git push complete

---

## Tasks

### 54.1 — B-115 Audit Export / Compliance Bundle

**Issue:** #302
**Scope:**
- CLI tool (`tools/audit_export.py`) that bundles mission logs, policy evaluations, approval records, and DLQ events into a single compliance-ready archive (ZIP/tar.gz)
- Export filters: date range, mission ID, user ID
- Output includes: mission timeline, policy decisions, approval chain, error/DLQ history
- API endpoint: `GET /api/v1/audit/export` with query params
- Format: JSON + optional CSV summary

**Evidence:**
- [ ] Unit tests for export logic
- [ ] API endpoint test
- [ ] Sample export file validates

**Exit criteria:** CLI produces valid archive, API returns correct filtered data

### 54.2 — B-018 Dynamic sourceUserId

**Issue:** #303
**Scope:**
- Replace hardcoded `sourceUserId` in mission creation with dynamic resolution
- Resolve from: (1) API auth context (session/token), (2) request header `X-Source-User`, (3) config fallback
- Update `mission_create_api.py` to use resolver chain
- Backward compatible: existing behavior preserved when no auth context

**Evidence:**
- [ ] Unit tests for resolver chain
- [ ] API integration test
- [ ] Existing tests still pass

**Exit criteria:** All existing tests pass, new resolver works for all 3 sources

### 54.3 — B-025 Bootstrap Heredoc Reduction

**Issue:** #304
**Scope:**
- Audit bootstrap/setup scripts for large heredoc blocks
- Extract heredoc content to template files where appropriate
- Reduce inline heredoc usage in PowerShell/bash scripts
- Maintain identical runtime behavior

**Evidence:**
- [ ] Before/after heredoc count
- [ ] Scripts still functional (manual verification)
- [ ] No behavior change

**Exit criteria:** Heredoc count reduced, no functional regression

---

## Produced Artifacts

| File | Change |
|------|--------|
| `tools/audit_export.py` | New — CLI tool |
| `agent/api/audit_api.py` | New — API router |
| `agent/tests/test_audit_export.py` | New — tests |
| `agent/api/mission_create_api.py` | Modified — resolver chain |
| `agent/tests/test_source_user.py` | New — tests |
| Bootstrap scripts | Modified — heredoc extraction |
| `config/templates/` | New — template files from heredoc |
| `docs/sprints/sprint-54/closure-check-output.txt` | Closure evidence |

## Verification Commands → Evidence Mapping

| # | Command | Evidence |
|---|---------|----------|
| 1 | `cd agent && python -m pytest tests/ -v` | closure-check-output.txt |
| 2 | `cd frontend && npx vitest run` | closure-check-output.txt |
| 3 | `cd frontend && npx tsc --noEmit` | closure-check-output.txt |
| 4 | `cd agent && python -m ruff check .` | closure-check-output.txt |
| 5 | `python tools/audit_export.py --help` | CLI tool verification |
| 6 | `curl localhost:8003/api/v1/audit/export` | API endpoint verification |
| 7 | `python tools/export_openapi.py` | OpenAPI sync check |

## Review Gates

- **Mid Review:** After 54.1 + 54.2 complete
- **Final Review:** After 54.3 complete, before closure

## Kickoff Checklist

- [x] Previous sprint `closure_status=closed` (S53)
- [x] Open decisions max 2 (0 open)
- [x] Task breakdown frozen with evidence checklist
- [x] GitHub milestone created (#29)
- [x] GitHub issues created (#302, #303, #304)
- [ ] GPT pre-sprint review PASS

## Dependencies

None. All three tasks are independent.

## Blocking Risks

None. All P3 scope, no architectural changes. No new D-XXX decisions required.
