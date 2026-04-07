# Browser Audit Session Template — D-149

**Sprint:** S{N}
**Date:** YYYY-MM-DD
**Mode:** observe_only / guided_repro / active_mutation
**Operator Approval:** N/A (observe_only) / Session-level / Per-mutation

---

## Session Scope

- **Target URL:** http://localhost:4000
- **Pages audited:** (list pages visited)
- **Duration:** (start → end)

---

## Pre-Session Checklist

- [ ] Frontend running on port 4000 (`cd frontend && npm run dev`)
- [ ] Backend API running on port 8003 (`cd agent && py oc-agent-runner.py`)
- [ ] Browser tools available (Claude in Chrome / Playwright)
- [ ] Evidence directory created: `evidence/sprint-{N}/browser-audit/`

---

## Evidence Artifacts

| # | Artifact | File | Status |
|---|----------|------|--------|
| 1 | Console log capture | `browser-console.txt` | [ ] |
| 2 | Network request log | `browser-network.txt` | [ ] |
| 3 | DOM observations | `browser-dom-notes.md` | [ ] |
| 4 | UX friction report | `ux-friction-report.md` | [ ] |
| 5 | Reproduction steps | `repro-steps.md` | [ ] |
| 6 | Screenshots | `screenshot-evidence/` (PNG) or session-ID references in report header (Claude in Chrome) | [ ] |

---

## Findings Summary

| ID | Title | Category | Severity | Repro | Page | Owner |
|----|-------|----------|----------|-------|------|-------|
| UX-001 | | | | | | |
| UX-002 | | | | | | |

---

## Session Notes

(Free-form observations, blocked areas, follow-up items)

---

## Post-Session

- [ ] All 6 evidence artifacts produced
- [ ] Findings cross-referenced with repro steps
- [ ] Screenshots annotated where needed
- [ ] Finding IDs sequential and unique
- [ ] Session summary written above
