# Sprint 8 — Phase 5A-1: Backend Read Model — Task Breakdown

**Sprint Hedefi:** FastAPI backend, frozen API schemas, MissionNormalizer, cache, security.
Bu sprint'ten sonra API contract dondurulmuş olur (D-067).

**Risk:** HIGH — 3 iç milestone ile yönetilecek (GPT-3)
**Ön koşul 1:** Sprint 7 tamamlanmış ✅ (D-078 E2E waiver: 2/4 pass, fail'ler scope dışı)
**Ön koşul 2:** Phase 5 Freeze Addendum FROZEN ✅ (`docs/ai/PHASE-5-FREEZE-ADDENDUM.md`)
**Frozen Decisions:** D-061, D-064, D-065, D-067, D-068/D-079, D-070, D-071, D-072, D-073, D-074, D-075, D-080
**Referans Tabloları:** BF-1 (freshness), BF-2 (ownership), BF-3 (migration), BF-4 (precedence)

---

## E2E Bulgusu — Pre-Sprint Blocker

T-OT-4 (complex) E2E'de `_save_mission()` corrupt JSON oluşturdu (truncated write).
`_save_mission()` hâlâ `json.dump()` kullanıyor — D-071 (atomic writes system-wide) ihlali.

**Aksiyon:** Task 8.1 (atomic_write.py) üretilince, `_save_mission()` da migrate edilecek.
Bu Sprint 8'in ilk işi — normalizer corrupt JSON okursa `degraded` döner.

---

## Milestone Yapısı

```
8α Foundation (Hafta 1 ilk yarı)
    8.0★ File owner/FS matrix review
    8.1  atomic_write.py + _save_mission migration
    8.2  schemas.py (FREEZE)
    8.3  capabilities.py
    8.4  cache.py
    8.5  circuit_breaker.py
    ──── Checkpoint: pip install ok, schemas import, cache unit test ────

8β Core Logic (Hafta 1 ikinci yarı)
    8.6  normalizer.py
    ──── Checkpoint: normalizer unit test, precedence, freshness ────

8γ Endpoints + Integration (Hafta 2)
    8.7  server.py (FastAPI + security)
    8.8  mission_api.py
    8.9  approval_api.py (R/O)
    8.10 telemetry_api.py
    8.11 health_api.py
    8.12 health snapshot FS migration
    8.13 services.json + startup
    8.14 log rotation config
    8.15 API test suite + sprint-end doc validation
    ──── Checkpoint: curl tüm endpoint → 200, health ext4 ────
```

---

## Bağımlılık Grafiği

```
8.0★ (FS matrix) ──┐
8.1 (atomic_write) ─┼──▶ 8.6 (normalizer) ──▶ 8.8–8.11 (endpoints)
8.2 (schemas)    ──┤                           │
8.4 (cache)      ──┤                           ▼
8.5 (breaker)    ──┘                      8.7 (server) ──▶ 8.15 (tests)
8.3 (capability) ───────────────────────────────┘
                                          8.12 (health FS)
                                          8.13 (services.json)
                                          8.14 (log rotation)
```

**Kritik yol:** 8.1 → 8.2 → 8.6 → 8.7 → 8.8 → 8.15

---

## Task 8.0★ — File Owner / Target FS Matrix Review

| Alan | Değer |
|------|-------|
| **ID** | 8.0★ |
| **Milestone** | Kickoff |
| **Dosya** | Docs (review only) |
| **Efor** | XS |
| **Bağımlılık** | — |

### Context

GPT-4 review'den gelen kickoff maddesi. v4.1 Section 17'deki file inventory'yi
doğrula. Her dosyanın write owner'ı ve target FS'i netleşmeli.

### Scope

Aşağıdaki tabloyu repo gerçekliğine göre doğrula ve güncelle:

| Dosya | Write Owner | Target FS | Migration |
|-------|-------------|-----------|-----------|
| `logs/missions/*.json` | Controller | ext4 ✅ | — |
| `logs/missions/*-state.json` | Controller | ext4 ✅ | — |
| `logs/missions/*-summary.json` | Controller | ext4 ✅ | — |
| `logs/policy-telemetry.jsonl` | Controller/Enforcer | ext4 ✅ | — |
| `logs/approvals/*.json` | Approval Service | ext4 ✅ | — |
| `logs/health-snapshot.json` | PS Health Script | **ext4 (taşınacak)** | **8.12** |
| `logs/agent-audit.jsonl` | Agent Runner | ext4 ✅ | — |
| `config/capabilities.json` | Controller (auto) | ext4 ✅ | — |
| `logs/services.json` | Single-key-per-service + heartbeat (D-080) | ext4 ✅ | — |
| `logs/interventions/*.json` | API (5C) | ext4 | Sprint 11 |

### Kabul Kriterleri

1. Tablo review edilmiş, repo gerçekliğiyle eşleşiyor
2. Çakışan write owner yok (bir dosyaya 2 writer yok)
3. health-snapshot migration planı netleşmiş (Task 8.12)

### Doğrulama

```bash
grep -rn "open\|write\|json.dump\|Save-OcJson" agent/ --include="*.py" | grep -i "log\|state\|mission\|summary\|telemetry"
```

---

## Task 8.1 — Atomic Write Helper + `_save_mission` Migration

| Alan | Değer |
|------|-------|
| **ID** | 8.1 |
| **Milestone** | 8α |
| **Dosya** | `agent/utils/atomic_write.py`, `agent/mission/controller.py` |
| **Efor** | S |
| **Bağımlılık** | — |
| **Bağımlı** | 8.6, 8.12, 8.13 |

### Context

D-071: atomic writes system-wide. `_update_capability_manifest()` zaten atomic pattern
kullanıyor (Sprint 7). Ama `_save_mission()` hâlâ `json.dump()` — T-OT-4'te corrupt JSON
üretti. Utility'yi çıkart, tüm JSON yazımları buraya bağlansın.

### Scope

**A. Utility oluştur:**

```python
# agent/utils/atomic_write.py
import json, os, tempfile

def atomic_write_json(path: str, data: dict, indent: int = 2) -> None:
    """Write JSON atomically: temp → fsync → replace."""
    dir_path = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

**B. `_save_mission()` migrate et:**
- Mevcut `json.dump(data, f)` → `atomic_write_json(path, data)` 
- `_update_capability_manifest()` inline atomic code → `atomic_write_json()` çağrısı

**C. `_emit_mission_summary()` migrate et:**
- Summary JSON yazımını da atomic yap

### Kabul Kriterleri

1. `agent/utils/atomic_write.py` mevcut
2. `_save_mission()` atomic_write_json kullanıyor
3. `_update_capability_manifest()` atomic_write_json kullanıyor
4. `_emit_mission_summary()` atomic_write_json kullanıyor
5. 129+ test, 0 failure
6. E2E T-OT-4 benzeri crash'ta corrupt JSON oluşmaz

### Doğrulama

```bash
grep "atomic_write_json" agent/mission/controller.py
grep "json.dump" agent/mission/controller.py  # 0 match beklenir
python -c "from agent.utils.atomic_write import atomic_write_json; print('OK')"
python -m pytest tests/ -x --tb=short
```

---

## Task 8.2 — Pydantic Schemas (FREEZE)

| Alan | Değer |
|------|-------|
| **ID** | 8.2 |
| **Milestone** | 8α |
| **Dosya** | `agent/api/schemas.py` |
| **Efor** | M |
| **Bağımlılık** | — |
| **Bağımlı** | 8.6, 8.7, 8.8–8.11, 8.15 |

### Context

D-067: Schema frozen after 5A-1. Post-freeze additive-only. Bu dosya Sprint 8'in
en kritik çıktısı — tüm frontend (Sprint 9) bu contract'a bağlı.

D-068/D-079: 6 data state (fresh, partial, stale, degraded, unknown, not_reached)
schema'da explicit olmalı.

**Freeze Addendum referansları:**
- BF-1 freshness semantics → `ResponseMeta.freshnessMs` hesaplama kuralı
- BF-1 stale thresholds → response type'a göre threshold tablosu
- BF-4 source precedence → `SourceInfo` field tanımları

### Scope

Pydantic v2 models:

```python
# Core enums
class DataQuality(str, Enum):
    """Response-level data quality indicator (D-068)."""
    FRESH = "fresh"             # Tüm kaynaklar mevcut ve threshold altında
    PARTIAL = "partial"         # ≥1 kaynak mevcut ama ≥1 eksik
    STALE = "stale"             # ≥1 kaynak threshold üzerinde
    DEGRADED = "degraded"       # ≥1 kaynak parse error / circuit open
    UNKNOWN = "unknown"         # Tüm kaynaklar eksik — veri yok
    NOT_REACHED = "not_reached" # Kaynak henüz oluşmadı

class MissionState(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    GATE_CHECK = "gate_check"
    REWORK = "rework"
    APPROVAL_WAIT = "approval_wait"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    TIMED_OUT = "timed_out"

# Response envelope
class SourceInfo(BaseModel):
    name: str
    ageMs: int
    status: DataQuality

class ResponseMeta(BaseModel):
    freshnessMs: int
    dataQuality: DataQuality
    sourcesUsed: list[SourceInfo]
    sourcesMissing: list[str]
    generatedAt: str

# Mission models
class StageDetail(BaseModel):
    index: int
    role: str
    agentUsed: str | None
    status: str
    gateResults: dict | None
    denyForensics: dict | None
    startedAt: str | None
    finishedAt: str | None

class MissionSummary(BaseModel):
    missionId: str
    state: MissionState
    stages: list[StageDetail]
    denyForensics: list[dict]
    startedAt: str | None
    completedAt: str | None
    totalDurationMs: int | None

class MissionListItem(BaseModel):
    missionId: str
    state: MissionState
    dataQuality: DataQuality
    startedAt: str | None
    stageSummary: str

# Capability + Health models
class CapabilityStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"

class CapabilityEntry(BaseModel):
    name: str
    status: CapabilityStatus  # bool değil — tri-state
    since: str | None
    detail: str | None

class ComponentHealth(BaseModel):
    name: str
    status: str               # ok | degraded | error | unknown
    lastCheckAt: str | None
    detail: str | None

# Approval + Telemetry models
class ApprovalEntry(BaseModel):
    id: str
    missionId: str
    status: str
    requestedAt: str
    respondedAt: str | None

class TelemetryEntry(BaseModel):
    type: str                  # policy_deny | gate_check | stage_complete
    timestamp: str
    missionId: str | None      # ilişkili mission (varsa)
    sourceFile: str            # JSONL provenance
    data: dict

# API wrapper responses (tüm endpoint'ler bunları döner)
class MissionDetailResponse(BaseModel):
    meta: ResponseMeta
    mission: MissionSummary

class MissionListResponse(BaseModel):
    meta: ResponseMeta
    missions: list[MissionListItem]

class StageListResponse(BaseModel):
    meta: ResponseMeta
    stages: list[StageDetail]

class HealthResponse(BaseModel):
    meta: ResponseMeta
    status: str  # ok | degraded | error
    components: dict[str, ComponentHealth]

class ApprovalListResponse(BaseModel):
    meta: ResponseMeta
    approvals: list[ApprovalEntry]

class TelemetryResponse(BaseModel):
    meta: ResponseMeta
    events: list[TelemetryEntry]

class CapabilitiesResponse(BaseModel):
    meta: ResponseMeta
    capabilities: dict[str, CapabilityEntry]
```

### Kabul Kriterleri

1. Tüm model'ler Pydantic v2 `BaseModel` extends
2. `DataQuality` enum 6 state (D-079): fresh, partial, stale, degraded, unknown, not_reached
3. `MissionState` enum 10 state
4. `ResponseMeta` her response'ta zorunlu
5. Sprint 7 field'ları: `agentUsed`, `gateResults`, `denyForensics`
6. `python -c "from agent.api.schemas import MissionDetailResponse; print('OK')"`

**⚠ Bu dosya FREEZE sonrası additive-only. Sprint 8 çıkışında dondurulur.**

---

## Task 8.3 — Capability Checker

| Alan | Değer |
|------|-------|
| **ID** | 8.3 |
| **Milestone** | 8α |
| **Dosya** | `agent/api/capabilities.py` |
| **Efor** | S |
| **Bağımlılık** | 8.2 |
| **Bağımlı** | 8.7 |

### Scope

`CapabilityChecker` class: `config/capabilities.json` okur, mtime caching.
`get_status(name)` → `CapabilityStatus` (tri-state: available/unavailable/unknown).
`is_available(name)` → `bool` (convenience, `get_status() == AVAILABLE`).
Bozuk/eksik manifest → tüm capability'ler `UNKNOWN`, graceful degradation.

### Kabul Kriterleri

1. `get_status("deny_forensics")` → `CapabilityStatus.AVAILABLE`
2. `is_available("deny_forensics")` → `True` (convenience)
3. Manifest yoksa → tüm status `UNKNOWN`, exception yok
4. Bozuk JSON → tüm status `UNKNOWN`, crash yok
5. File mtime caching çalışıyor

---

## Task 8.4 — Incremental File Cache

| Alan | Değer |
|------|-------|
| **ID** | 8.4 |
| **Milestone** | 8α |
| **Dosya** | `agent/api/cache.py` |
| **Efor** | M |
| **Bağımlılık** | — |
| **Bağımlı** | 8.6 |

### Scope

`IncrementalFileCache`: mtime/size based invalidation.
JSON → full read. JSONL → incremental offset tracking (yeni satırlar).
`stats()` → hit/miss/invalidation counts.

### Kabul Kriterleri

1. Cache hit: ikinci read disk'e gitmez
2. mtime değişti → invalidate → re-read
3. Bozuk JSON → `None` + error flag, crash yok
4. JSONL incremental append desteği
5. `stats()` doğru

---

## Task 8.5 — Circuit Breaker

| Alan | Değer |
|------|-------|
| **ID** | 8.5 |
| **Milestone** | 8α |
| **Dosya** | `agent/api/circuit_breaker.py` |
| **Efor** | S |
| **Bağımlılık** | — |
| **Bağımlı** | 8.6 |

### Scope

D-072: Per-source circuit breaker. CLOSED → OPEN (3 failure) → HALF_OPEN (30s sonra).
Source'lar bağımsız.

### Kabul Kriterleri

1. 3 ardışık failure → OPEN
2. OPEN'da fn çağrılmaz → `CircuitOpenError`
3. recovery_timeout → HALF_OPEN → 1 success → CLOSED
4. Source isolation: A OPEN, B CLOSED

---

## Task 8.6 — MissionNormalizer

| Alan | Değer |
|------|-------|
| **ID** | 8.6 |
| **Milestone** | 8β |
| **Dosya** | `agent/api/normalizer.py` |
| **Efor** | L |
| **Bağımlılık** | 8.1, 8.2, 8.4, 8.5 |
| **Bağımlı** | 8.8–8.11 |

### Context

D-065: Normalized API. Bu sprint'in **en büyük ve en riskli** task'ı.

**Freeze Addendum referansları (zorunlu — implementasyon bu tablolara bağlı):**
- BF-1: freshness semantics → `freshnessMs` hesaplama kuralı
- BF-1: stale thresholds → response type'a göre eşik tablosu
- BF-4: source precedence → field-level primary/fallback kaynaklar
- BF-2: ownership matrix → hangi kaynak kimin

### Source Precedence (BF-4 Freeze Addendum'dan)

| Veri | Primary | Fallback | Kural |
|------|---------|----------|-------|
| Mission status | state.json | mission.json | state > mission |
| Stage status | state.json | mission.json | state > mission |
| Stage details | mission.json | — | tek kaynak |
| Agent used | summary.json | mission.json | summary > mission |
| Gate results | summary.json | mission.json | summary > mission |
| Deny forensics | summary.json | telemetry.jsonl | summary > telemetry |
| Policy deny counts | telemetry.jsonl | — | tek kaynak |
| Health | health-snapshot.json | — | tek kaynak |
| Approvals | approvals/*.json | — | tek kaynak |
| Capabilities | capabilities.json | — | tek kaynak |
| Mission timing | mission.json | state.json | mission > state |

### Freshness (BF-1 Freeze Addendum'dan)

- `freshnessMs = max(source.ageMs)` — en eski kaynak belirleyici
- Stale thresholds:

| Response Type | Threshold |
|--------------|-----------|
| Mission detail | 10s |
| Mission list | 30s |
| Health | 60s |
| Telemetry | 30s |
| Approval | 30s |

### DataQuality Mapping (GPT review fix applied)

| Koşul | dataQuality | sourcesMissing |
|-------|-------------|----------------|
| Tüm source'lar taze (< threshold) | `fresh` | `[]` |
| ≥1 source mevcut, ≥1 eksik | `partial` | eksik kaynak isimleri |
| ≥1 source stale (> threshold) | `stale` | `[]` |
| ≥1 source corrupt / circuit open | `degraded` | `[]` |
| Tüm source'lar eksik | `unknown` | tüm beklenen kaynaklar |
| Kaynak henüz oluşmamış | `not_reached` | `[]` |

**Öncelik (birden fazla durum):** `degraded > stale > partial > fresh`

### Kabul Kriterleri

1. Precedence unit test geçiyor
2. freshnessMs doğru
3. Missing source → API düşmez, sourcesMissing'te listeleniyor
4. Corrupt JSON → degraded, API düşmez
5. Circuit breaker entegre
6. Cache entegre

---

## Task 8.7 — FastAPI Server + Security

| Alan | Değer |
|------|-------|
| **ID** | 8.7 |
| **Milestone** | 8γ |
| **Dosya** | `agent/api/server.py` |
| **Efor** | M |
| **Bağımlılık** | 8.2, 8.6 |

### Scope

D-061: FastAPI. D-064: Port 8003. D-070: Localhost security.
D-074: Startup sequence (config → FS → cache → normalizer → serve).

### Kabul Kriterleri

1. `uvicorn agent.api.server:app --host 127.0.0.1 --port 8003` başlıyor
2. Non-localhost Host → 403
3. CORS 127.0.0.1:3000 + localhost:3000
4. Swagger UI `/docs`

---

## Task 8.8–8.11 — API Endpoints

| Task | Endpoint | Response Type | Efor |
|------|----------|--------------|------|
| 8.8 | `GET /api/v1/missions` | `MissionListResponse` | M |
| 8.8 | `GET /api/v1/missions/{id}` | `MissionDetailResponse` | |
| 8.8 | `GET /api/v1/capabilities` | `CapabilitiesResponse` | |
| 8.9 | `GET /api/v1/approvals` (R/O) | `ApprovalListResponse` | S |
| 8.10 | `GET /api/v1/telemetry?limit=50&mission_id=X` | `TelemetryResponse` | M |
| 8.11 | `GET /api/v1/health` | `HealthResponse` | S |

Tüm endpoint'ler normalizer'dan data alır, ResponseMeta ekler.
Missing data → graceful degradation, 500 yok.

---

## Task 8.12 — Health Snapshot FS Migration

| Alan | Değer |
|------|-------|
| **ID** | 8.12 |
| **Milestone** | 8γ |
| **Efor** | S |
| **Bağımlılık** | 8.0★, 8.1 |

D-075: health-snapshot.json ext4'e taşınacak. Geçiş stratejisi 8.0★'da netleşir.

---

## Task 8.13 — services.json + Startup (Heartbeat Model — D-080)

| Alan | Değer |
|------|-------|
| **ID** | 8.13 |
| **Milestone** | 8γ |
| **Efor** | S |
| **Bağımlılık** | 8.1, 8.7 |

### Scope

Service registration with **heartbeat freshness** — crash-safe, fake live üretmez.

```python
# Her service kendi key'ini yazar:
{
    "mission-control-api": {
        "status": "running",         # running | stopped
        "port": 8003,
        "pid": 12345,
        "startedAt": "2026-03-25T..Z",
        "lastHeartbeatAt": "2026-03-25T..Z",  # periyodik güncelleme
        "heartbeatIntervalS": 30
    }
}
```

**Canlılık kuralı:**
- `lastHeartbeatAt + (heartbeatIntervalS × 2) > now` → alive
- Aksi halde → stale registration → health endpoint `degraded`
- Crash → heartbeat durur → threshold aşılır → otomatik algılanır
- Clean shutdown → `status: "stopped"` (bonus, zorunlu değil)

**Heartbeat mekanizması:** Background task (asyncio), her 30s `lastHeartbeatAt` güncelle.
Atomic read-modify-write: dosyayı oku → kendi key'ini güncelle → `atomic_write_json()`.

### Kabul Kriterleri

1. Startup'ta `services.json` güncelleniyor
2. `lastHeartbeatAt` periyodik güncelleniyor
3. Crash simulation: process kill → heartbeat durur → stale olarak tespit edilir
4. Başka service'in key'ine dokunulmuyor

---

## Task 8.14 — Log Rotation Config

| Alan | Değer |
|------|-------|
| **ID** | 8.14 |
| **Milestone** | 8γ |
| **Efor** | XS |

D-073: 10MB / 5 files / 14 days. `RotatingFileHandler`.

---

## Task 8.15 — API Test Suite + Sprint-End Doc Validation

| Alan | Değer |
|------|-------|
| **ID** | 8.15 |
| **Milestone** | 8γ |
| **Efor** | M |
| **Bağımlılık** | 8.1–8.14 |

### Scope

**Tests:** cache (5+), circuit breaker (4+), normalizer (8+), API integration (per-endpoint), security (Host check). 129+ existing + new, 0 failure.

**Doc validation:** `python tools/validate_sprint_docs.py --sprint 8` → 0 FAIL.

---

## Sprint 8 Çıkış Kriterleri

| # | Kriter | Task |
|---|--------|------|
| 1 | 8α: schemas import, cache test, breaker test | 8.2, 8.4, 8.5 |
| 2 | 8β: normalizer test, precedence, freshness | 8.6 |
| 3 | 8γ: curl tüm endpoint → 200 | 8.7–8.11 |
| 4 | freshnessMs = max(source ages) | 8.6 |
| 5 | Stale thresholds per response type | 8.6 |
| 6 | Missing source → sourcesMissing + `partial`, API lives | 8.6 |
| 7 | Corrupt JSON → `degraded`, API lives | 8.6, 8.5 |
| 8 | Precedence rules verified | 8.6 |
| 9 | Atomic write tüm JSON yazımlarında | 8.1 |
| 10 | D-070 security | 8.7 |
| 11 | health-snapshot ext4 (D-075) | 8.12 |
| 12 | FS matrix reviewed | 8.0★ |
| 13 | **Schema FROZEN** (D-067) | 8.2 |
| 14 | Doc validation pass (D-077) | 8.15 |
| 15 | `_save_mission()` atomic | 8.1 |
| 16 | `ComponentHealth` + `CapabilityStatus` tri-state tanımlı | 8.2, 8.3 |
| 17 | `services.json` heartbeat freshness çalışıyor | 8.13 |
| 18 | Tüm endpoint'ler wrapper response döner (`*Response`) | 8.8–8.11 |
| 19 | D-078 waiver kaydı DECISIONS.md'de | doc |

---

## Yeni Dosyalar

```
agent/
├── api/
│   ├── __init__.py
│   ├── server.py           ← 8.7
│   ├── schemas.py          ← 8.2 (FROZEN)
│   ├── normalizer.py       ← 8.6
│   ├── cache.py            ← 8.4
│   ├── capabilities.py     ← 8.3
│   ├── circuit_breaker.py  ← 8.5
│   ├── mission_api.py      ← 8.8
│   ├── approval_api.py     ← 8.9
│   ├── telemetry_api.py    ← 8.10
│   └── health_api.py       ← 8.11
├── utils/
│   └── atomic_write.py     ← 8.1
tests/
├── test_cache.py           ← 8.15
├── test_circuit_breaker.py ← 8.15
├── test_normalizer.py      ← 8.15
└── test_api.py             ← 8.15
```

---

*Sprint 8 Task Breakdown — OpenClaw Phase 5A-1*
*Date: 2026-03-25*
*Operator: AKCA | Architect: Claude Opus 4.6*
