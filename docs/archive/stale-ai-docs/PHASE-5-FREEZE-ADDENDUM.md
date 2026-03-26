# Phase 5 — Freeze Addendum: Blocking Fix Closure

**Date:** 2026-03-25
**Status:** FROZEN
**Scope:** 4 blocking fix'in yazılı closure'ı — Sprint 8 başlangıç ön koşulu
**Source:** Phase 5 Design v4.1 + GPT Final Review + GPT Sprint 7 Review

---

## BF-1: Response Freshness Semantics

**Problem:** Freshness hesaplama kuralı birden fazla yoruma açıktı.
`generatedAt`, source freshness, response freshness, stale threshold ayrımı yapılmamıştı.

### Frozen Definitions

| Kavram | Tanım | Formül |
|--------|-------|--------|
| **Source age** | Tek bir kaynağın ne kadar eski olduğu | `source.ageMs = now_ms - file.mtime_ms` |
| **Response freshness** | API response'un genel tazeliği | `freshnessMs = max(source.ageMs for source in sourcesUsed)` |
| **generatedAt** | Response'un üretildiği an | `datetime.utcnow()` — cache hit'te bile güncellenir |
| **Stale threshold** | Bir kaynağın stale sayıldığı eşik | Response type'a göre değişir (aşağıdaki tablo) |

### Tek Kural

> **Response freshness = age of the oldest source used.**
> En eski kaynak response'un tazeliğini belirler. Bir kaynak stale ise response stale'dir.

### Stale Threshold'lar

| Response Type | Threshold | Gerekçe |
|--------------|-----------|---------|
| Mission detail | 10s | Aktif mission izleme, düşük tolerans |
| Mission list | 30s | Liste genel bakış, orta tolerans |
| Health | 60s | Health data daha az dinamik |
| Telemetry | 30s | Policy event'leri orta frekanslı |
| Approval | 30s | Onay kuyruğu orta frekanslı |

### Source Freshness → DataQuality Mapping (D-079 amended)

| Koşul | dataQuality |
|-------|-------------|
| Tüm kaynaklar fresh (< threshold) | `fresh` |
| ≥1 kaynak mevcut, ≥1 eksik | `partial` (sourcesMissing doldurulur) |
| ≥1 kaynak stale (> threshold) | `stale` |
| Kaynak dosyası yok | `unknown` |
| Kaynak parse edilemez | `degraded` |
| Kaynak henüz oluşmamış (mission başlamadı) | `not_reached` |

**Öncelik (birden fazla durum):** `degraded > stale > partial > fresh`

---

## BF-2: Startup Ownership Matrix

**Problem:** `capabilities.json`, `services.json`, health registration gibi dosyaların
ownership'i belirsizdi. Birden fazla component aynı dosyaya yazabilir miydi, startup
sırası neyi garanti ederdi — bunlar tanımsızdı.

### Frozen Ownership Matrix

| Artifact | Write Owner | Read Consumers | Write Trigger | Conflict Policy |
|----------|-------------|---------------|---------------|-----------------|
| `config/capabilities.json` | Controller (`_update_capability_manifest`) | API CapabilityChecker | Controller init/startup | Controller sole writer, atomic write (D-071) |
| `logs/services.json` | **Single-key-per-service** (API, Controller, WMCP) | Health endpoint, other services | Service startup + heartbeat (30s) | Atomic read-modify-write. Her service kendi key'ini yazar. Heartbeat freshness ile canlılık tespiti. |
| `logs/health-snapshot.json` | PS Health Script (`oc-task-health.ps1`) | API Health endpoint | On-demand (Bridge `get_health`) | PS script sole writer, API read-only |
| `logs/preflight-state.json` | PS Preflight Script | PS Health Script, API | AtStartup (boot) | Preflight sole writer |
| `logs/missions/*.json` | Controller | API Normalizer | Mission lifecycle | Controller sole writer, atomic write |
| `logs/missions/*-state.json` | Controller | API Normalizer | Stage transitions | Controller sole writer |
| `logs/missions/*-summary.json` | Controller | API Normalizer | Mission complete | Controller sole writer |
| `logs/policy-telemetry.jsonl` | **Append-only multi-writer** (Controller + PolicyEnforcer) | API Telemetry endpoint | Append-only | Multi-writer OK: her writer kendi JSONL satırını atomic append. Satır = tek `\n`-terminated JSON line. |
| `logs/approvals/*.json` | Approval Service | API Approval endpoint | Approval request/response | ApprovalService sole writer |
| `logs/agent-audit.jsonl` | Agent Runner | API (future) | Agent call completion | Append-only |
| `bridge/logs/bridge-audit.jsonl` | Bridge Script | N/A (operator only) | Per-request | Bridge sole writer |

### Service Registration Protocol

| Service | Registration Key in services.json | Startup Order |
|---------|-----------------------------------|---------------|
| Mission Controller | `agent-controller` | 1st (always) |
| Mission Control API | `mission-control-api` | 2nd (after controller) |
| WMCP Server | `wmcp-server` | Independent |

**Kural:** Her service `logs/services.json` içinde yalnızca kendi key'ini yazar.
Atomic read-modify-write: dosyayı oku → kendi key'ini güncelle → atomic write.
Başka service'in key'ine dokunma.

---

## BF-3: Migration Boundary Inventory (D-075)

**Problem:** Hangi dosyanın hangi filesystem'de olduğu, hangisinin taşınması gerektiği,
taşımanın hangi sprint'te yapılacağı net değildi.

### Frozen Migration Boundary Table

| Artifact | Current Owner | Future Owner | Current FS | Target FS | Migration Sprint | Migration Method |
|----------|--------------|-------------|-----------|-----------|-----------------|-----------------|
| `logs/missions/*.json` | Controller | Controller | ext4 | ext4 | — (zaten hedefte) | N/A |
| `logs/missions/*-state.json` | Controller | Controller | ext4 | ext4 | — | N/A |
| `logs/missions/*-summary.json` | Controller | Controller | ext4 | ext4 | — | N/A |
| `logs/policy-telemetry.jsonl` | Controller/Enforcer | Controller/Enforcer | ext4 | ext4 | — | N/A |
| `logs/approvals/*.json` | Approval Service | Approval Service | ext4 | ext4 | — | N/A |
| `logs/health-snapshot.json` | PS Health Script | PS Health Script | **NTFS** | **ext4** | **Sprint 8** | PS script output path → ext4, API reads from ext4 |
| `logs/agent-audit.jsonl` | Agent Runner | Agent Runner | ext4 | ext4 | — | N/A |
| `config/capabilities.json` | Controller | Controller | ext4 | ext4 | — | N/A |
| `logs/services.json` | Per-service | Per-service | ext4 | ext4 | — | N/A |
| `logs/interventions/*.json` | API (5C) | API (5C) | — | ext4 | Sprint 11 | Created directly on ext4 |
| `bridge/logs/bridge-audit.jsonl` | Bridge (PS) | Bridge (PS) | NTFS | NTFS | — | Bridge runs on Windows, stays NTFS |
| `logs/preflight-state.json` | PS Preflight | PS Preflight | NTFS | NTFS | — | PS runtime, stays NTFS. API reads via health endpoint. |

### Migration Kuralları

1. **Cross-OS erişim yalnızca API üzerinden** (D-075). Windows → ext4 dosyaya doğrudan yazma yasak.
2. Sprint 8'de taşınacak tek dosya: `health-snapshot.json` (NTFS → ext4).
3. Bridge audit ve PS preflight-state NTFS'te kalır — bunlara API üzerinden erişilir, doğrudan dosya okuma yok.
4. Sprint 11'de oluşturulacak `interventions/` zaten ext4'te doğar.

---

## BF-4: MissionNormalizer Source Precedence

**Problem:** Normalizer birden fazla kaynaktan veri okuyor ama aynı alan farklı
kaynaklarda çeliştiğinde hangisinin kazanacağı tanımsızdı.

### Frozen Source Precedence Table

| Field Category | Primary Source | Fallback Source | Precedence Rule |
|---------------|---------------|-----------------|-----------------|
| **Mission status** | `*-state.json` | `missions/*.json` | State file wins — daha sık güncellenir |
| **Stage status** | `*-state.json` | `missions/*.json` | State file wins |
| **Stage details** (role, metadata) | `missions/*.json` | — | Mission file sole source |
| **agentUsed** | `*-summary.json` | `missions/*.json` (stage.agent_used) | Summary wins — post-processed |
| **denyForensics** | `*-summary.json` | `logs/policy-telemetry.jsonl` | Summary wins — structured, complete |
| **gateResults** | `*-summary.json` | `missions/*.json` (stage.gate_results) | Summary wins — post-processed |
| **Policy deny counts** | `logs/policy-telemetry.jsonl` | — | Telemetry sole source |
| **Approval status** | `logs/approvals/*.json` | — | Approval file sole source |
| **Health** | `logs/health-snapshot.json` | — | Health file sole source |
| **Capabilities** | `config/capabilities.json` | — | Capabilities file sole source |
| **Mission timing** (startedAt, finishedAt) | `missions/*.json` | `*-state.json` | Mission file wins — original timestamps |
| **Stage timing** | `missions/*.json` | `*-state.json` | Mission file wins |

### Precedence Özet Kuralı

> **Status: state > mission.** State file daha sık güncellenir, son durum burada.
> **Forensics: summary > telemetry.** Summary structured ve complete, telemetry raw event stream.
> **Timing: mission > state.** Original timestamps mission file'da.
> **Sole sources: değişmez.** Telemetry, approval, health, capabilities tek kaynaktan gelir.

### Çelişki Durumunda

| Senaryo | Davranış |
|---------|----------|
| Primary ve fallback farklı değer | Primary source kazanır |
| Primary source yok | Fallback kullanılır, `sourcesMissing` eklenmez (fallback yeterli) |
| Her iki kaynak da yok | `dataQuality: unknown`, ilgili alan `null` |
| Primary parse error | `dataQuality: degraded`, fallback denenir |
| Fallback da parse error | `dataQuality: degraded`, alan `null` |

---

## Doğrulama

```bash
# BF-1
grep "response freshness = age of the oldest source used" docs/ai/PHASE-5-FREEZE-ADDENDUM.md

# BF-2
grep "ownership matrix" docs/ai/PHASE-5-FREEZE-ADDENDUM.md

# BF-3
grep "migration boundary" docs/ai/PHASE-5-FREEZE-ADDENDUM.md

# BF-4
grep "source precedence" docs/ai/PHASE-5-FREEZE-ADDENDUM.md
```

---

## Sprint 8 Ön Koşulu

Bu belgedeki 4 tablo Sprint 8 implementasyonunun referans kaynağıdır:

- **8.2 (schemas):** BF-1 freshness + BF-4 precedence → schema field tanımları
- **8.4 (cache):** BF-1 stale threshold → cache invalidation kuralı
- **8.6 (normalizer):** BF-4 precedence → normalizer logic
- **8.12 (health migration):** BF-3 boundary → migration planı
- **8.13 (services.json):** BF-2 ownership → registration protocol

**Sprint 8, bu belge FROZEN olmadan başlamaz.**

---

*Phase 5 Freeze Addendum — OpenClaw Local Agent Runtime*
*4 Blocking Fix Closure*
*Date: 2026-03-25*
*Status: FROZEN*
