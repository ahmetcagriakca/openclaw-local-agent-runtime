# D-109 — Benchmark Strategy

**ID:** D-109
**Title:** Benchmark Pipeline — Evidence-Only Model
**Status:** frozen
**Proposed date:** 2026-03-27
**Frozen date:** 2026-03-27
**Owner:** AKCA
**Recommended by:** GPT (CI audit), Claude (Sprint 17 kickoff)

---

## Context

`tools/benchmark_api.py` produces `evidence/sprint-12/benchmark.txt` — a human-readable performance report using FastAPI TestClient. The CI workflow (`benchmark.yml`) had a broken compare step referencing nonexistent `compare_benchmark.py` and `benchmark-baseline.json`. This created false CI confidence: the step silently skipped due to baseline-not-found guard.

Two options:
1. **Evidence-only:** benchmark produces `.txt` report, uploaded as artifact. No automated regression gate.
2. **Regression gate:** benchmark produces JSON baseline, compare script enforces threshold. Requires new tooling.

---

## Decision

**Evidence-only model.** Benchmark pipeline produces and uploads `benchmark.txt` as CI artifact. No automated regression comparison.

Rationale:
- Current benchmark tool outputs plain text, not structured JSON
- Building a real regression gate (JSON baseline, threshold comparator, baseline rotation) is a separate effort
- Evidence-only gives visibility without false gates
- Regression gate can be added in a future sprint when JSON output + baseline infra exists

---

## Implications

1. `benchmark.yml` runs `python tools/benchmark_api.py` from repo root
2. Evidence verify step: `test -f evidence/sprint-12/benchmark.txt`
3. Artifact upload: `evidence/sprint-12/benchmark.txt`
4. No compare step until future sprint adds JSON baseline tooling
5. CI benchmark job = informational, not blocking

---

## Validation Criteria

1. `python tools/benchmark_api.py` completes without error
2. `evidence/sprint-12/benchmark.txt` is produced
3. No dead code referencing nonexistent compare scripts

---

## Supersedes

None. First benchmark strategy decision.
