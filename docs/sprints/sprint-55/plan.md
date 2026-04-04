# Sprint 55 Plan — Audit Export + Dynamic Source + Heredoc Cleanup

**Phase:** 7
**Model:** A (full closure)
**Class:** Operations + DevEx + Cleanup
**Start:** 2026-04-04
**Priority tier:** P3 (all P1/P2 complete)
**Owner:** Claude Code (Opus) — AKCA delegated
**implementation_status:** not_started
**closure_status:** not_started
**Carried from:** Sprint 54 (deferred — not implemented)

---

## Sprint-Level Acceptance Criteria

- All 3 tasks implemented with contract-level tests
- All existing tests continue to pass (no regression)
- CI green on push
- D-134 resolver precedence verified in tests
- 55.1 audit export: auth scoping, filter correctness, fail-closed on unauthorized access

## Sprint-Level Exit Criteria

- 18-step closure checklist (Rule 16) fully executed
- GPT final review PASS
- Git push complete
- Closure evidence in `docs/sprints/sprint-55/closure-check-output.txt` (D-132 convention)

---

## Tasks

### 55.1 — B-115 Audit Export / Compliance Bundle

**Issue:** #305
**Scope:**
- CLI tool (`tools/audit_export.py`) that bundles mission logs, policy evaluations, approval records, and DLQ events into a single compliance-ready archive (ZIP/tar.gz)
- Export filters: date range, mission ID, user ID
- Output includes: mission timeline, policy decisions, approval chain, error/DLQ history
- API endpoint: `GET /api/v1/audit/export` with query params
- Format: JSON + optional CSV summary

**Export Contract:**
- **Authorized callers:** Localhost only (D-070/D-087 trust boundary). No external access.
- **User/mission scoping:** Export filtered by authenticated user context. Users can only export their own missions unless operator role.
- **Redaction:** API keys, secrets, and LLM response content stripped from export. Only metadata + policy decisions + state transitions included.
- **Included record types:** Mission timeline, policy evaluations, approval chain, DLQ events, error summaries.
- **Fail-closed:** Unauthorized request → HTTP 403. Missing/invalid filters → HTTP 422. Export generation failure → HTTP 500 with error detail, no partial archive.
- **Archive integrity:** ZIP with SHA-256 checksum file included. CLI verifies checksum on export.
- **Size/time guardrails:** Max 1000 missions per export. Timeout 60s. Response streamed for large archives.

**Evidence:**
- [ ] Unit tests for export logic (filter, scoping, redaction)
- [ ] API endpoint test (auth, error paths, success)
- [ ] Fail-closed test (unauthorized, invalid filter)
- [ ] Sample export validates (archive structure, checksum)

**Exit criteria:** CLI produces valid archive with checksum. API enforces auth scoping. Unauthorized access returns 403. Invalid filters return 422. Redaction verified in tests.

### 55.2 — B-018 Dynamic sourceUserId

**Issue:** #306
**Frozen decision:** D-134 (Source User Identity Resolution Contract)
**Scope:**
- Replace hardcoded `sourceUserId` in mission creation with dynamic resolution per D-134
- Resolver precedence (D-134): (1) authenticated session/token, (2) `X-Source-User` header (trusted origins only), (3) `config.default_user` fallback
- Fail-closed: if no source resolves → HTTP 401
- Header-based resolution restricted to trusted origins (localhost/internal) per D-070
- Update `mission_create_api.py` to use resolver chain
- Backward compatible: existing behavior preserved (config fallback = current hardcoded value)

**Evidence:**
- [ ] Unit tests for resolver chain (all 3 tiers + fail-closed)
- [ ] API integration test (auth context, header, fallback, rejection)
- [ ] Trusted origin validation test
- [ ] Existing tests still pass (backward compat)

**Exit criteria:** All 3 resolution tiers work. Fail-closed on no resolution (401). Header only from trusted origins. All existing tests pass.

### 55.3 — B-025 Bootstrap Heredoc Reduction

**Issue:** #307
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
| `agent/tests/test_audit_export.py` | New — tests (export, auth, redaction, fail-closed) |
| `agent/api/mission_create_api.py` | Modified — D-134 resolver chain |
| `agent/tests/test_source_user.py` | New — tests (3 tiers, fail-closed, trusted origin) |
| `bin/start-wmcp-server.ps1` | Modified — heredoc extraction |
| `bin/oc-system-health.ps1` | Modified — heredoc extraction |
| `config/templates/wmcp-config.template` | New — extracted heredoc content |
| `config/templates/health-check.template` | New — extracted heredoc content |
| `docs/sprints/sprint-55/closure-check-output.txt` | Closure evidence (D-132) |
| `docs/decisions/D-134-source-user-identity.md` | Formal decision record |

## Verification Commands → Evidence Mapping

| # | Command | Evidence |
|---|---------|----------|
| 1 | `cd agent && python -m pytest tests/ -v` | closure-check-output.txt (backend) |
| 2 | `cd frontend && npx vitest run` | closure-check-output.txt (frontend) |
| 3 | `cd frontend && npx tsc --noEmit` | closure-check-output.txt (TypeScript) |
| 4 | `cd agent && python -m ruff check .` | closure-check-output.txt (lint) |
| 5 | `python tools/audit_export.py --help` | closure-check-output.txt (CLI smoke) |
| 6 | `curl -s localhost:8003/api/v1/audit/export` | closure-check-output.txt (API smoke) |
| 7 | `python tools/export_openapi.py` | closure-check-output.txt (OpenAPI sync) |
| 8 | `bash tools/preflight.sh` | closure-check-output.txt (full preflight) |

**Note:** Project closure evidence convention per D-132 and GOVERNANCE.md Rule 16 step 15 is `docs/sprints/sprint-{N}/closure-check-output.txt` — single file containing all verification output.

## Review Gate Tasks

### 55.G1 — Mid Review Gate

**After:** 55.1 + 55.2 complete
**Action:** Submit mid-sprint review to GPT with implementation evidence
**Gate:** GPT PASS required before 55.3

### 55.G2 — Final Review Gate

**After:** 55.3 complete
**Action:** Submit final review to GPT with full closure evidence
**Gate:** GPT PASS required before 18-step closure

## Risks

| Risk | Mitigation |
|------|-----------|
| 55.1 data exposure via audit export | Localhost-only (D-070), auth scoping, redaction, fail-closed |
| 55.1 large archive size/timeout | Max 1000 missions, 60s timeout, streaming response |
| 55.2 identity resolution precedence ambiguity | Frozen as D-134, explicit fail-closed, trusted origin gate |
| 55.2 header spoofing from untrusted origin | X-Source-User only accepted from trusted origins (D-070) |

## Kickoff Checklist

- [x] Previous sprint deferred (S54 — not implemented, tasks carried forward)
- [x] Open decisions max 2 (D-134 frozen this sprint)
- [x] Task breakdown frozen with evidence checklist
- [x] GitHub milestone created (#30)
- [x] GitHub issues created (#305, #306, #307)
- [x] GPT pre-sprint review PASS (Round 5)

## Dependencies

Tasks are implementation-independent. Review gates create sequential checkpoints (mid after 55.1+55.2, final after 55.3).
