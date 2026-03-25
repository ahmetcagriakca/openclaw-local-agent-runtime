# CLAUDE.md — OpenClaw Local Agent Runtime

## Project

OpenClaw Local Agent Runtime — governed multi-agent mission system.
Windows 11 + WSL2 Ubuntu-E + Python 3.14 + PowerShell.
9 specialist roles, 3 quality gates, 10-state mission state machine.
24 MCP tools, 3 LLM providers (GPT-4o, Claude Sonnet, Ollama).

## Current State

- Phase 4.5-B: COMPLETED (E2E validated, oc_root bug fixed, 129 tests, 0 failures)
- Phase 4.5-C: READY (Sprint 7 — operational tuning, 10 tasks)
- Phase 5: DESIGNED (Sprint 8–12 — Mission Control Center, 64 tasks)
- Frozen decisions: D-059 → D-076 (17 decisions)

## Active Sprint

Sprint 7 — Phase 4.5-C: Operational Tuning

Tasks:
1. P0.5: controller.py → `_aggregate_deny_forensics()` + mission summary integration
2. P1a: specialists.py → developer self-verification prompt
3. P1b: specialists.py → tester verdict guidelines
4. P2: controller.py → agent_used metadata propagation (scope-safe, single point)
5. P4: approval_service.py → sunset docstring + STATE.md note
6. P5: controller.py + quality_gates.py → schema validation → gate findings visibility
7. P6: STATE.md + NEXT.md → "durable" → "state-persisted, resume not yet implemented"
8. P7: ops/wsl/ → 5 template files
9. 7.9: config/capabilities.json → auto-generated capability manifest
10. 7.10: regression test + E2E rerun

## Key Reference Docs

- `docs/ai/STATE.md` — current system state
- `docs/ai/DECISIONS.md` — frozen decisions D-001 → D-058
- `docs/ai/NEXT.md` — roadmap
- `docs/ai/BACKLOG.md` — backlog
- `docs/ai/PROTOCOL.md` — sprint + freeze protocols

## Architecture Quick Reference

```
Telegram → OpenClaw (WSL) → Agent Runner (Windows) → Mission Controller
  → 9 roles with quality gates → MCP → PowerShell

Port Map:
  8001  WMCP (Windows MCP Proxy)
  8002  Legacy Health Dashboard
  8003  Mission Control API (Phase 5, not yet built)
```

### Mission Flow
```
User goal → PO → Analyst → Architect → PM → Developer → Tester → Reviewer → Manager
            G1 (requirements)    G2 (code+test)    G3 (review)
```

### Key Files
```
agent/mission/controller.py        — mission orchestrator (sole executor)
agent/mission/specialists.py       — 9 role specialist prompts
agent/mission/quality_gates.py     — 3 quality gates
agent/mission/artifact_extractor.py — 3-layer artifact parse
agent/services/approval_service.py — approval handling
agent/services/policy_enforcer.py  — file system policy enforcement
bridge/oc-bridge.ps1               — PowerShell bridge to Windows
config/capabilities.json           — capability manifest (auto-generated)
```

## Working Rules

- Turkish conversation, English technical terms.
- Iterative: design → review → revise → freeze.
- Every task produces concrete output (file, code, doc). No chat-only.
- Blocking fixes first.
- Frozen decisions use D-XXX format.
- Unknown ≠ zero. Missing ≠ healthy.
- Atomic writes: temp → fsync → os.replace(). No raw json.dump to file.
- Source precedence: state.json > mission.json (status), summary > telemetry (forensics).
- Capability detection via config/capabilities.json, not heuristics.

## Build & Test

```bash
# Run all tests
cd agent && python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_sprint_6d.py -v    # Sprint 6D (41 tests)
python -m pytest tests/test_phase45a.py -v     # Phase 4.5-A (18 tests)
python -m pytest tests/test_sprint_5c.py -v    # Sprint 5C (70 tests)

# E2E test
python tools/run_e2e_test.py --all

# Telemetry analysis
python tools/analyze_telemetry.py --last 5

# Verify specific changes
grep "denyForensics" agent/mission/controller.py
grep "SELF-VERIFICATION" agent/mission/specialists.py
grep "agent_used" agent/mission/controller.py
```

## Phase 5 Preview (Sprint 8+)

Mission Control Center — "See Everything, Including What's Missing"

- FastAPI + Uvicorn (port 8003) — D-061
- MissionNormalizer = aggregation layer (7 sources) — D-065
- Schema frozen in Sprint 8 — D-067
- dataQuality model: freshnessMs, stale, partial, degraded — D-068
- Localhost security: Host validation, explicit CORS — D-070
- SSE event ID: `{source}:{offset}` — D-076
- Read-only first (5A), live updates (5B), intervention behind feature flag (5C)

## Do Not

- Do not replace existing architecture with "clean rewrite."
- Do not design from mock data. Use normalized API contract.
- Do not write to files without atomic_write_json().
- Do not treat UI mock structure as backend truth.
- Do not claim "done" without verification evidence.
- Do not leave "to be clarified later" in any task.
