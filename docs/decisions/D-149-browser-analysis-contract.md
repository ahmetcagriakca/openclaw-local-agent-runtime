# D-149: Browser Analysis — 3-Mode Observation Contract

- **ID:** D-149
- **Title:** Browser Analysis — 3-Mode Observation Contract
- **Status:** frozen
- **Phase:** S78
- **Date:** 2026-04-07
- **Owner:** AKCA
- **Recommended by:** Claude (architecture analysis) + GPT (cross-review)

---

## Context

- Vezir frontend (React dashboard, port 4000) usability analysis pending.
- Dynamic role selection (D-148) requires observation data — routing decisions are blind without browser behavior measurement.
- Claude Code browser-supported analysis available (Claude in Chrome, Playwright, console/network/DOM capture).
- Opening unrestricted browser mutation = unnecessary risk — read-only observation layer first.
- Usability findings feed remediation scope.

---

## Decision

1. **Browser-based analysis operates in 3 modes:**

| Mode | Scope | Operator Approval |
|---|---|---|
| `observe_only` | DOM/console/network capture, screenshot, no mutation | Not required |
| `guided_repro` | Replay specific flow, produce evidence, no mutation | Session-level approval |
| `active_mutation` | Staging-only form fill / click / input | Per-mutation approval |

2. **v1 scope: `observe_only` only.** `guided_repro` and `active_mutation` deferred.
3. **Every browser analysis session produces mandatory evidence artifacts.**
4. **Findings tagged with severity + reproducibility + owner.**
5. **No mutation outside staging.** Production URL mutation forbidden.

---

## Evidence Artifact Standard

Each browser analysis session produces:

| Artifact | Format | Description |
|---|---|---|
| `browser-console.txt` | Plain text | Console errors, warnings, logs captured during session |
| `browser-network.txt` | Plain text | Failed requests, slow requests, CORS errors, 4xx/5xx |
| `browser-dom-notes.md` | Markdown | DOM state observations: missing elements, broken layouts, empty states |
| `ux-friction-report.md` | Markdown | Structured finding report (see Finding Schema) |
| `repro-steps.md` | Markdown | Step-by-step reproduction for each finding |
| `screenshot-evidence/` | PNG or session-ID reference | Screenshots per finding. When captured via Claude in Chrome, session IDs (e.g., `ss_6911kxpcc`) are the accepted format with traceability note in the report header. Standalone PNG export is preferred when tooling supports it. |

---

## Finding Schema

```yaml
finding:
  id: UX-001
  title: "descriptive title"
  category: empty_state_quality
  severity: medium        # low / medium / high / critical
  reproducibility: always # always / intermittent / once
  page: /missions
  repro_steps:
    - step 1
    - step 2
  expected: "what should happen"
  actual: "what actually happens"
  console_errors: none
  network_errors: none
  screenshot: screenshot-evidence/UX-001.png OR session-ID (e.g., ss_6911kxpcc)
  owner: TBD
  status: open
```

---

## Task Taxonomy

| Category | Description |
|---|---|
| `onboarding_friction` | First-use experience barriers |
| `navigation_confusion` | Unclear routing, dead ends, missing breadcrumbs |
| `approval_flow_friction` | Approval create/decide/expire UX problems |
| `failure_visibility` | Error states hidden, silent failures, missing error messages |
| `empty_state_quality` | Empty/loading/error states missing or unhelpful |
| `latency_perception` | Slow responses without loading indicators, stale data shown |
| `data_quality_display` | Missing/unknown data shown as zero or blank |
| `agent_stuck_vs_user_stuck` | Distinguishing agent-side vs UI-side failure |
| `accessibility` | Keyboard nav, screen reader, contrast, focus management |

---

## Success Criteria (v1)

| Criterion | Target |
|---|---|
| Verified usability findings | >= 5 (net repro verified) |
| Finding categories covered | >= 3 distinct categories |
| Agent vs user stuck distinction | Stated in every finding |
| Evidence artifacts complete | 6 artifacts per session |
| Console/network errors documented | All 4xx/5xx and JS errors listed |

---

## Impacted Files

| File | Change |
|---|---|
| `docs/shared/browser-audit-template.md` | New — session template |
| `docs/shared/ux-finding-schema.yaml` | New — finding format definition |
| `evidence/sprint-{N}/browser-audit/` | New — per-sprint browser evidence folder |

---

## Trade-offs

| + | - |
|---|---|
| Observation data enables informed routing decisions (D-148) | Additional evidence artifact overhead per session |
| Structured finding format enables tracking over time | v1 limited to observe_only — no interactive repro |
| Browser evidence integrates with existing sprint closure model | Requires frontend running on localhost for analysis |
| Taxonomy prevents ad-hoc, unstructured UX complaints | Categories may need expansion after first audit run |

---

## Validation Method

Each D-149 rule is verified by:

| Rule | Verification |
|---|---|
| observe_only = no mutation | Audit session evidence contains zero POST/PATCH/PUT/DELETE to frontend; all interactions are read-only (screenshot + DOM read) |
| 6 mandatory artifacts per session | `ls evidence/sprint-{N}/browser-audit/` must contain: browser-console.txt, browser-network.txt, browser-dom-notes.md, ux-friction-report.md, repro-steps.md, screenshot-evidence/ |
| >= 5 verified findings | `grep -c "^### UX-" evidence/sprint-{N}/browser-audit/ux-friction-report.md` >= 5 |
| >= 3 categories covered | `grep "Category:" ux-friction-report.md \| sort -u \| wc -l` >= 3 |
| stuck_party on every finding | Every finding in ux-friction-report.md has a "Stuck party:" field with value user/agent/both/unclear |
| No mutation outside staging | No browser tool calls with action=left_click on forms, no type actions into application inputs (observe_only mode) |

---

## Rollback / Reversal

- Browser analysis is additive — no existing system modified.
- Disabling: simply don't run browser audit sessions.
- Evidence artifacts are standalone — removal doesn't affect other sprint evidence.

---

## Dependencies

- D-148 (Azure provider) — audit provider routing behavior in browser.
- Frontend must be running (port 4000) during analysis sessions.
- Claude Code browser capability (Claude in Chrome or Playwright).

---

## Decision Lifecycle

| Date | Event |
|---|---|
| 2026-04-06 | Proposed by Claude + GPT cross-review |
| 2026-04-07 | Frozen (S78) |
