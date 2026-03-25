# Phase 5 — Freeze Addendum: Blocking Fix Closure

**Date:** 2026-03-25
**Status:** FROZEN
**Scope:** 4 blocking fix'in yazılı closure'ı — Sprint 8 başlangıç ön koşulu
**Source:** Phase 5 Design v4.1 + GPT Final Review + GPT Sprint 7 Review

---

## BF-1: Response Freshness Semantics

**Frozen Definitions:**

| Kavram | Tanım | Formül |
|--------|-------|--------|
| Source age | Tek kaynağın eskiliği | `source.ageMs = now_ms - file.mtime_ms` |
| Response freshness | Response'un genel tazeliği | `freshnessMs = max(source.ageMs for source in sourcesUsed)` |
| generatedAt | Response üretim anı | `datetime.utcnow()` — cache hit'te bile güncellenir |
| Stale threshold | Kaynağın stale sayıldığı eşik | Response type'a göre değişir |

**Stale Thresholds:**

| Response Type | Threshold |
|--------------|-----------|
| Mission detail | 10s |
| Mission list | 30s |
| Health | 60s |
| Telemetry | 30s |
| Approval | 30s |

---

## BF-2: Startup Ownership Matrix

| Artifact | Write Owner | Write Trigger | Conflict Policy |
|----------|------------|---------------|-----------------|
| config/capabilities.json | Controller | Startup | Sole writer, atomic |
| logs/services.json | Per-service | Startup + heartbeat | Atomic R-M-W, own key only |
| logs/health-snapshot.json | PS Health Script | On-demand | Sole writer |
| logs/missions/*.json | Controller | Mission lifecycle | Sole writer, atomic |
| logs/policy-telemetry.jsonl | Multi-writer | Append-only | Each writer atomic JSONL line |
| logs/approvals/*.json | Approval Service | Request/response | Sole writer |

---

## BF-3: Migration Boundary Inventory (D-075)

| Artifact | Current FS | Target FS | Migration Sprint |
|----------|-----------|-----------|-----------------|
| logs/missions/*.json | ext4 | ext4 | — |
| logs/policy-telemetry.jsonl | ext4 | ext4 | — |
| logs/approvals/*.json | ext4 | ext4 | — |
| logs/health-snapshot.json | NTFS | ext4 | Sprint 8 |
| config/capabilities.json | ext4 | ext4 | — |
| logs/services.json | ext4 | ext4 | — |
| bridge/logs/bridge-audit.jsonl | NTFS | NTFS | — (stays) |

---

## BF-4: Source Precedence Table (D-065)

| Field | Primary | Fallback | Rule |
|-------|---------|----------|------|
| Mission status | state.json | mission.json | state > mission |
| Stage status | state.json | mission.json | state > mission |
| agentUsed | summary.json | mission.json | summary > mission |
| denyForensics | summary.json | telemetry.jsonl | summary > telemetry |
| gateResults | summary.json | mission.json | summary > mission |
| Policy deny counts | telemetry.jsonl | — | sole source |
| Mission timing | mission.json | state.json | mission > state |
| Health | health-snapshot.json | — | sole source |
| Capabilities | capabilities.json | — | sole source |
