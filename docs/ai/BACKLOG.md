# Backlog

**Last updated:** 2026-03-24

---

## Phase 2 — Security / Policy Hardening

| ID | Item | Notes |
|----|------|-------|
| B-001 | Task-level authorization | Source-to-task matrix |
| B-002 | Operation-level authorization | Per-user submit/cancel permissions |
| B-003 | Task risk classification | Risk scoring framework |
| B-004 | Filesystem confinement | Deeper sandboxing |
| B-005 | Rate limiting | Contract-level throttling |
| B-006 | Encrypted secret storage | Vault/DPAPI |
| B-007 | Automatic secret rotation | Beyond manual |
| B-008 | Audit log tamper resistance | Retention + integrity |
| B-009 | Multi-source allowlist | Per-channel lists |
| B-010 | WMCP credential replacement | Replace local-mcp-12345 |
| B-011 | Transport encryption | mTLS or equivalent |

## Phase 3 — Productization

| ID | Item | Notes |
|----|------|-------|
| B-012 | Stronger dedupe | requestId-based |
| B-013 | Richer policyContext | Runtime parameter expansion |
| B-014 | timeoutSeconds in contract | External timeout field |
| B-015 | Push/callback notifications | Beyond polling |
| B-016 | Task result artifact access | Beyond outputPreview |
| B-017 | Multi-step status visibility | Step-level status |
| B-018 | Dynamic sourceUserId | WSL wrapper improvement |
| B-019 | Intent mapping refinement | OpenClaw conversation quality |
| B-020 | Standard task library | Common task definitions |

## Phase 3 — Agent-MCP System (Done)

| ID | Item | Status | Notes |
|----|------|--------|-------|
| B-029 | Core agent runner | **Done** | Phase 3-B: GPT provider, MCP client, basic tool gateway |
| B-030 | Risk engine + approval service | **Done** | Phase 3-C: deterministic risk, Telegram approval flow |
| B-031 | Full tool catalog + typed artifacts | **Done** | Phase 3-D: 24 named tools, artifact store, audit |
| B-032 | Multi-provider support | **Done** | Phase 3-E: OpenAI, Claude, Ollama providers |
| B-033 | Multi-agent foundation / mission controller | **Done** | Phase 3-F: hub-and-spoke, specialist agents |
| B-034 | Agent-to-agent delegation protocol | **Done** | Phase 3-F: typed artifact handoff contracts |
| B-035 | Persistent mission state | **Done** | Phase 3-F: multi-stage mission tracking |

## Phase 4 — Agent Governance (Done)

| ID | Sprint | Status | Scope |
|----|--------|--------|-------|
| Sprint 0+1 | Governance Enforcer | **Done** | Working Set, Path Resolver, Policy Telemetry |
| Sprint 1H+2 | Governance Context | **Done** | Context Assembler, Expansion Broker, Summary Cache |
| Sprint 2C | Integration Completion | **Done** | Artifact Identity, Summary Cache fixes |
| Sprint 3 | Role Expansion | **Done** | 9 roles, 10 skill contracts, 2 feedback loops |
| Sprint 4 | Complexity Router | **Done** | 4-tier routing, discovery governance |
| Sprint 5 | Quality Gates + State Machine | **Done** | 3 gates, 10-state machine, approval store |
| Sprint 5C | Controller Integration | **Done** | State machine, gates, recovery, approval store wired |
| Sprint 6 | Integration Test Suite | **Done** | 110/110 tests pass |
| Sprint 6C | Closure Hardening | **Done** | Typed artifacts + model wiring from role registry |
| Sprint 6D | Final Seal | **Done** | Structured extraction + strict approval enforcement |

## Phase 4.5 — Agent Governance Tuning (Planned)

| ID | Item | Notes |
|----|------|-------|
| B-036 | Structured artifact extraction | **Done** — Sprint 6D: LLM response → typed artifact parser |
| B-037 | Strict approval enforcement | **Done** — Sprint 6D: approve `<id>` / deny `<id>` |
| B-038 | Crash resume | resume_mission(mission_id) |
| B-039 | Tier C scoped extraction | Partial content delivery by role |
| B-040 | Token budget enforcement | Real-time per-role tracking |
| B-041 | E2E all complexity levels | Medium (7 roles), Complex (8 roles) |
| B-042 | Cost tuning from telemetry | Per-role token budgets from actual usage |
| B-043 | Prompt refinement for schema compliance | LLM output→schema mapping improvements |
| B-044 | build_command string template debt | Replace string concatenation with templates |

## Phase 4 — Reproducibility / DR

| ID | Item | Notes |
|----|------|-------|
| B-021 | Clean machine bootstrap | Fresh install smoke |
| B-022 | Backup / restore | Runtime state recovery |
| B-023 | Corrupted runtime recovery | Beyond stuck-task policy |
| B-024 | Deterministic redeploy | Reproducible from repo |

## Cleanup (no phase gate)

| ID | Item | Notes |
|----|------|-------|
| B-025 | Bootstrap heredoc reduction | 114KB monolithic deployer |
| B-026 | Dead-letter retention policy | No auto-purge defined |
| B-027 | Task directory retention policy | No auto-purge defined |
| B-028 | Stale .bak files | Bootstrap-created backups |
