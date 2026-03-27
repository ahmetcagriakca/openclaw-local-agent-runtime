# D-105 — Closure Model Standardization

**ID:** D-105
**Title:** Sprint Closure Model — Standard vs Lightweight with Mandatory Waivers
**Status:** frozen
**Proposed date:** 2026-03-27
**Frozen date:** 2026-03-27
**Owner:** AKCA
**Recommended by:** GPT (S13 review), Claude (S13–S16 reviews), 4 sprints without resolution

---

## Context

Six sprints have been reviewed (12–16+). Only Sprint 12 had sprint-time evidence and executed gates. Every subsequent sprint (13, 14A, 14B, 15, 16) required retroactive evidence or gate waivers. Without a formal closure model, each sprint reinvents the same decisions: What evidence is acceptable? Which gates can be waived? When is reused evidence valid?

This compounds to process overhead, governance risk, and inconsistent audit trails. D-105 must be frozen before Sprint 17 kickoff.

---

## Decision (Proposed)

Define two closure models. **Operator selects which model applies at sprint kickoff.**

---

### Model A — Full Closure (Sprint 12 baseline)

All evidence collected during sprint execution (not retroactively). All gates executed in correct order. No waivers except explicitly pre-approved categories.

**Requirements:**
- All mandatory evidence files collected before closure attempt
- Kickoff gate executed before implementation starts
- Mid-sprint gate executed at task midpoint
- Final review gate executed after implementation, before closure
- Evidence under `evidence/sprint-{N}/` (not `docs/`)
- GPT review completed and findings addressed

**Use when:** Phase-closure sprints, architecture-mutation sprints, or sprints with external dependencies.

---

### Model B — Lightweight Closure (regularization model)

Evidence may be retroactive if: (a) implementation is complete, (b) tests pass on current codebase, (c) each gap is documented with an explicit waiver, and (d) no evidence is fabricated.

**Requirements:**
- All mandatory evidence files present (retroactive origin acceptable if current codebase)
- Retrospective is never waivable — must be produced
- Each gate waiver requires an explicit waiver record with justification
- Evidence path exception (`docs/` vs `evidence/`) is logged as process debt
- `closure_status=closed` still operator-only

**What Model B does NOT allow:**
- Ad-hoc closure rules invented per sprint
- Evidence claimed without file existence verification
- Decision records referenced as "frozen" without formal record
- Ghost decision state (referenced as dependency but status unknown)
- Claiming "fully validated" when live E2E was not performed

**Use when:** Single-session implementation sprints where gate timing was structurally impossible.

---

## Answers to Open Questions

| Question | Answer |
|----------|--------|
| When is retroactive evidence acceptable? | Model B only. Must be current-codebase output, not stale snapshots. |
| Which gates can be waived? | Kickoff and mid-sprint (Model B). Retrospective = NEVER. Final review = NEVER. |
| Current-state test output counts as sprint evidence? | YES in Model B, with explicit note that evidence is retroactive. |
| Reused evidence (e.g., S12 lighthouse)? | Acceptable if still current (codebase unchanged for that dimension), with explicit reuse note. |
| `closure_status=closed` minimum set? | Model A: 13 mandatory files + all gates. Model B: 13 mandatory files + retrospective + waiver docs + operator sign-off. |
| Model A vs Model B selection? | Operator declares at kickoff. Default = Model A unless explicitly downgraded. |
| Forbidden? | Ad-hoc per-sprint closure rules. Evidence fabrication. Ghost decision state. |

---

## Trade-off

| Model A | Model B |
|---------|---------|
| Full audit trail | Acceptable for single-session fast sprints |
| Higher process overhead | Risk of "waiver inflation" if Model B becomes default |
| Required for phase-closure sprints | Must not become a permanent shortcut |

**Constraint:** Model B may only be used for maximum 2 consecutive sprints before a Model A sprint is required. This prevents permanent downgrade of process standards.

---

## Impacted Files / Process Artifacts

| Artifact | Change |
|---------|--------|
| `tools/sprint-closure-check.sh` | Add `--model` flag: `A` enforces no waivers; `B` validates waiver docs present |
| Sprint kickoff template | Add: "Closure Model: A / B" field |
| Sprint README template | Add: "Closure Model" field |
| `DECISIONS.md` | Add D-105 entry |

---

## Validation Method

- Sprint 17 kickoff includes explicit closure model declaration
- `sprint-closure-check.sh` respects declared model
- No sprint proceeds past kickoff gate without model declaration

---

## Rollback / Reversal Condition

If Model B causes repeated evidence gaps or governance failures, deprecate Model B and require Model A for all sprints. Operator decision.

---

## Operator Action Required

Review and approve this proposal. Once approved, status → `frozen`. Update DECISIONS.md.

**This must be frozen before Sprint 17 kickoff.**
