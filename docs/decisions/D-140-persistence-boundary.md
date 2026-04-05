# D-140: Persistence Boundary Contract

**Phase:** Sprint 66 | **Status:** Frozen | **Date:** 2026-04-06

## Context

Vezir uses file-based persistence (D-106). As the platform grows, the implicit boundary between store types creates ambiguity: which stores tolerate contention, which require append-only integrity, and which are read-heavy config. This decision stratifies all persistence into five explicit categories with distinct write semantics, integrity contracts, and scaling observation methods.

## Decision

### Store Stratification

All Vezir persistence falls into exactly five categories:

```
+-------------------------------------------------------------------+
|                    VEZIR PERSISTENCE BOUNDARY                      |
+-------------------------------------------------------------------+
|                                                                    |
|  HOT STATE (read-write, atomic, contention-sensitive)              |
|  ┌─────────────────────────────────────────────────────┐           |
|  │  MissionStore     → logs/mission-history.json       │           |
|  │  ApprovalStore    → logs/approvals/apv-*.json       │           |
|  │  DLQStore         → logs/dlq.json                   │           |
|  │  ServiceHeartbeat → (in-memory, periodic flush)     │           |
|  └─────────────────────────────────────────────────────┘           |
|  Write: atomic_write_json (D-071)                                  |
|  Lock: threading.Lock per store                                    |
|  Scaling signal: file lock wait time under concurrent writers      |
|                                                                    |
|  AUDIT LOG (append-only, hash-chained, tamper-evident)             |
|  ┌─────────────────────────────────────────────────────┐           |
|  │  AuditIntegrity   → logs/audit/audit.jsonl          │           |
|  │  PolicyTelemetry  → logs/policy-telemetry.jsonl     │           |
|  └─────────────────────────────────────────────────────┘           |
|  Write: append (JSONL), SHA-256 hash chain (D-129)                 |
|  Lock: append lock (single writer)                                 |
|  Scaling signal: replay/filter latency over growing log            |
|                                                                    |
|  ARTIFACT STORE (write-once per sprint, read-many)                 |
|  ┌─────────────────────────────────────────────────────┐           |
|  │  Mission artifacts → logs/missions/{id}/             │           |
|  │  Evidence packets  → evidence/sprint-{N}/            │           |
|  │  TraceStore        → logs/trace-history.json         │           |
|  │  MetricStore       → logs/metric-history.json        │           |
|  └─────────────────────────────────────────────────────┘           |
|  Write: atomic_write_json or file creation (D-071)                 |
|  Lock: threading.Lock (low contention — mostly writes at close)    |
|  Scaling signal: startup scan latency (file count x parse time)    |
|                                                                    |
|  PLUGIN STATE (registry-scoped, thread-locked)                     |
|  ┌─────────────────────────────────────────────────────┐           |
|  │  PluginMarketplace → logs/plugin-marketplace.json   │           |
|  │  PluginRegistry    → (in-memory, manifest-loaded)   │           |
|  │  PluginConfig      → config/plugins/{name}.json     │           |
|  └─────────────────────────────────────────────────────┘           |
|  Write: atomic_write_json (D-071), per-plugin lock (D-136)         |
|  Lock: Store-level lock per plugin ID                              |
|  Scaling signal: install/uninstall contention frequency             |
|                                                                    |
|  CONFIG (startup-loaded, rarely written)                           |
|  ┌─────────────────────────────────────────────────────┐           |
|  │  Policies          → config/policies/*.yaml         │           |
|  │  Capabilities      → config/capabilities.json       │           |
|  │  Features          → config/features.json           │           |
|  │  Secrets           → config/secrets.enc.json        │           |
|  │  Alert rules       → config/alert-rules.json        │           |
|  │  Secret rotation   → config/secret-rotation-meta.json│          |
|  │  Allowlists        → config/allowlists/*.yaml       │           |
|  │  Grafana templates → config/grafana/*.json          │           |
|  └─────────────────────────────────────────────────────┘           |
|  Write: atomic_write_json (D-071), operator-triggered only         |
|  Lock: threading.Lock (rare writes)                                |
|  Scaling signal: startup load time (config file count)             |
|                                                                    |
+-------------------------------------------------------------------+
```

### Integrity Contracts per Category

| Category | Write Semantics | Integrity | Concurrency | Recovery |
|----------|----------------|-----------|-------------|----------|
| Hot state | atomic_write_json (temp → fsync → rename) | Last-write-wins per file | threading.Lock | Re-read from disk |
| Audit log | Append JSONL, hash-chain (D-129) | Tamper-evident, verifiable | Single-writer append lock | Hash-chain verify CLI |
| Artifact | atomic_write_json or file create | Immutable after write | Low contention (sprint-scoped) | Re-create from source |
| Plugin state | atomic_write_json, per-plugin lock | Per-plugin isolation | Store-level lock per ID | Re-scan manifests |
| Config | atomic_write_json, operator-triggered | Startup-validated (D-057) | Rare writes, read-heavy | Re-deploy from repo |

### Scaling Observation Method

Migration away from file-based persistence is NOT pre-scheduled. Instead, scaling pressure is detected through observation:

**What to measure (when investigating performance):**

1. **Concurrent writer contention** — File lock wait time in hot-state stores. If MissionStore or ApprovalStore lock waits become observable in trace spans, contention exists.

2. **Startup scan latency** — Time to load all mission/artifact files at startup. If parse-and-load dominates startup time, file count has grown beyond comfortable bounds.

3. **Replay/query latency** — Time to filter or scan audit logs (JSONL). If audit export or integrity verification takes minutes, log size warrants investigation.

4. **Approval poll I/O cost** — Frequency of approval file reads vs actual state changes. If poll-to-change ratio grows large, polling overhead is wasteful.

**Migration evaluation trigger:** Any of the above measured and found degraded, OR operator-reported issue. NOT a threshold like "missions > N" or "operators > N".

**What migration looks like (when needed):**
- Hot state → SQLite or PostgreSQL (connection pool, row-level locking)
- Audit log → Append-only DB table with hash-chain column
- Artifact store → Object storage or compressed archive
- Plugin state → Likely stays file-based (low volume)
- Config → Stays file-based (repo-managed)

Each category migrates independently. No big-bang migration.

### Non-Negotiable Rules

1. **Atomic writes everywhere.** All mutable stores use D-071 atomic write. No partial writes, no corruption on crash.
2. **Category boundaries are explicit.** A store belongs to exactly one category. Cross-category access goes through service layer.
3. **Audit logs are append-only.** No in-place mutation of audit/telemetry JSONL files. Hash chain (D-129) is the integrity guarantee.
4. **No hardcoded numeric thresholds.** Scaling decisions are observation-driven, not predictive.
5. **File-based is the current contract.** All stores are file-based until measured evidence justifies migration.

## Trade-offs

- **Pro:** Explicit boundaries prevent accidental coupling between store types.
- **Pro:** Observation-based scaling avoids premature optimization and speculative thresholds.
- **Pro:** Independent migration per category reduces blast radius.
- **Con:** File-based stores have inherent concurrency limits under high load.
- **Con:** No pre-defined migration trigger means operator must actively monitor.
- **Accepted:** Single-operator platform with bounded mission volume. File-based stores are appropriate for current and near-term scale.

## Validation

- Store stratification diagram reviewed: 5 categories, all stores assigned.
- No numeric thresholds in migration triggers.
- Measurement methods documented for each scaling signal.
- Existing D-071 (atomic write), D-106 (file store), D-129 (hash chain) referenced and compatible.

## References

- D-071: Atomic file writes system-wide
- D-106: Persistence Model — JSON File Store
- D-129: Secret Storage + Audit Integrity Contract
- D-136: Plugin Marketplace + Installer Contract
