# D-127: Sprint Closure Class Taxonomy

**ID:** D-127
**Status:** Frozen
**Phase:** 7 / Sprint 34
**Date:** 2026-03-29

---

## Context

Sprint 33 closure required 4 review rounds because `sprint-closure-check.sh` applied product-sprint evidence requirements to a governance sprint. Evidence like `mutation-drill.txt`, `lighthouse.txt`, and `e2e-output.txt` are not producible in governance sprints. Ad hoc `NO EVIDENCE` placeholder creation delays closure and creates friction.

## Decision

### Sprint Classes

| Class | Definition | Example Sprints |
|-------|-----------|-----------------|
| **product** | Adds/modifies user-facing features, API endpoints, UI, or runtime behavior | S30, S31, S32 |
| **governance** | Tooling, docs, decisions, normalization, validation — no product changes | S33, S34 |

### Class Metadata

Each sprint's evidence packet MUST contain `sprint-class.txt` as the canonical class source:
- Content: exactly `governance` or `product` (single line, no whitespace)
- Created by: `tools/generate-evidence-packet.sh <sprint> <class>`
- Read by: `tools/sprint-closure-check.sh` (auto-detect from packet metadata)

### Required Evidence by Class

#### Product Sprint (canonical-evidence-manifest-product.txt)

| File | Source | Required |
|------|--------|----------|
| pytest-output.txt | `cd agent && python -m pytest tests/ -v` | YES |
| vitest-output.txt | `cd frontend && npx vitest run` | YES |
| tsc-output.txt | `cd frontend && npx tsc --noEmit` | YES |
| lint-output.txt | `cd frontend && npm run lint` | YES |
| build-output.txt | `cd frontend && npm run build` | YES |
| playwright-output.txt | `npx playwright test --reporter=list` | YES |
| e2e-output.txt | Playwright or unit E2E raw output | YES |
| validator-output.txt | `python tools/project-validator.py` | YES |
| validator-tests.txt | `python -m pytest tests/test_project_validator.py -v` | YES |
| closure-check-output.txt | `bash tools/sprint-closure-check.sh <N>` | YES |
| contract-evidence.txt | grep-based contract checks | YES |
| grep-evidence.txt | canonical name for contract checks | YES |
| live-checks.txt | curl health + SSE + host attack | YES |
| mutation-drill.txt | mutation lifecycle drill | YES |
| lighthouse.txt | accessibility/performance audit | YES |
| file-manifest.txt | `ls -la evidence/sprint-{N}/` | YES |
| review-summary.md | copy of S{N}-REVIEW.md | YES |
| sprint-class.txt | "product" | YES |

#### Governance Sprint (canonical-evidence-manifest-governance.txt)

| File | Source | Required |
|------|--------|----------|
| pytest-output.txt | `cd agent && python -m pytest tests/ -v` | YES |
| vitest-output.txt | `cd frontend && npx vitest run` | YES |
| tsc-output.txt | `cd frontend && npx tsc --noEmit` | YES |
| lint-output.txt | `cd frontend && npm run lint` | YES |
| build-output.txt | `cd frontend && npm run build` | YES |
| playwright-output.txt | `npx playwright test --reporter=list` | YES |
| validator-output.txt | `python tools/project-validator.py` | YES |
| validator-tests.txt | `python -m pytest tests/test_project_validator.py -v` | YES |
| closure-check-output.txt | `bash tools/sprint-closure-check.sh <N>` | YES |
| file-manifest.txt | `ls -la evidence/sprint-{N}/` | YES |
| review-summary.md | copy of S{N}-REVIEW.md | YES |
| sprint-class.txt | "governance" | YES |
| e2e-output.txt | NO EVIDENCE — governance sprint | PLACEHOLDER |
| contract-evidence.txt | NO EVIDENCE — governance sprint | PLACEHOLDER |
| grep-evidence.txt | NO EVIDENCE — governance sprint | PLACEHOLDER |
| live-checks.txt | NO EVIDENCE — governance sprint | PLACEHOLDER |
| mutation-drill.txt | NO EVIDENCE — governance sprint | PLACEHOLDER |
| lighthouse.txt | NO EVIDENCE — governance sprint | PLACEHOLDER |

### NO EVIDENCE Rules

- A `NO EVIDENCE` file MUST exist (not omitted) with content: `NO EVIDENCE — <reason>`
- Allowed only in governance class for product-specific artifacts
- NEVER allowed for: pytest, vitest, tsc, lint, build, validator, closure-check, file-manifest, review-summary, sprint-class
- Product sprints MUST NOT contain any NO EVIDENCE files

### Class Resolution

- `sprint-closure-check.sh` reads `evidence/sprint-{N}/sprint-class.txt` to determine class
- If file missing: FAIL (cannot determine class)
- Sprint-number-based branching is FORBIDDEN
- `--governance` flag is an explicit override/debug path that forces governance rules

## Consequences

- Evidence packet generator creates class-aware packets
- Closure-check auto-detects class from metadata
- Governance sprints skip product-specific evidence checks without ad hoc workarounds
- Product sprints remain fully checked
