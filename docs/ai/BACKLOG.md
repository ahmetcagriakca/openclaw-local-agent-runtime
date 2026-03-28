# Backlog — Vezir Platform

**Last updated:** 2026-03-28
**Phase:** 7 active
**Archived:** B-001, B-002, B-015, B-017, B-020, B-021, B-024, B-050 (done in S23-S30)

---

## P1 — Security & Execution Safety

| ID | Item | Category | Notes |
|----|------|----------|-------|
| B-003 | Task risk classification | Security | Risk scoring framework for tool/mission operations |
| B-004 | Filesystem confinement | Security | Deeper sandboxing for agent execution |
| B-006 | Encrypted secret storage | Security | auth.json plaintext → encrypted (Vault/DPAPI) |
| B-011 | Transport encryption | Security | mTLS or equivalent for inter-service communication |
| B-012 | Full request idempotency | Security | Pending dedupe exists, need full idempotency keys |
| B-005 | HTTP rate limiting | Security | Per-endpoint rate limits (beyond guardrail quotas) |
| B-008 | Audit log tamper resistance | Security | Integrity verification, retention policy |

## P1 — Product Core (Phase 7)

| ID | Item | Category | Notes |
|----|------|----------|-------|
| B-101 | Scheduled mission execution | Product | D-120 frozen, implementation pending |
| B-102 | Full approval inbox UI | Product | D-121 inbox with approve/reject/expire in dashboard |
| B-103 | Mission presets / quick-run | Product | Pre-configured templates for common workflows |
| B-104 | Template parameter UI | Product | Form-based parameter input for run-from-template |

## P2 — Operational & Policy

| ID | Item | Category | Notes |
|----|------|----------|-------|
| B-105 | Cost/outcome dashboard | Operations | ROI visibility, token cost tracking, showback |
| B-106 | Retry/DLQ/replay/resume | Operations | Failure recovery automation |
| B-107 | Policy engine | Operations | Who can run what, under which conditions |
| B-108 | Agent health / capability view | Operations | Worker liveness, heartbeat, capability registry |
| B-016 | Task result artifact access | Operations | Beyond outputPreview — full artifact download |
| B-022 | Backup / restore | Operations | Runtime state snapshot and recovery |
| B-023 | Corrupted runtime recovery | Operations | Beyond stuck-task policy |
| B-026 | Dead-letter retention policy | Operations | Auto-purge with configurable TTL |
| B-013 | Richer policyContext | Operations | Runtime parameter expansion for policy decisions |
| B-014 | timeoutSeconds in contract | Operations | External timeout field for tool contracts |

## P2 — Developer Experience

| ID | Item | Category | Notes |
|----|------|----------|-------|
| B-109 | Template/plugin scaffolding CLI | DevEx | `vezir create-plugin <name>` / `vezir create-template <name>` |
| B-110 | Contract test pack | DevEx | Plugin/provider/MCP tool contract tests |
| B-111 | Mission replay / fixture runner | DevEx | Deterministic replay for debugging |
| B-112 | Local dev sandbox / seeded demo | DevEx | One-command demo with sample data |
| B-113 | Docs-as-product pack | DevEx | Operator guide, template author guide, plugin guide |

## P3 — Cleanup & Nice-to-Have

| ID | Item | Category | Notes |
|----|------|----------|-------|
| B-007 | Automatic secret rotation | Security | Beyond SECRETS-CONTRACT manual rotation |
| B-009 | Multi-source allowlist | Security | Per-channel authorization lists |
| B-010 | WMCP credential replacement | Security | Replace local-mcp-12345 |
| B-018 | Dynamic sourceUserId | DevEx | WSL wrapper improvement |
| B-019 | Intent mapping refinement | Product | Vezir conversation quality |
| B-025 | Bootstrap heredoc reduction | Cleanup | 114KB monolithic deployer |
| B-027 | Task directory retention | Cleanup | No auto-purge defined |
| B-028 | Stale .bak files | Cleanup | Bootstrap-created backups |

## P3 — Future Platform (Phase 8+)

| ID | Item | Category | Notes |
|----|------|----------|-------|
| B-114 | Knowledge/connector input layer | Product | Mission'lar gerçek kullanıcı verisiyle çalışır |
| B-115 | Audit export / compliance bundle | Operations | Exportable governance evidence |
| B-116 | Multi-tenant isolation | Product | Full tenant boundary enforcement |
| B-117 | Grafana dashboard pack | Operations | Pre-built observability dashboards |
| B-118 | Plugin marketplace / discovery | Product | Community plugin ecosystem |

---

## Sprint 31 Candidates (GPT operator recommendation)

Security-first approach before Phase 7 feature expansion:

1. **B-003** Task risk classification
2. **B-004** Filesystem confinement
3. **B-012** Full request idempotency
4. **B-005** HTTP rate limiting
5. **B-013** Richer policyContext

Rationale: Security zemini ve execution safety düzelmeden scheduled missions gibi user-facing genişleme açmak hatalı.
