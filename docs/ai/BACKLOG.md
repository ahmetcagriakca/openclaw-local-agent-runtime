# Backlog

**Last updated:** 2026-03-25

---

## Completed

| ID | Item | Sprint | Notes |
|----|------|--------|-------|
| B-029 | Deny forensic summary | Sprint 7 | `_aggregate_deny_forensics()` in controller |
| B-030 | Developer self-verification prompt | Sprint 7 | specialists.py hardened |
| B-031 | Tester verdict guidelines (unknown=fail) | Sprint 7 | D-068 aligned |
| B-032 | Model tracking per stage (agent_used) | Sprint 7 | Single-point propagation |
| B-033 | Approval sunset docstring | Sprint 7 | D-063 reference added |
| B-034 | Gate findings structured | Sprint 7 | 3 semantic states ready |
| B-035 | STATE.md + NEXT.md wording fix | Sprint 7 | "durable" → "state-persisted" |
| B-036 | ops/wsl/ versioned templates | Sprint 7 | 5 files created |
| B-037 | Capability manifest auto-gen | Sprint 7 | D-071 atomic write |
| B-038 | Sprint-End Doc Policy + validation script | Sprint 7 | D-077 frozen |

---

## Sprint 8 — Phase 5A-1: Backend Read Model

| ID | Item | Notes |
|----|------|-------|
| B-039 | FastAPI + Uvicorn setup (D-061) | Foundation |
| B-040 | Pydantic schemas freeze (D-067) | /api/v1/ contract |
| B-041 | MissionNormalizer (D-065) | Aggregation + precedence + cache |
| B-042 | IncrementalFileCache | File watcher + cache invalidation |
| B-043 | Per-source circuit breaker (D-072) | Fault isolation |
| B-044 | Atomic write utility (D-071) | System-wide helper |
| B-045 | CapabilityChecker service | Reads capabilities.json |
| B-046 | Localhost security (D-070) | Host + Origin validation |
| B-047 | Health snapshot FS migration (D-075) | ext4 state |
| B-048 | File owner/target FS matrix (GPT-4) | Sprint 8 kickoff item |
| B-049 | API test suite | Endpoint integration tests |
| B-050 | D-021→D-058 extraction to DECISIONS.md | Documentation debt |

---

## Sprint 9 — Phase 5A-2: Frontend Read-Only

| ID | Item | Notes |
|----|------|-------|
| B-051 | React scaffold + API client | mission-control/ |
| B-052 | DataQualityBadge + StaleBanner components | D-068 UI enforcement |
| B-053 | Mission List + Detail pages | Core UI |
| B-054 | Per-panel error boundary (D-072) | UI fault isolation |
| B-055 | Approval queue read-only | No buttons, Telegram note |

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

---

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

---

## Phase 4 — Reproducibility / DR

| ID | Item | Notes |
|----|------|-------|
| B-021 | Clean machine bootstrap | Fresh install smoke |
| B-022 | Backup / restore | Runtime state recovery |
| B-023 | Corrupted runtime recovery | Beyond stuck-task policy |
| B-024 | Deterministic redeploy | Reproducible from repo |

---

## Cleanup (no phase gate)

| ID | Item | Notes |
|----|------|-------|
| B-025 | Bootstrap heredoc reduction | 114KB monolithic deployer |
| B-026 | Dead-letter retention policy | No auto-purge defined |
| B-027 | Task directory retention policy | No auto-purge defined |
| B-028 | Stale .bak files | Bootstrap-created backups |
