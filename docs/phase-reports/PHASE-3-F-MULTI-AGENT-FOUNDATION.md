# Phase 3-F: Multi-Agent Foundation

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator + Claude Opus 4.6
**Scope:** Mission Controller + analyst/executor specialists — first multi-agent orchestration

---

## Section 1: Executive Summary

**What was built:** A hub-and-spoke Mission Controller that breaks complex user requests into sequential stages, delegates each stage to a specialist agent (analyst or executor), collects typed artifacts between stages, and generates a final summary. This is the first multi-agent implementation in the OpenClaw system.

**End-to-end verified:** 4 tests passed:

| Test | Type | Result | Duration |
|------|------|--------|----------|
| Single agent (CPU query) | Regression | PASS | 13s |
| System diagnostics mission | 5-stage analyst | PASS | 55s |
| Create + verify mission | executor → analyst | PASS | 22s |
| Mission state persistence | JSON on disk | PASS | — |

**Key design decisions:**
- D-029: Hub-and-spoke — all handoffs through Mission Controller, agents never call each other
- D-030: Specialists share the same LLM provider, differentiated by system prompt + tool policy
- D-031: Sequential execution only in Phase 3-F, parallel deferred

---

## Section 2: Architecture

### 2.1 Mission Flow

```
User request (--mission flag)
  -> MissionController.execute_mission()
    -> Step 1: _plan_mission() — LLM breaks goal into stages
    -> Step 2: _execute_stage() × N — each stage runs a specialist
    -> Step 3: _generate_summary() — LLM summarizes all results
  -> JSON output with stages, artifacts, summary
```

### 2.2 Hub-and-Spoke Pattern

```
                    ┌─────────────────────┐
                    │  Mission Controller  │
                    │  (planner + router)  │
                    └──────┬──────┬───────┘
                           │      │
              ┌────────────┘      └────────────┐
              ▼                                ▼
    ┌──────────────────┐            ┌──────────────────┐
    │  Analyst Agent   │            │  Executor Agent  │
    │  (read-only)     │            │  (write/action)  │
    │  14 tools        │            │  12 tools        │
    └──────────────────┘            └──────────────────┘
```

- Controller is the single success/failure owner
- Agents never call each other directly
- Artifact handoff: each stage receives previous stage artifacts as context

### 2.3 Specialist Differentiation

| Aspect | Analyst | Executor |
|--------|---------|----------|
| System prompt | Read-only, structured findings | Action-oriented, report results |
| Tool policy | 14 read-only tools | 12 write/action tools + 3 read tools |
| Risk profile | Low (all read operations) | Medium-high (write, launch, modify) |
| LLM provider | Same as planner | Same as planner |

### 2.4 Stage Execution

Stages execute sequentially: Stage 1 → Stage 2 → ... → Stage N.

Each stage receives:
- Its own instruction from the planner
- A summary of all previous stage artifacts (typed artifact handoff)

If any stage fails, the mission fails immediately with the error recorded.

---

## Section 3: Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `agent/mission/__init__.py` | Package init |
| `agent/mission/controller.py` | Mission Controller — plan, execute, summarize |
| `agent/mission/specialists.py` | Specialist prompts and tool policies |
| `agent/oc_agent_runner_lib.py` | Reusable agent runner with tool_policy + prompt override |

### Modified Files

| File | Change |
|------|--------|
| `agent/oc-agent-runner.py` | Refactored to import from lib, added `--mission` flag |
| `wsl/oc-agent-run` | Mission mode via 4th arg or `mission:` prefix, timeout 300s |
| `docs/ai/STATE.md` | Phase 3-F closed, Mission Controller in component table |
| `docs/ai/NEXT.md` | Updated with post-3-F roadmap |
| `docs/ai/DECISIONS.md` | D-029, D-030, D-031 added |

---

## Section 4: Test Results

### Test 1 — Single Agent Regression
```
Input:  "CPU kullanımı ne?"
Output: "Şu an CPU kullanımı %57."
Tools:  get_system_info (1 call)
Result: PASS — existing flow unaffected
```

### Test 2 — System Diagnostics Mission
```
Input:  "Bilgisayarımın genel durumunu kontrol et: CPU, RAM, disk, ağ bağlantısı ve çalışan servisler"
Stages: 5 (all analyst)
  stage-1: CPU → %40
  stage-2: RAM → 20.6/63.7 GB
  stage-3: Disk → C: 374.7/475.8 GB, E: 540.3/1863 GB
  stage-4: Network → Ethernet 3, Bluetooth
  stage-5: Services → crcDaemon, SystemSoundsService, ResolutionHost, ...
Duration: 55s
Result: PASS
```

### Test 3 — Create + Verify Mission
```
Input:  "results klasörüne agent-mission-test.txt yaz, sonra doğrula"
Stages: 2
  stage-1 (executor): write_file → file created at results/agent-mission-test.txt
  stage-2 (analyst):  list_directory → file confirmed present
Duration: 22s
Result: PASS — typed artifact handoff (file_created → analyst context) verified
```

### Test 4 — Mission State Persistence
```
Files: logs/missions/mission-*.json (4 files)
Content: Full mission state with stages, artifacts, timestamps, durations
Result: PASS — crash recovery data available
```

---

## Section 5: Usage

### CLI
```bash
# Single agent (unchanged)
python agent/oc-agent-runner.py -m "mesaj"

# Multi-agent mission
python agent/oc-agent-runner.py -m "karmaşık görev açıklaması" --mission

# Mission with specific provider
python agent/oc-agent-runner.py -m "görev" --agent claude-general --mission
```

### WSL Bridge
```bash
# Normal
oc-agent-run "mesaj"

# Mission via 4th argument
oc-agent-run "görev" gpt-general 8654710624 mission

# Mission via prefix
oc-agent-run "mission: görev"
```

---

## Section 6: Future Work (Not in Phase 3-F)

| Item | Description |
|------|-------------|
| Parallel execution | Run independent stages concurrently |
| More specialists | developer, tester, reviewer roles |
| Per-specialist models | Cheap model for analysis, expensive for execution |
| Mission resume | Restart from last completed stage after crash |
| OpenClaw auto-routing | Complex requests auto-routed to mission mode |
| Stage retry | Retry failed stage before failing entire mission |

---

## Section 7: Decisions Frozen

- **D-029:** Hub-and-spoke — all handoffs through Mission Controller
- **D-030:** Specialists differentiated by system prompt + tool policy, same underlying provider
- **D-031:** Sequential stage execution in Phase 3-F, parallel deferred
