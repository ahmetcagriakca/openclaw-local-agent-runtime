# Phase 4.5-A — Telemetry Tooling

**Date:** 2026-03-24
**Status:** COMPLETE
**Author:** Operator (AKCA) + Claude Opus 4.6
**Prerequisite:** Phase 4 complete (Sprint 6D done)

---

## Section 1: Executive Summary

Phase 4.5-A delivers operational tooling for analyzing mission telemetry and running E2E tests across all complexity levels. Additionally, specialist prompts were refined to encourage structured JSON output, improving artifact extraction rates.

**Deliverables:**
1. `agent/tools/analyze_telemetry.py` — Telemetry aggregation + human/JSON report
2. `agent/tools/run_e2e_test.py` — E2E test runner with 4 predefined test cases
3. Prompt refinements in `agent/mission/specialists.py` — JSON output blocks for 4 roles
4. 18 new unit tests (all pass)

---

## Section 2: Telemetry Analyzer

### 2.1 Features

- Parses `logs/policy-telemetry.jsonl` for policy event analysis
- Parses `logs/missions/*-summary.json` for mission metrics
- Aggregates: event type counts, deny reasons, deny by role
- Mission stats: duration, stage count, reworks, gate pass rates
- Model usage per agent/role
- Context tier distribution (A through E)
- Artifact extraction rate estimates
- Cost estimates per complexity level

### 2.2 Usage

```bash
# Human-readable report
python agent/tools/analyze_telemetry.py

# JSON output
python agent/tools/analyze_telemetry.py --json

# Last 5 missions only
python agent/tools/analyze_telemetry.py --last 5

# Last 24 hours of telemetry
python agent/tools/analyze_telemetry.py --hours 24
```

---

## Section 3: E2E Test Runner

### 3.1 Predefined Test Cases

| ID | Complexity | Roles | Budget | Message |
|----|-----------|-------|--------|---------|
| T-OT-1 | Trivial | 3 | $0.10 | Update get_system_info description |
| T-OT-2 | Simple | 4 | $0.50 | Add blocked pattern to risk_engine |
| T-OT-3 | Medium | 7 | $2.00 | Add new MCP tool: get_disk_details |
| T-OT-4 | Complex | 8 | $5.00 | Design Slack integration for approval service |

### 3.2 Usage

```bash
# List test cases
python agent/tools/run_e2e_test.py --list

# Check prerequisites
python agent/tools/run_e2e_test.py --check

# Run single complexity level
python agent/tools/run_e2e_test.py --complexity trivial

# Run all test cases
python agent/tools/run_e2e_test.py --all

# Custom mission message
python agent/tools/run_e2e_test.py --message "your goal here"
```

---

## Section 4: Prompt Refinements

Added structured JSON output instructions to 4 specialist prompts:

| Role | JSON Block Added |
|------|-----------------|
| product-owner | `{"title", "summary", "requirements", "constraints", ...}` |
| developer | `{"touched_files", "self_test_notes", "blockers"}` |
| tester | `{"verdict", "criteria_results", "bugs"}` |
| reviewer | `{"decision", "findings", "design_compliance", "security_concerns"}` |

Each prompt now includes `IMPORTANT: Include a structured JSON block in your response wrapped in ```json ... ``` markers.` with a concrete example.

**Expected impact:** artifact_extractor's `_try_json_extraction` path will be used more frequently, reducing reliance on regex/heuristic fallbacks.

---

## Section 5: Test Evidence

```
Phase 4.5-A Tests: 18 passed, 0 failed — OK
Sprint 6D Tests:   41 passed, 0 failed — OK
Sprint 5C Tests:   70 passed, 0 failed — ALL TESTS PASSED
Total:            129 tests, 0 failures
```

---

## Section 6: File Manifest

| File | Action | Description |
|------|--------|-------------|
| `agent/tools/__init__.py` | CREATE | Package marker |
| `agent/tools/analyze_telemetry.py` | CREATE | Telemetry analysis + reporting |
| `agent/tools/run_e2e_test.py` | CREATE | E2E test runner (4 test cases) |
| `agent/mission/specialists.py` | MODIFY | JSON output blocks for 4 roles |
| `agent/tests/test_phase45a.py` | CREATE | 18 unit tests |
