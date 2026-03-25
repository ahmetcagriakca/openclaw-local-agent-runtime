# Sprint 7-8 Cross-Review Fix Record

**Date:** 2026-03-25
**Source:** GPT Sprint 7-8 Toplu Review (7 blocking + 3 non-blocking)
**Reviewer verdict:** `partial`
**Our assessment:** 3 hemen düzeltilmeli, 2 zaten çözülmüş, 2 implementasyonda çözülecek

---

## Bulgu Analizi

| # | GPT Bulgu | Geçerli? | Aksiyon |
|---|-----------|----------|---------|
| 1 | Sprint 7 closure overstated | Çözülmüş — D-078 waiver frozen | Yok |
| 2 | Stale threshold drift | Terminoloji tutarlı (task breakdown "response type" diyor) — GPT muhtemelen olmayan result raporu referans ediyor | Guard note |
| 3 | D-068 semantics dirty | **Geçerli** — D-068 "5 state" frozen, Sprint 8 "6 state" kullanıyor | D-079 amendment |
| 4 | Response contract çelişkili | Wrapper'lar eklendi (önceki fix) ama D-068 cross-ref temizlenmedi | Doc fix |
| 5 | Health migration evidence weak | Sprint 8 henüz implement edilmedi — implementasyonda çözülecek | Sprint 8 scope |
| 6 | services.json liveness weak | Heartbeat model eklendi (önceki fix) ama DECISIONS.md'de karar kaydı yok | D-080 |
| 7 | D-077 evidence eksik | Sprint 8 henüz implement edilmedi — implementasyonda çözülecek | Sprint 8 scope |

### Kritik Ayrım: Sprint 8 Plan vs Implement

GPT review "Sprint 8 result" diyor ama ortada Sprint 8 result raporu yok.
Sprint 8 henüz **plan aşamasında** — task breakdown, schema tanımları, freeze addendum
mevcut ama kod yazılmadı. Bu yüzden:

- "Evidence yok" bulguları (5, 7) → implementasyonda üretilecek, şu an beklenen.
- "Doküman çelişkisi" bulguları (2, 3, 4, 6) → hemen düzeltilmeli.
- "Zaten çözülmüş" bulgular (1) → aksiyon yok.

---

## D-079: DataQuality Enum Amendment

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

**Context:** D-068 "5 data states: known_zero, unknown, not_reached, stale, degraded"
olarak donduruldu. Sprint 8 schema tasarımında (GPT review sonrası) iki sorun çıktı:

1. `known_zero` semantik olarak yanlış kullanılıyordu — "tüm veriler fresh" anlamında.
   `known_zero` yalnızca "veri gerçekten sıfır ve bu biliniyor" durumunda anlamlı.
   Bu bir veri kalitesi state'i değil, value state'i.

2. `partial` (bazı kaynaklar mevcut, bazıları eksik) durumu için state yoktu.
   Pratikte normalizer bu durumla karşılaşır ve `sourcesMissing` doldurur.
   Ama response-level dataQuality bunu yansıtmıyordu.

**Decision:** D-068 ilkesi korunur (unknown ≠ zero, UI tüm durumları ayırt eder).
State listesi güncellenir:

| Eski (D-068) | Yeni (D-079) | Değişiklik |
|-------------|-------------|-----------|
| `known_zero` | ~~kaldırıldı~~ | Value state, kalite state'i değil |
| — | `fresh` | Tüm kaynaklar mevcut + threshold altı |
| — | `partial` | ≥1 kaynak mevcut, ≥1 eksik |
| `unknown` | `unknown` | Değişmedi |
| `not_reached` | `not_reached` | Değişmedi |
| `stale` | `stale` | Değişmedi |
| `degraded` | `degraded` | Değişmedi |

**Yeni enum (6 state):**

```python
class DataQuality(str, Enum):
    FRESH = "fresh"
    PARTIAL = "partial"
    STALE = "stale"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    NOT_REACHED = "not_reached"
```

**Öncelik kuralı (birden fazla durum):** `degraded > stale > partial > fresh`

**D-068 ilkesi değişmez:**
- Unknown veriyi sıfır, boş, pass veya yeşil göstermek YASAK.
- UI 6 state'in tamamını ayırt etmeli.
- `fresh` + alan değeri 0 = bilinen sıfır (kalite katmanında değil, veri katmanında).

**Trade-off:** D-068'in state sayısı 5→6 değişti. Bu frozen decision amendment'ı.
İlke ve güvenlik garantisi aynı, temsil kapasitesi arttı.

**Rollback:** `partial` ve `fresh` kaldırılıp `known_zero` geri getirilebilir.
Ama `known_zero`'nun semantik sorunu geri döner.

---

## D-080: Service Registry Freshness Rule

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

**Context:** `services.json` startup/shutdown model'i crash durumunda stale "running"
bırakır. Bu fake live üretir ve D-068 ilkesini ("unknown ≠ zero, missing ≠ healthy")
ihlal eder.

**Decision:** Service registration heartbeat-based freshness ile korunur.

**Kurallar:**
1. Her service `lastHeartbeatAt` + `heartbeatIntervalS` yazar
2. Canlılık: `lastHeartbeatAt + (heartbeatIntervalS × 2) > now` → alive
3. Threshold aşımı → stale registration → health endpoint `degraded` gösterir
4. Clean shutdown → `status: "stopped"` (bonus, canlılık heartbeat'e bağlı)
5. Crash → heartbeat durur → otomatik stale tespiti

**İmpacted:** `agent/api/server.py` (heartbeat task), `agent/api/health_api.py` (freshness check)

---

## Cross-Document Consistency Fixes

### Fix 1: D-068 DECISIONS.md Amendment

D-068 tanımını D-079 referansıyla güncelle. Eski "5 states" ifadesi
"6 states (D-079 amendment)" olarak düzeltilecek.

### Fix 2: Stale Threshold Terminoloji Guard

Tüm dokümanlarda threshold terminolojisi: **"response-type threshold"**.
"per-source threshold" ifadesi YASAK — bu farklı bir konsept.

| Doğru | Yanlış |
|-------|--------|
| response-type threshold | per-source threshold |
| "Mission detail response → 10s stale threshold" | "state.json source → 10s threshold" |

Source'lar için ageMs hesaplanır (her source'un yaşı). Ama stale kararı
**response type'a** göre verilir — aynı source farklı response type'larda
farklı threshold'a tabi olabilir.

### Fix 3: Sprint 8 Durum Netleştirmesi

Sprint 8 şu an **plan aşamasında**. Implementasyon başlamadı.
Mevcut dokümanlar:
- `SPRINT-8-TASK-BREAKDOWN.md` → implementasyon planı ✅
- `SPRINT-8-GPT-REVIEW-FIX.md` → plan düzeltmeleri ✅
- `PHASE-5-FREEZE-ADDENDUM.md` → design freeze ✅

Sprint 8 **implementasyon başladığında** üretilecek:
- `PHASE-5A-1-SPRINT-8-REPORT.md` → result raporu
- Test evidence (pytest output)
- Doc validator evidence (`validate_sprint_docs.py`)
- E2E evidence
- curl evidence

Bu dokümanlar olmadan Sprint 8 "done" etiketlenemez.

---

## Doğrulama

```bash
# D-079 amendment
grep "D-079" docs/ai/DECISIONS.md
grep "6 state\|FRESH\|PARTIAL" docs/ai/DECISIONS.md

# D-080 heartbeat
grep "D-080" docs/ai/DECISIONS.md
grep "lastHeartbeatAt\|heartbeat" docs/ai/DECISIONS.md

# Threshold terminoloji — "per-source threshold" olmamalı
grep -ri "per.source threshold" docs/ SPRINT-8-TASK-BREAKDOWN.md
# Beklenen: 0 match

# DataQuality tutarlılık — known_zero ve live olmamalı
grep -ri "known_zero\|KNOWN_ZERO\|\"live\"" SPRINT-8-TASK-BREAKDOWN.md docs/ai/
# Beklenen: 0 match (sadece D-068 eski referansı hariç)
```

---

*Sprint 7-8 Cross-Review Fix Record — OpenClaw Local Agent Runtime*
*Date: 2026-03-25*
*GPT review: 7 findings, 3 actioned now, 2 already resolved, 2 deferred to implementation*
