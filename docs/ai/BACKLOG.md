# Backlog — Vezir Platform

**Last updated:** 2026-03-27

Open items only. Completed items archived (Sprint 18, D-113).

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
| B-019 | Intent mapping refinement | Vezir conversation quality |
| B-020 | Standard task library | Common task definitions |

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
| B-050 | D-021→D-058 extraction to DECISIONS.md | Documentation debt |
