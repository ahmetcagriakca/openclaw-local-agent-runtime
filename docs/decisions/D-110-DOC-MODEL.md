# D-110 — Documentation Model Hierarchy

**ID:** D-110
**Title:** Canonical Document Model — Dual Source with Clear Hierarchy
**Status:** frozen
**Proposed date:** 2026-03-27
**Frozen date:** 2026-03-27
**Owner:** AKCA
**Recommended by:** GPT (source-of-truth audit), Claude (Sprint 17 kickoff)

---

## Context

Two documentation systems coexist in the repo:

1. **STATE.md / NEXT.md model** — established since Phase 4, continuously maintained through 16 sprints. Contains system state, component status, test evidence, roadmap.
2. **Repo-native workflow** — introduced in Session 3 (2026-03-27). Includes `handoffs/current.md`, `sprint-plan.sh`, `sprint-finalize.sh`, review packets.

The handoff document (current.md) references the repo-native workflow as active, while the actual repo evidence shows STATE.md/NEXT.md as the continuously maintained canonical source. This ambiguity creates confusion about which documents are authoritative.

---

## Decision

**Dual model with explicit hierarchy:**

| Document | Role | Authority |
|----------|------|-----------|
| `docs/ai/STATE.md` | System state — components, ports, test counts, decisions | **Canonical** |
| `docs/ai/NEXT.md` | Roadmap — completed sprints, Phase 6 items, capabilities | **Canonical** |
| `docs/ai/DECISIONS.md` | Decision index | **Canonical** |
| `docs/ai/handoffs/current.md` | Session context — what happened this session, next steps | **Supplementary** |
| `docs/ai/state/open-items.md` | Active blockers and carry-forward | **Supplementary** |
| `tools/sprint-plan.sh` | Kickoff planning orchestrator | **Optional tooling** |
| `tools/sprint-finalize.sh` | Closure orchestrator | **Optional tooling** |
| `docs/review-packets/` | Generated audit packets | **Optional artifacts** |

### Hierarchy rules:
1. If STATE.md and current.md conflict → STATE.md wins
2. Session start: read current.md for context, verify against STATE.md
3. Session end: update both current.md (session context) and STATE.md (system state)
4. Sprint tooling (sprint-plan.sh, sprint-finalize.sh) is available but not mandatory
5. Review packets are useful artifacts, not governance requirements

---

## Implications

1. STATE.md and NEXT.md remain the primary session-start reads
2. current.md provides session continuity but is not authoritative for system state
3. No forced migration to packet-only workflow
4. Tooling can be adopted incrementally as operator sees fit

---

## Validation Criteria

1. STATE.md contains doc model marker
2. NEXT.md contains doc model marker
3. No document claims sole canonical authority over another canonical document

---

## Supersedes

None. First formal doc model decision.
