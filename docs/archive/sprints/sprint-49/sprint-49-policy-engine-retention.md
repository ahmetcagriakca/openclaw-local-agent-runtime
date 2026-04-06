# Sprint 49 — Policy Engine + Operational Hygiene (v2)

**Tarih:** 2026-04-04
**Kaynak:** Claude Code (Opus) — cross-review DONE (GPT CONDITIONAL + Claude Chat CONDITIONAL)
**Model:** A (full closure — sprint-time evidence, all gates, no waivers)
**Class:** Product + Operations (hybrid)
**Phase:** 7
**Predecessor:** Sprint 48 closed (Session 23, 2026-03-31)
**Closure model:** Model A — D-105 compliant.

---

## Review Trail

| Round | Actor | Verdict | Key Delta |
|-------|-------|---------|-----------|
| 1 | Claude Code | Initial plan v1 | 3 scope items, 14 tasks |
| 2 | GPT | CONDITIONAL — 5 blocking | B1-B5: fail-closed contradiction, YAML/CRUD SoT, alert write-only, DLQ unbounded, sprint controls |
| 3 | Claude Chat | CONDITIONAL — 3 blocking | BF-1: fail-closed, BF-2: perf budget, BF-3: user_id propagation |
| 4 | Claude Code | **This document (v2)** | All blocking findings patched |
| 5 | Claude Chat | **GO** | 3/3 blocking kapandı, tüm patch'ler kabul |
| 6 | GPT | **PASS** (kickoff eligible) | 5/5 blocking kapandı, tüm patch'ler kabul |

---

## Sprint 49 Goal

Policy engine implementation (B-107, D-133 contract), DLQ retention policy (B-026), ve alert namespace scoping fix (B-119). Ana deliverable: config-driven rule evaluation engine that runs pre-stage in mission controller.

---

## Policy Engine Evaluation Contract (BF-1 / GPT-B1 patch)

D-133 defines inputs/outputs. This section freezes **evaluation semantics** for S49:

- **Evaluation order:** Rules sorted by `priority` (ascending, lower = higher priority). First matching rule wins.
- **Default on no match:** `deny` (fail-closed). No implicit allow-all.
- **Bootstrap rule:** A `default-allow.yaml` rule ships at priority=9999 (lowest). This makes the engine **functionally fail-open during bootstrap** while explicit deny/escalate rules override at higher priority. This is intentional for backward compatibility with existing missions.
- **Rule loading failure:** If YAML parse error or file missing → log error, skip that rule, continue evaluation. If ALL rules fail to load → `deny` (true fail-closed).
- **Malformed rule:** Pydantic validation on load. Invalid rules rejected with structured error log.

## Storage Authority (GPT-B2 patch)

**Decision: Option A — YAML-backed read-only rules for S49.**

- `config/policies/*.yaml` is the sole source-of-truth at runtime.
- CRUD API is **read-only** in S49: GET /api/v1/policies (list), GET /api/v1/policies/{name} (detail).
- Write API (POST/PUT/DELETE) deferred to S50 — requires atomic write, validation, reload semantics.
- Rules are loaded once at engine init and cached. Reload via API endpoint: POST /api/v1/policies/reload.

---

## Scope

### T1: B-107 Policy Engine Implementation (Major)

D-133 contract frozen. B-013 policyContext + B-014 timeoutConfig already implemented (S48). This sprint builds the engine itself.

**Tasks:**

| # | Task | Deliverable |
|---|------|-------------|
| 49.1 | Policy rule model + YAML loader + Pydantic validation | `agent/mission/policy_engine.py` — Rule dataclass, YAML parse, schema validation, priority sort |
| 49.2 | Policy evaluator (fail-closed) + benchmark test | `evaluate(policy_context, mission_config, tool_request) → Decision`. Perf budget: p99 < 5ms. Benchmark test included. |
| 49.3 | Default rules (YAML) | `config/policies/` — 5 rules: wmcp-degradation, risk-escalation, timeout-enforcement, budget-denial, default-allow (priority=9999) |
| 49.4 | Controller integration (pre-stage hook) | `controller.py` — call `evaluate()` before specialist invocation, handle all 4 decisions. Only if 49.2 benchmark passes. |
| 49.5 | Policy read-only API + reload | `agent/api/policy_api.py` — GET list, GET detail, POST reload. Write API deferred to S50. |
| 49.6 | Policy engine tests | Unit tests: rule loading, evaluation, priority, fail-closed, all 4 decisions, malformed rule rejection, escalate+degrade edge cases |
| 49.7 | Integration tests | Controller + engine + default rules E2E |

**Exit criteria:**
- 5 default rule YAML files in `config/policies/`
- Engine evaluates rules by priority (first-match), returns correct decision
- Fail-closed: no matching rule → deny; all rules fail to load → deny
- Malformed YAML rejected with Pydantic validation error
- Controller calls engine pre-stage, handles allow/deny/escalate/degrade
- Read-only API + reload operational
- p99 eval time < 5ms (benchmark evidence)
- All tests pass

### T2: B-026 DLQ Retention Policy (Small)

DLQ store currently has **zero retention logic** — entries persist indefinitely. Only manual `purge()` and `purge_resolved()` exist.

**Bounded cleanup contract (GPT-B4 patch):**
- Cleanup order: age purge first, then count trim
- Max cleanup batch per enqueue: 50 entries
- Eviction rule: oldest first (FIFO by enqueue timestamp)
- Observability: emit `dlq.cleanup.count` and `dlq.cleanup.duration_ms` log entries

**Tasks:**

| # | Task | Deliverable |
|---|------|-------------|
| 49.8 | Retention config + bounded cleanup method | `dlq_store.py` — `max_age_days` (default 30), `max_entries` (default 1000), `cleanup(max_batch=50)` method with age-first eviction |
| 49.9 | Lazy cleanup on enqueue + observability | Call `cleanup(max_batch=50)` on `enqueue()`, emit cleanup counters in structured log |
| 49.10 | Retention tests | TTL expiry, max entries cap, batch limit, age-first ordering, observability output |

**Exit criteria:**
- Configurable retention (age + count)
- Bounded cleanup on enqueue (max 50 per call)
- Age-first eviction order
- Cleanup counters emitted
- Tests cover TTL, capacity, batch limits, and ordering

### T3: B-119 Alert Namespace Scoping Fix (Small)

Alert engine has broken namespace scoping — `user_id` filter exists in `get_active()`/`get_history()` but Alert class **never populates user_id field**. Filter always returns True (silently bypassed).

**Namespace contract (GPT-B3 patch):**
- user_id added to Alert model (write-path)
- user_id populated from event data in _fire() (source: mission.operator or "system")
- Read-path scoping enforced on get_active/get_history
- Legacy alerts (user_id=None): treated as "system" scope — visible to all users (backward compatible)
- No backfill required — legacy rows remain accessible

**Tasks:**

| # | Task | Deliverable |
|---|------|-------------|
| 49.11 | Add user_id to Alert model + legacy compat | Alert.__init__ + to_dict + from_dict includes user_id (default=None for legacy) |
| 49.12 | Populate user_id in _fire() + read-path enforcement | Extract user from event data (mission.operator), enforce scoping on get_active/get_history. Legacy (None) = visible to all. |
| 49.13 | Create GitHub issue #B-119 | Issue for backlog tracking |
| 49.14 | Alert scoping tests | Write-path population, read-path filtering, legacy-row visibility, edge cases |

**Exit criteria:**
- Alert has user_id field
- _fire() populates user_id from event context
- get_active/get_history correctly filters by user_id
- Legacy alerts (user_id=None) remain visible to all users
- Tests verify write + read path scoping

---

## Non-Scope (Anti-Scope-Creep)

Bu sprint'te aşağıdakiler **kesinlikle kapsam dışıdır:**

- Policy engine UI (frontend page) — S50+ scope
- Policy write API (POST/PUT/DELETE rules) — S50 scope
- Complex rule conditions (AND/OR/NOT combinators) — V2 scope
- Policy versioning / audit trail — V2 scope
- DLQ retry automation (already done in S42 B-106)
- Frontend changes (no new pages, no component changes)
- Alert backfill migration — legacy rows stay as-is
- "oc" rename (operator decision pending)
- D-132 sprint folder path migration
- Weekly report screen implementation
- RFC 9457 error envelope

**Scope creep detection rule:** G1'de `config/policies/` ve `agent/mission/policy_engine.py` dışında yeni module oluşturulmuşsa (API endpoint hariç) → scope creep, HOLD.

---

## Blocking Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | Policy engine changes controller hot-path | Performance regression | p99 < 5ms eval budget. Benchmark test in 49.2. If fails → 49.4 deferred. |
| R2 | YAML parsing security (untrusted input) | Injection risk | `yaml.safe_load()` only + Pydantic schema validation |
| R3 | All rules fail to load | Mission lockout | True fail-closed (deny). default-allow.yaml as bootstrap safety net. |
| R4 | DLQ cleanup on failure-path | Incident latency amplification | Bounded batch (max 50), age-first eviction |
| R5 | Alert user_id not available in _fire() context | B-119 incomplete | Pre-task audit of _fire() call chain. Fallback: user_id="system" |

---

## Dependencies

| Dependency | Status | Required By |
|------------|--------|-------------|
| D-133 Policy Engine Contract | Frozen (S48) | T1 |
| B-013 policyContext | Done (S48) | T1 |
| B-014 timeoutConfig | Done (S48) | T1 |
| B-106 DLQ Store | Done (S42) | T2 |
| Alert Engine | Operational (S16) | T3 |

---

## Test Plan

| Area | Expected New Tests |
|------|-------------------|
| Policy engine unit | ~25 (rule loading, validation, evaluation, priority, fail-closed, all 4 decisions, malformed rejection, escalate/degrade edge cases) |
| Policy API | ~5 (read-only list, detail, reload) |
| Controller integration | ~5 (pre-stage hook, decision handling) |
| Benchmark | ~1 (p99 < 5ms eval time) |
| DLQ retention | ~8 (TTL, capacity, batch limit, age-first ordering, observability) |
| Alert scoping | ~6 (write-path, read-path filtering, legacy compat, edge cases) |
| **Total** | **~50 new tests** |

---

## Issues

Sprint 49 requires GitHub issues for each task group:

| Task Group | Issue Title | Backlog |
|------------|-------------|---------|
| T1 | [B-107] Policy engine implementation | #162 |
| T2 | [B-026] DLQ retention policy | #167 |
| T3 | [B-119] Alert namespace scoping fix | NEW (to be created) |

---

## Acceptance Criteria (GPT-B5 patch)

1. Policy engine evaluates rules pre-stage in controller with correct decision output
2. 5 default YAML rules operational (including default-allow bootstrap)
3. Read-only API + reload endpoint operational
4. p99 eval time < 5ms (benchmark evidence)
5. DLQ has bounded retention with age-first eviction and observability
6. Alert namespace scoping works on both write and read paths
7. Legacy alerts remain accessible
8. All existing tests pass (966+ total)
9. ~50 new tests added
10. Preflight green

## Exit Criteria

- All acceptance criteria met
- G1 self-review PASS
- G2 GPT review PASS
- All tests green (1016+ total)
- Sprint doc updated with evidence
- Handoff + open-items updated
- Git commit + push

## Verification Commands

```bash
# Backend tests
cd agent && python -m pytest tests/ -v

# Frontend tests (no changes expected, regression check)
cd frontend && npx vitest run

# Playwright E2E
cd frontend && npx playwright test

# Preflight
bash tools/preflight.sh

# Benchmark
python tools/benchmark_api.py

# Policy engine specific
cd agent && python -m pytest tests/test_policy_engine.py -v
cd agent && python -m pytest tests/test_dlq_retention.py -v
cd agent && python -m pytest tests/test_alert_scoping.py -v
```

## Expected Evidence

- [ ] Policy engine test results (all pass)
- [ ] Benchmark evidence (p99 < 5ms)
- [ ] DLQ retention test results
- [ ] Alert scoping test results
- [ ] Preflight output (all green)
- [ ] Git commit hash
- [ ] GitHub issues created/closed

## Task Execution Order

1. Alert _fire() call chain audit (pre-req for 49.12)
2. 49.1 Rule model + YAML loader + validation
3. 49.2 Evaluator + benchmark test → perf gate
4. 49.3 Default rules YAML (5 files)
5. 49.4 Controller integration (only if benchmark passes)
6. 49.5 Read-only API + reload
7. 49.6-49.7 Policy tests
8. 49.8-49.10 DLQ retention (can start parallel from step 2)
9. 49.11-49.14 Alert namespace fix
