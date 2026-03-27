# Phase 4 — Sprint 4: Complexity Router + Discovery Map + Working Set Population

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator + Claude Opus 4.6
**Scope:** Tier 0 deterministic complexity classification, artifact schema validation, planner constraint injection, discovery→working set pipeline, analyst prompt refinement

---

## Section 1: Executive Summary

**Problem:** Two gaps remained after Sprint 3:

1. **Cost:** Every mission — even trivial ones like "CPU kullanımı ne?" — triggered a full Tier 2 LLM planning call. D-034 Rule 9: "No premium model for routing."
2. **Working set gap:** Developer/Tester/Reviewer ran with generic template budgets. The Analyst's discovery_map existed but didn't flow into downstream working sets.

**What was built:**

1. **Complexity Router:** Tier 0 deterministic pattern matching classifies requests as trivial/simple/medium/complex before any LLM call ($0.000 cost). Each complexity level maps to a fixed role template that constrains the planner.
2. **Artifact Schema Validator:** 8 machine-readable schemas with required field, type, allowed value, and nested field validation. Discovery map extraction pipeline for downstream working set population.
3. **Planner Constraint Injection:** The planner no longer chooses roles freely — it receives a complexity-determined template and fills in instructions within that template.
4. **Discovery→Working Set Pipeline:** Analyst's discovery_map automatically populates Developer/Tester/Reviewer file targets before their stages execute.

**Validation:** 5/5 router pattern tests, schema validation correct, E2E mission routed as trivial with 3 stages, regression green.

---

## Section 2: Complexity Router (Task 4-1)

### 2.1 Two-Tier Classification

| Tier | Method | Cost | Latency | When Used |
|------|--------|:----:|:-------:|-----------|
| Tier 0 | Regex pattern matching | $0.000 | <1ms | Always tried first |
| Tier 2 | LLM classification (cheapest model) | ~$0.001 | ~2s | Only when Tier 0 returns None |
| Fallback | Default "medium" | $0.000 | 0ms | When no provider available |

### 2.2 Pattern Categories

**Trivial patterns** (single-file edits, status queries):
- `satır ekle`, `satırını ekle`, `dosyasına ... ekle`
- `durumu`, `kontrol et`, `status`, `health`
- `oku`, `göster`, `docstring ekle`
- `güncelle ... version`, `düzelt typo`

**Simple patterns** (small features, 1-2 files):
- `yeni fonksiyon/method`, `kontrol/validation ekle`
- `log/logging ekle`, `hata mesajı`

**Complex patterns** (multi-component, architectural):
- `yeni modül/module/component/service`
- `mimari/architecture/refactor`
- `entegrasyon/integration`, `güvenlik katmanı`
- `migration/göç`

### 2.3 Stage Templates

| Complexity | Roles | Count |
|------------|-------|:-----:|
| trivial | analyst → developer → tester | 3 |
| simple | analyst → developer → tester → reviewer | 4 |
| medium | product-owner → analyst → architect → developer → tester → reviewer → manager | 7 |
| complex | product-owner → analyst → architect → project-manager → developer → tester → reviewer → manager | 8 |

All (role, skill) pairs in templates validated against skill contracts — zero invalid combinations.

### 2.4 Test Results

| Test Message | Expected | Actual | Tier |
|-------------|----------|--------|:----:|
| "requirements.txt dosyasina satirini ekle" | trivial | trivial | 0 |
| "Sistem durumunu kontrol et" | trivial | trivial | 0 |
| "Hata mesajini guncelle" | simple | simple | 0 |
| "Yeni bir MCP tool modulu ekle" | complex | complex | 0 |
| "Guvenlik katmanini sertlestir" | complex | complex | 0 |
| "Bu cok belirsiz bir gorev" (no match) | medium (fallback) | medium | -1 |

**File:** `agent/mission/complexity_router.py`

---

## Section 3: Artifact Schema Validator (Task 4-2)

### 3.1 Schemas Defined

| Artifact Type | Required Fields | Nested Validation | Allowed Values |
|---------------|:---------------:|:-----------------:|:--------------:|
| discovery_map | 4 | relevant_files[], component_map[], working_set_recommendations | — |
| requirements_brief | 3 | requirements[] | — |
| analysis_report | 5 | — | feasibility, recommendation |
| test_report | 1 | — | verdict |
| review_decision | 1 | — | decision |
| code_delivery | 1 | — | — |
| work_plan | 1 | tasks[] | — |
| recovery_decision | 2 | — | recovery_action |

### 3.2 Validation Capabilities

- **Required fields:** Missing field → error
- **Field types:** Wrong type (e.g., string instead of list) → error
- **Allowed values:** Value not in enum → error
- **Nested required:** Array items missing fields → error per item
- **Unknown types:** Pass-through (fail-open for extensibility)

### 3.3 Discovery Map Extraction

`extract_working_set_from_discovery()` transforms discovery_map's `working_set_recommendations` into downstream-consumable file targets:

```python
Input:  discovery_map.working_set_recommendations = {
    "developer": ["agent/services/tool_catalog.py"],
    "tester": ["agent/services/tool_catalog.py"],
    "reviewer": ["agent/services/tool_catalog.py"]
}

Output: {
    "developer": {
        "readOnly": ["agent/services/tool_catalog.py"],
        "readWrite": [],      # Populated later by work_plan
        "creatable": [],      # Populated later by work_plan
        "directoryList": ["agent/services"]
    },
    "tester": {
        "readOnly": ["agent/services/tool_catalog.py"],
        "directoryList": ["agent/services"]
    },
    "reviewer": {
        "readOnly": ["agent/services/tool_catalog.py"],
        "directoryList": ["agent/services"]
    }
}
```

**Files:** `agent/artifacts/__init__.py`, `agent/artifacts/schema_validator.py`

---

## Section 4: Planner Constraint Injection (Task 4-3)

### 4.1 New Planning Flow

```
Before Sprint 4:
  User message → Planner LLM (free choice) → Stages

After Sprint 4:
  User message → Complexity Router (Tier 0/$0)
    → Stage template (fixed role sequence)
      → Constrained Planner LLM (fill instructions only)
        → Validated stages
          → _force_template() if planner deviated
```

### 4.2 Constrained Planner Prompt

The planner receives:
- `TASK COMPLEXITY: {trivial|simple|medium|complex}`
- `REQUIRED ROLE SEQUENCE: analyst -> developer -> tester`
- Explicit stage list with specialist and skill pre-filled
- Instruction: "Do NOT add or remove roles"

### 4.3 Force Template Safety Net

If the planner produces a different number of stages than the template requires, `_force_template()` overrides:
- Uses template roles/skills exactly
- Salvages instructions from planner output where role names match
- Generates generic instructions for unmatched stages

### 4.4 Telemetry

New event: `complexity_classified`
```json
{
  "event": "complexity_classified",
  "mission_id": "mission-20260323...",
  "complexity": "trivial",
  "tier_used": 0,
  "role_count": 3,
  "message_preview": "Sistem durumunu kontrol et"
}
```

### 4.5 Mission State

New field: `mission["complexity"]` — stored in mission JSON for audit.

**File modified:** `agent/mission/controller.py`

---

## Section 5: Discovery → Working Set Pipeline (Task 4-4)

### 5.1 Enrichment Flow

```
Analyst stage completes
  → discovery_map artifact stored in Assembler
    → Developer/Tester/Reviewer stage about to start
      → _enrich_working_set_from_discovery()
        → Finds latest discovery_map in Assembler
        → Extracts file targets via extract_working_set_from_discovery()
        → Merges into existing working set (union, not replace)
```

### 5.2 Enrichment Rules

| Role | Added to working set |
|------|---------------------|
| developer | readOnly, readWrite, creatable, directoryList |
| tester | readOnly, directoryList |
| reviewer | readOnly, directoryList |

- Enrichment is **additive** — existing template files are preserved
- If no discovery_map exists, template defaults are used (regression safe)
- Developer gets readWrite/creatable from discovery recommendations; work_plan will narrow these further in Sprint 5+

**File modified:** `agent/mission/controller.py` — new method `_enrich_working_set_from_discovery()`

---

## Section 6: Analyst Prompt Refinement (Task 4-5)

The analyst prompt now explicitly specifies the discovery_map output schema:

1. **repo_structure:** List of directory paths (max 3 levels)
2. **relevant_files:** List with path, purpose, relevance_score (0-1)
3. **component_map:** List with component, files, responsibility
4. **working_set_recommendations:** Dict with developer/tester/reviewer file lists

Key additions:
- "Be PRECISE with working_set_recommendations" — precision guidance
- "Developer list should include files that need modification + their imports"
- "Do NOT produce free-text descriptions — the downstream pipeline parses this structure **programmatically**"

**File modified:** `agent/mission/specialists.py`

---

## Section 7: E2E Validation

### Live Mission Test

```bash
python agent/oc-agent-runner.py -m "Sistem durumunu kontrol et" --mission
```

**Result:**
- Complexity router: **trivial** (Tier 0, $0.000)
- Template: 3 stages (analyst → developer → tester)
- All 3 stages completed successfully
- Telemetry: `complexity_classified` event with `tier_used: 0`
- Mission summary JSON produced

### Regression

| Test | Result |
|------|--------|
| Single-agent: `"CPU kullanımı ne?"` | PASS (completed, no routing overhead) |
| Mission mode: `"Sistem durumunu kontrol et"` | PASS (trivial, 3 stages) |

---

## Section 8: File Map

### New Files

| File | Task | Purpose |
|------|------|---------|
| `agent/mission/complexity_router.py` | 4-1 | Tier 0/2 complexity classification + stage templates |
| `agent/artifacts/__init__.py` | 4-2 | Package init |
| `agent/artifacts/schema_validator.py` | 4-2 | 8 artifact schemas + validation + discovery extraction |

### Modified Files

| File | Tasks | Changes |
|------|-------|---------|
| `agent/mission/controller.py` | 4-3, 4-4 | Constrained planner, _force_template, discovery enrichment, complexity in mission state |
| `agent/mission/specialists.py` | 4-5 | Analyst prompt with discovery_map schema specification |

---

## Section 9: Cost Impact

### Before Sprint 4
Every mission required at minimum:
- 1 Tier 2 planner call (~$0.01-0.03)
- N stage execution calls

### After Sprint 4
- **Trivial/simple/complex tasks:** Tier 0 classification ($0.000) + constrained planner call (cheaper — less decision-making required)
- **Ambiguous tasks only:** Tier 0 miss + Tier 2 classification (~$0.001) + constrained planner call

**Estimated savings:** 30-50% reduction in planning token cost for pattern-matched tasks, which covers the majority of operational requests.

---

## Section 10: Sprint 5 Readiness

Sprint 4 delivers the intelligence layer that Sprint 5 (Quality Gates + Feedback Loops) depends on:

| Prerequisite | Status |
|--------------|--------|
| Complexity-based stage templates | Done |
| Discovery map schema validation | Done |
| Discovery → working set pipeline | Done |
| Planner constrained by template | Done |
| Analyst produces structured discovery_map | Done (prompt refined) |
| Artifact schema validator for quality gate checks | Done |

Sprint 5 will add:
- Quality gates between stage groups (Gate 1: requirements+design, Gate 2: code+test, Gate 3: review)
- Developer↔Tester and Developer↔Reviewer feedback loops with iteration limits
- Recovery triage via manager role on gate failure

---

## Section 11: Commit History

```
213c87e Sprint 4: complexity router + discovery schema + working set population
```

---

*Phase 4 Sprint 4 Report*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Date: 2026-03-23*
