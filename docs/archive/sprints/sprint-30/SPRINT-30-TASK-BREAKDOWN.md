# Sprint 30 — Task Breakdown

**Sprint:** 30
**Phase:** 7 (kickoff)
**Title:** Repeatable Automation Core — Templates + Timeline + Approval + Guardrails
**Model:** A

**Goal:** Build the first complete user workflow cycle: template → run → inspect → approve → enforce. Phase 7 theme: repeatable + governable + inspectable automation.

---

## Track 1: Decision Freeze + Templates

**30.1 — Phase 7 workflow decision pack freeze**

Freeze three product decisions before implementation starts.

**Repo scope:** `docs/ai/DECISIONS.md`, `docs/decisions/`
**Branch:** `sprint-30/t30.1-workflow-decisions`

**Implementation:**
1. D-119: Mission template lifecycle contract
   - Template schema (name, description, parameters, specialist config)
   - CRUD operations (create, read, update, delete, publish/unpublish)
   - Run-from-template API contract
   - Parameter validation rules
2. D-120: Scheduled/triggered mission execution contract
   - Cron-based scheduling model
   - Event-triggered execution model
   - Execution queue semantics
   - Deferred to implementation in S31+ (decision frozen now)
3. D-121: Approval gate contract
   - Approval request lifecycle (pending → approved/rejected/expired)
   - Actor-chain audit (who requested, who approved)
   - Expiration policy
   - Integration with mission state machine

**Acceptance:** D-119, D-120, D-121 frozen. No ambiguity.

---

**30.2 — Mission Templates v1**

Template CRUD + run-from-template API + minimal template UI.

**Repo scope:** `agent/templates/`, `agent/api/`, `frontend/src/`
**Branch:** `sprint-30/t30.2-mission-templates`
**Depends on:** 30.1 (D-119 must be frozen)

**Implementation:**
1. Create `agent/templates/store.py` — template CRUD (file-based JSON)
2. Create `agent/templates/schema.py` — template schema validation
3. Add API endpoints: GET/POST/PUT/DELETE /api/v1/templates
4. Add POST /api/v1/templates/{id}/run — create mission from template
5. Add minimal template list UI component
6. Add template tests

**Acceptance:**
1. Template CRUD works via API
2. Run-from-template creates mission with template parameters
3. Template list visible in UI
4. Tests pass

---

## Gates

**30.G1 — Mid Review Gate**

After Track 1. Branch-exempt.

---

## Track 2: Timeline + Approval + Guardrails

**30.3 — Mission Timeline / Run Detail UI v1**

Visual timeline of mission execution in the dashboard.

**Repo scope:** `frontend/src/components/`, `frontend/src/pages/`
**Branch:** `sprint-30/t30.3-mission-timeline`
**Depends on:** 30.G1

**Implementation:**
1. Mission run list page (all missions with status, duration, template)
2. Run detail page with step timeline
3. Tool/plugin usage summary per step
4. Failure point visibility (error highlight)
5. Use generated API types from OpenAPI SDK

**Acceptance:** Timeline renders mission stages, errors visible, types from SDK

---

**30.4 — Approval Inbox v1**

Centralized approval request management.

**Repo scope:** `agent/api/`, `frontend/src/`
**Branch:** `sprint-30/t30.4-approval-inbox`
**Depends on:** 30.G1

**Implementation:**
1. Approval inbox API: list pending, approve, reject with reason
2. Approval expiration check (auto-expire after configurable timeout)
3. Actor-chain audit fields (requester, approver, timestamp)
4. Minimal inbox UI component
5. Add approval lifecycle tests

**Acceptance:** Inbox shows pending approvals, approve/reject works, audit trail

---

**30.5 — Tenant Guardrails baseline**

Usage limits and budget controls.

**Repo scope:** `agent/services/`, `agent/api/`
**Branch:** `sprint-30/t30.5-guardrails`
**Depends on:** 30.G1

**Implementation:**
1. Per-tenant usage counter (missions created, API calls, LLM tokens)
2. Configurable quota thresholds in config
3. Soft-stop (warning event) + hard-stop (deny mutation) hooks
4. Guardrail metrics in observability
5. Add guardrail tests

**Acceptance:** Usage counted, thresholds enforced, events emitted

---

**30.G2 — Final Review Gate**
**30.RETRO — Retrospective**
**30.CLOSURE — Sprint Closure**

---

## Decisions to Freeze

| ID | Topic | When |
|----|-------|------|
| D-119 | Mission template lifecycle | Before 30.2 |
| D-120 | Scheduled/triggered missions | Before 30.2 (deferred impl) |
| D-121 | Approval gate contract | Before 30.4 |

## Carry-Forward

| Item | Target |
|------|--------|
| Scheduled mission execution | S31 (D-120 frozen, impl deferred) |
| Cost/outcome dashboard | S31 |
| Knowledge/connector layer | S32+ |
| Policy engine | S31+ |

## Output Files

| Task | Output |
|------|--------|
| 30.1 | `docs/decisions/D-119,D-120,D-121` |
| 30.2 | `agent/templates/`, API endpoints, template UI |
| 30.3 | `frontend/src/` timeline components |
| 30.4 | Approval inbox API + UI |
| 30.5 | `agent/services/guardrails.py`, usage counters |
