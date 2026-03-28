# Sprint 25 — Task Breakdown

**Sprint:** 25
**Phase:** 6
**Title:** Contract Execution and Frontend Reliability
**Model:** A

**Goal:** Execute deferred archive cleanup, establish OpenAPI→TypeScript SDK generation pipeline, and create frontend component test baseline.

---

## Track 1: Operational Cleanup + Contract Generation

**25.1 — Archive --execute on closed sprints**

Execute the archive tool on closed sprint directories. Move historical sprint data to `docs/archive/sprints/` per D-113.

**Repo scope:** `docs/sprints/`, `docs/archive/sprints/`, `tools/execute-archive.py`, `tools/generate-archive-manifest.py`
**Depends on:** —
**Branch:** `sprint-25/t25.1-archive-execute`

**Implementation:**
1. Run `python tools/generate-archive-manifest.py` to list eligible sprints
2. Review manifest — only closed sprints (not current/last)
3. Run `python tools/execute-archive.py --dry-run` first
4. Run `python tools/execute-archive.py --execute` to move files
5. Verify: archived sprints no longer in `docs/sprints/`, present in `docs/archive/sprints/`
6. Update any references if needed

**Acceptance:**
1. Eligible closed sprints archived to `docs/archive/sprints/`
2. Dry-run output matches execute output
3. No data loss — git history preserved
4. `check-stale-refs.py` still PASS after archive
5. Evidence: archive manifest + execute output in artifacts/

**Verification commands:**
```bash
python tools/generate-archive-manifest.py
python tools/execute-archive.py --dry-run
python tools/check-stale-refs.py
```

**Evidence required:** archive-execute-output.txt, stale-refs check

---

**25.2 — OpenAPI to TypeScript SDK generation pipeline**

Generate TypeScript types/client from Vezir API's OpenAPI spec. Establish reproducible generation command and CI validation.

**Repo scope:** `tools/export_openapi.py`, `frontend/src/api/`, `.github/workflows/ci.yml`
**Depends on:** —
**Branch:** `sprint-25/t25.2-openapi-sdk`

**Implementation:**
1. Export OpenAPI spec: `python tools/export_openapi.py` → `openapi.json`
2. Choose generator: `openapi-typescript` (lightweight, types-only) or `openapi-fetch`
3. Generate TypeScript types: `npx openapi-typescript openapi.json -o frontend/src/api/generated.ts`
4. Add npm script: `"generate:api": "openapi-typescript openapi.json -o src/api/generated.ts"`
5. Add CI validation step: generate → diff → fail if drift detected
6. Commit generated types + generation script

**Acceptance:**
1. `openapi.json` exported and committed
2. TypeScript types generated and compile without errors
3. CI step validates types match current API spec
4. Generation is reproducible (`npm run generate:api` idempotent)
5. Evidence: generation output + tsc check

**Verification commands:**
```bash
python tools/export_openapi.py
cd frontend && npm run generate:api
cd frontend && npx tsc --noEmit
```

**Evidence required:** openapi-sdk-gen-output.txt, tsc-output.txt

---

## Gates

**25.G1 — Mid Review Gate**

After Track 1 (25.1 + 25.2). Review: archive safety, SDK source-of-truth, test strategy. Branch-exempt.

---

## Track 2: Frontend Testing

**25.3 — Frontend Vitest component test baseline**

Create component test baseline using generated TypeScript types. Cover at least one critical frontend flow.

**Repo scope:** `frontend/src/__tests__/`, `frontend/vitest.config.ts`
**Depends on:** 25.G1 (SDK types must exist)
**Branch:** `sprint-25/t25.3-component-tests`

**Implementation:**
1. Identify critical frontend flows (mission list, mission detail, approval)
2. Write component tests using `@testing-library/react` + vitest
3. Use generated API types for mock data (type-safe mocks)
4. Target: 5+ new component tests covering real data flows
5. Ensure existing 29 tests still pass

**Acceptance:**
1. 5+ new component tests added
2. Tests use generated API types (not any/unknown)
3. All existing tests still pass (29+)
4. Evidence: vitest output with new test count

**Verification commands:**
```bash
cd frontend && npx vitest run
```

**Evidence required:** vitest-output.txt showing 34+ tests

---

**25.G2 — Final Review Gate**

Full evidence: pytest + vitest + tsc + lint + archive + SDK gen + closure check. Branch-exempt.

**25.RETRO — Retrospective**

Answer: Is archive safe and reliable? Is SDK generation maintainable? Are component tests covering real flows or just smoke?

**25.CLOSURE — Sprint Closure**

All branches merged. Evidence in artifacts/. GPT operator sets `closure_status=closed`.

---

## Carry-Forward (explicit defer)

| Item | Reason | Target |
|------|--------|--------|
| Backend physical restructure | Program-level change | S26+ |
| Docker dev environment | Not urgent | S26+ |
| Multi-user auth | Requires decision + schema + migration | S26+ |
| Jaeger/Grafana deployment | Infrastructure scope | S26+ |

---

## Output Files

| Task | Output |
|------|--------|
| 25.1 | `docs/archive/sprints/` (archived sprint dirs) |
| 25.2 | `openapi.json`, `frontend/src/api/generated.ts`, CI step |
| 25.3 | `frontend/src/__tests__/*.test.tsx` (5+ new) |
