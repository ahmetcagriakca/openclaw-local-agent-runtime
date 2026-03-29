# Test Taxonomy — Vezir Platform

This document maps all test suites to their locations, runner commands, evidence filenames, and count extraction commands per D-127 sprint closure class taxonomy.

## Test Suites

| Suite | Location | Runner Command | Evidence File | Count Extraction |
|-------|----------|---------------|---------------|-----------------|
| Backend | `agent/tests/` | `cd agent && python -m pytest tests/ -v` | `pytest-output.txt` | `python -m pytest tests/ --co -q \| tail -1 \| grep -oE '[0-9]+' \| head -1` |
| Validator | `tests/test_project_validator.py` | `python -m pytest tests/test_project_validator.py -v` | `validator-tests.txt` | `python -m pytest tests/test_project_validator.py --co -q \| tail -1` |
| E2E Unit | `agent/tests/test_e2e.py` | `cd agent && python -m pytest tests/test_e2e.py -v` | `pytest-output.txt` (included in backend) | `python -m pytest tests/test_e2e.py --co -q \| tail -1` |
| E2E Playwright | `tests/e2e/*.spec.ts` | `npx playwright test --reporter=list` | `playwright-output.txt` | `npx playwright test --reporter=list 2>&1 \| grep -cE '✓\|✘'` |
| Frontend | `frontend/src/__tests__/` | `cd frontend && npx vitest run` | `vitest-output.txt` | `npx vitest run 2>&1 \| grep 'Tests' \| grep -oE '[0-9]+ passed'` |

## Count Reconciliation

The `sprint-closure-check.sh` total is: **backend + frontend + e2e-unit**.

- Backend count includes E2E unit tests (they live in `agent/tests/test_e2e.py`)
- Playwright tests are counted separately and reported in `playwright-output.txt`
- Validator tests are counted separately and reported in `validator-tests.txt`
- Frontend tests are counted from vitest output

## Evidence File Mapping

| Evidence File | Source Suite | Class: Product | Class: Governance |
|--------------|-------------|----------------|-------------------|
| `pytest-output.txt` | Backend (includes E2E unit) | Required | Required |
| `vitest-output.txt` | Frontend | Required | Required |
| `playwright-output.txt` | E2E Playwright | Required | Required |
| `validator-tests.txt` | Validator | Required | Required |
| `validator-output.txt` | Board validator | Required | Required |
| `e2e-output.txt` | Playwright raw or combined | Required | NO EVIDENCE |

## Running All Suites

```bash
# Backend (465+ tests including 39 E2E unit)
cd agent && python -m pytest tests/ -v

# Validator (29 tests)
python -m pytest tests/test_project_validator.py -v

# Frontend (75 tests)
cd frontend && npx vitest run

# Playwright E2E (7 tests, requires API on :8003)
npx playwright test --reporter=list

# Board validator (not a test suite, but produces validator-output.txt)
python tools/project-validator.py
```
