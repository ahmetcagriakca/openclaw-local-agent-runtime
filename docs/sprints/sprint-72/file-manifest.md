# Sprint 72 — File Manifest

## New Files
| File | Task | Lines | Purpose |
|------|------|-------|---------|
| `tools/pre-implementation-check.py` | T72.2 | 271 | Session entry gate — 7 deterministic checks |
| `tests/test_pre_implementation_check.py` | T72.3 | 380 | 37 unit tests for the gate tool |

## Modified Files
| File | Task | Change |
|------|------|--------|
| `CLAUDE.md` | T72.1 | Session Protocol expanded: 3 steps → 11 steps (entry/during/exit) |
| `docs/ai/state/open-items.md` | T72.1 | Next sprint format fix for state-sync regex compatibility |

## Pre-Sprint Setup (committed before T72.1)
| File | Purpose |
|------|---------|
| `tools/ask-gpt-review.sh` | GPT review API script |
| `docs/ai/prompts/gpt-review-system_v3.md` | Review system prompt |
| `docs/ai/prompts/review-verdict-contract_v2.md` | Verdict output contract |
| `docs/ai/prompts/review-delta-packet_v2.md` | Delta packet template |
| `docs/ai/prompts/review-pipeline-runbook_v2.md` | Pipeline runbook |
| `.env.example` | APIM credentials template |
| `AGENTS.md` | Codex agent instructions |

## Evidence Files
| File | Source |
|------|--------|
| `evidence/sprint-72/pytest-output.txt` | `py -m pytest tests/test_pre_implementation_check.py -v` |
| `evidence/sprint-72/pre-impl-check-output.txt` | `py tools/pre-implementation-check.py` |
| `evidence/sprint-72/intake-gate-output.txt` | `py tools/task-intake.py 72 --skip-project` |
| `evidence/sprint-72/mid-review-gate.txt` | pre-impl-check + state-sync after T72.1 |
| `evidence/sprint-72/validator-output.txt` | `py tools/project-validator.py` |
| `evidence/sprint-72/ci-output.txt` | `gh run list --limit 3` |
| `evidence/sprint-72/closure-check-output.txt` | Sprint closure eligibility |
