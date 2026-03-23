# Phase 4 — Sprint 3: Role Expansion — 2 Specialist → 9 Governed Role

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator + Claude Opus 4.6
**Scope:** 10 skill contracts, 9 role registry entries, 9 system prompts, 9 working set templates, planner update, forbidden skill enforcement, artifact×role tier matrix

---

## Section 1: Executive Summary

**What changed:** The system's operational identity expanded from 2 undifferentiated specialists (analyst, executor) to 9 governed roles, each bounded by its own skill contract, tool policy, working set template, system prompt, and context tier defaults. This is the largest architectural change since Phase 3-F introduced the Mission Controller.

**Before Sprint 3:**
- 2 specialists: analyst (read-only), executor (write/action)
- Planner forced every task into one of these two buckets
- No skill validation, no role-specific budgets, no tier differentiation

**After Sprint 3:**
- 9 roles: product-owner, analyst, architect, project-manager, developer, tester, reviewer, manager, remote-operator
- 10 skill contracts with forbidden role enforcement
- 47-entry artifact×role tier matrix
- Role-specific working set templates with differentiated budgets
- Planner uses complexity-based routing (trivial/simple/medium/complex)
- Startup validates all registries before first LLM call

**Test results:** All unit tests passed, 8/8 forbidden skill cases, regression green (single-agent + mission mode).

---

## Section 2: The 9 Roles

| Role | Default Skill | Tool Policy | File Reads | Expansions | Model |
|------|---------------|-------------|:----------:|:----------:|-------|
| product-owner | requirement_structuring | No tools (0) | 0 | 0 | gpt-4o |
| analyst | repository_discovery | Read-only (14) | 30 | 999 | claude-sonnet |
| architect | architecture_synthesis | Read-only (14) | 15 | 999 | claude-sonnet |
| project-manager | work_breakdown | No tools (0) | 0 | 0 | gpt-4o |
| developer | targeted_code_change | Dev (14, incl. write_file) | 20 | 8 | claude-sonnet |
| tester | test_validation | Read-only (13) | 15 | 3 | claude-sonnet |
| reviewer | quality_review | Read-only (4) | 12 | 5 | claude-sonnet |
| manager | summary_compression | No tools (0) | 0 | 0 | gpt-4o |
| remote-operator | controlled_execution | All tools (24) | 10 | 2 | gpt-4o |

**Alias table (D-048):** `executor` → `remote-operator`, `po` → `product-owner`, `pm` → `project-manager`

---

## Section 3: The 10 Skill Contracts

| Skill | Owning Role(s) | Output Artifact | Tools | Cost Class |
|-------|----------------|-----------------|:-----:|:----------:|
| requirement_structuring | product-owner | requirements_brief | 0 | minimal |
| repository_discovery | analyst, architect | discovery_map | 13 | high |
| architecture_synthesis | architect | technical_design | 4 | high |
| work_breakdown | project-manager | work_plan | 0 | minimal |
| targeted_code_change | developer | code_delivery | 14 | high |
| test_validation | tester | test_report | 13 | medium |
| quality_review | reviewer | review_decision | 4 | high |
| controlled_execution | remote-operator | execution_result | all | variable |
| summary_compression | manager | artifact_summary | 0 | minimal |
| recovery_triage | manager | recovery_decision | 4 | medium |

Each contract specifies: owningRoles, secondaryRoles, forbiddenRoles, inputArtifacts (with contextTier), outputArtifact, allowedTools, forbiddenTools, budgets (maxTurns, maxFileReads, maxDirectoryReads, maxToolCalls, maxWorkingSetExpansions), costClass, defaultModelTier, preferredModels, escalationTier, claudeJustified.

---

## Section 4: Task Details

### 4.1 Task 3-1: Skill Contract Registry

**File:** `agent/mission/skill_contracts.py`

10 machine-readable contracts as Python dicts. Each contract validated by `validate_all_contracts()` which checks 5 required fields (owningRoles, outputArtifact, allowedTools, budgets, defaultModelTier).

**Helpers:** `get_skill_contract()`, `validate_role_skill()`, `get_allowed_tools()`, `get_forbidden_tools()`, `get_skill_budgets()`, `validate_all_contracts()`

### 4.2 Task 3-2: Role Registry

**File:** `agent/mission/role_registry.py`

9 canonical roles with displayName, defaultSkill, allowedSkills, forbiddenSkills, toolPolicy, allowedTools, defaultModelTier, preferredModel, discoveryRights, budget limits, expansion rights.

**Helpers:** `resolve_role()`, `get_role()`, `get_role_tool_policy()`, `validate_role_registry()`

### 4.3 Task 3-3: System Prompts

**File:** `agent/mission/specialists.py` — rewritten

10 prompt entries (9 roles + executor alias). Each prompt contains:
1. Role identity (1 sentence)
2. Output specification (artifact structure)
3. Constraints (tool/file/discovery limits)
4. Language instruction

Tool policies now **derived from role_registry** at module load time, replacing the old hardcoded `SPECIALIST_TOOL_POLICIES` dict. Single source of truth.

### 4.4 Task 3-4: Working Set Templates

**File:** `agent/mission/controller.py` — `_WORKING_SET_TEMPLATES` expanded

9 templates with role-appropriate budgets:

| Role | max_file_reads | max_directory_reads | max_expansions | forbidden_patterns |
|------|:--------------:|:-------------------:|:--------------:|-------------------|
| product-owner | 0 | 0 | 0 | .ps1, .env, allowlist.json |
| analyst | 30 | 15 | 999 | .env, allowlist.json |
| architect | 15 | 10 | 999 | .env, allowlist.json |
| project-manager | 0 | 0 | 0 | .ps1, .env, allowlist.json |
| developer | 20 | 5 | 8 | .env, allowlist.json |
| tester | 15 | 5 | 3 | .env, allowlist.json |
| reviewer | 12 | 3 | 5 | .env, allowlist.json |
| manager | 0 | 0 | 0 | .ps1, .env, allowlist.json |
| remote-operator | 10 | 5 | 2 | (none) |

Unknown roles get restrictive fallback: 5 reads, 2 dir reads, 0 expansions.

### 4.5 Task 3-5: Planner Prompt Update

**File:** `agent/mission/controller.py` — `_plan_mission()` planner prompt

The planner now knows all 9 roles and uses complexity-based routing:

| Complexity | Roles Used |
|------------|-----------|
| Trivial | analyst only, or developer + tester |
| Simple | analyst → developer → tester → reviewer |
| Medium | product-owner → analyst → architect → developer → tester → reviewer → manager |
| Complex | All roles in sequence |

Stage JSON now includes a `skill` field alongside `specialist`, enabling forbidden skill validation.

### 4.6 Task 3-6: Forbidden Skill Enforcement

**Two enforcement points:**

1. **Planning phase:** After planner generates stages, each (role, skill) pair is validated via `validate_role_skill()`. Invalid combinations → stage pre-failed with `POLICY:` error.

2. **Dispatch phase:** Pre-failed stages are caught before execution, triggering mission failure with the policy error.

**Startup validation extended:** `oc-agent-runner.py` now validates:
- Tool catalog governance (`validate_catalog_governance()`)
- Skill contracts (`validate_all_contracts()`)
- Role registry (`validate_role_registry()`)

Any validation failure → `FATAL` + exit 1.

### 4.7 Task 3-7: Artifact×Role Tier Matrix

**File:** `agent/context/assembler.py` — `_TIER_MATRIX` + `_ROLE_DEFAULT_TIER`

47-entry matrix mapping `(artifactType, role)` → context tier:

```
Priority: explicit override > matrix lookup > role default > "B" fallback
```

**Key design decisions in the matrix:**
- PO gets discovery_map at tier A (metadata only — doesn't need implementation details)
- Developer gets discovery_map at tier C (scoped — only relevant sections)
- Tester gets code_delivery at tier D (full — needs to verify every line)
- PM gets technical_design at tier D (full — needs to decompose it)
- Manager gets test_report at tier D (full — needs to assess quality gate)

---

## Section 5: Test Results

### Unit Tests

| Test Category | Count | Result |
|---------------|:-----:|--------|
| System prompts: 10 entries, all have content | 2 | PASS |
| Tool policies: derived from registry, correct counts | 4 | PASS |
| Working set templates: 9 entries, budgets correct | 5 | PASS |
| Forbidden skill enforcement | 8 | PASS |
| Tier matrix lookups | 6 | PASS |
| **Total** | **25** | **25/25 PASS** |

### Forbidden Skill Test Cases

| Role | Skill | Expected | Result |
|------|-------|----------|--------|
| developer | targeted_code_change | allowed | PASS |
| developer | controlled_execution | forbidden | PASS |
| manager | repository_discovery | forbidden | PASS |
| analyst | repository_discovery | allowed | PASS |
| remote-operator | controlled_execution | allowed | PASS |
| product-owner | repository_discovery | forbidden | PASS |
| reviewer | quality_review | allowed | PASS |
| tester | targeted_code_change | forbidden | PASS |

### Tier Matrix Verification

| Artifact Type | Role | Expected Tier | Result |
|---------------|------|:-------------:|--------|
| discovery_map | developer | C | PASS |
| code_delivery | tester | D | PASS |
| test_report | manager | D | PASS |
| discovery_map | product-owner | A | PASS |
| unknown_type | developer | C (default) | PASS |
| discovery_map (override) | developer | D (override) | PASS |

### Regression

| Test | Result |
|------|--------|
| Single-agent: `"CPU kullanımı ne?"` | PASS (completed) |
| Mission mode: system uptime query | PASS (1 stage, analyst, completed) |

---

## Section 6: File Map

### New Files (Sprint 3)

| File | Task | Purpose |
|------|------|---------|
| `agent/mission/skill_contracts.py` | 3-1 | 10 skill contracts + validation helpers |
| `agent/mission/role_registry.py` | 3-2 | 9 role definitions + alias resolution |

### Modified Files

| File | Tasks | Changes |
|------|-------|---------|
| `agent/mission/specialists.py` | 3-3 | Rewritten: 10 prompts, tool policies from registry |
| `agent/mission/controller.py` | 3-4, 3-5, 3-6 | 9 templates, planner prompt, role/skill validation |
| `agent/context/assembler.py` | 3-7 | 47-entry tier matrix, matrix-based tier selection |
| `agent/oc-agent-runner.py` | 3-6 | Startup validates contracts + registry |

---

## Section 7: Architecture After Sprint 3

```
User Request
  -> oc-agent-runner.py
    -> [D-057] Startup Gate: catalog + contracts + registry validation
    -> Single-agent: run_agent_with_config() (unchanged)
    -> Mission mode: MissionController.execute_mission()
      -> Planner LLM (9-role aware, complexity routing)
        -> Stages with (specialist, skill) pairs
        -> [3-6] validate_role_skill() per stage
        -> [3-6] resolve_role() alias resolution
        -> [3-4] _build_default_working_set() from templates
      -> For each stage:
        -> [3-6] Pre-failed stage check (forbidden skill)
        -> [D-053] Working set fail-closed
        -> [3-7] build_context_for_role() with tier matrix
        -> run_agent_with_config()
          -> [3-3] System prompt from role
          -> [3-3] Tool policy from role_registry
          -> Working Set Enforcer (mutation_surface_mismatch)
          -> Risk Engine -> Approval -> MCP
        -> Assembler stores artifact with D-047 header
      -> Mission summary + telemetry
```

---

## Section 8: Commit History

```
eb10368 Sprint 3: skill contract registry — 10 machine-readable contracts
7849f7e Sprint 3: role registry — 9 canonical roles with tool policies and budgets
1350325 Sprint 3 complete: 9 governed roles — prompts, templates, enforcement, tier matrix
```

---

## Section 9: Sprint 4 Readiness

Sprint 3 delivers the role layer that Sprint 4 (Discovery Map + Complexity Router) depends on:

| Prerequisite | Status |
|--------------|--------|
| 9 roles with differentiated tool policies | Done |
| 10 skill contracts with forbidden enforcement | Done |
| Role-specific working set templates | Done |
| Planner knows all 9 roles | Done |
| Tier matrix for artifact distribution | Done |
| Startup validates all registries | Done |

Sprint 4 will add:
- `repository_discovery` skill producing cached `discovery_map` artifacts
- Complexity router classifying requests as trivial/simple/medium/complex
- Discovery map → working set population (developer file targets from discovery)

---

*Phase 4 Sprint 3 Report*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Date: 2026-03-23*
