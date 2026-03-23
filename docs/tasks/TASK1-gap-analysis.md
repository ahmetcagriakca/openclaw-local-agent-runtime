# Görev 1: Worker Fail Recovery — GPT Spec vs Claude Implementasyon Karşılaştırması

## Durum özeti

v3.1 bootstrap'ta Görev 1'in çekirdek parçaları implement edildi ve canlıda doğrulandı. Ancak GPT'nin detaylı spesifikasyonundaki bazı edge case'ler henüz kapsanmamış. Aşağıda tam karşılaştırma ve aksiyon planı var.

---

## 1. Runner postcondition hardening

| Gereksinim | Durum | Detay |
|-----------|-------|-------|
| Runner non-zero → worker task'ı force-fail eder | ✅ Kapsandı | Worker `$runnerExitCode != 0` durumunda task'ı `failed`'a zorluyor |
| **Runner exits 0 ama task hâlâ non-terminal** | ❌ Eksik | Worker sadece `!$runnerSuccess` kontrol ediyor. Runner 0 dönerse `$runnerSuccess = $true` oluyor ve post-check yapılmıyor. Eğer runner 0 dönüp task'ı `succeeded`'a çekmeyi unutursa (veya snapshot yazma sırasında crash olursa), task `running`'de kalır |
| task.json + events.jsonl + worker.log güncelleniyor | ✅ Kapsandı | `task_failed_by_worker` event, `worker.log`'a reason |

**Gerekli düzeltme:** Worker'da runner exit'ten sonra **hem success hem fail durumunda** task snapshot kontrolü yapılmalı. Exit 0 ama status hâlâ non-terminal → force `succeeded` veya `failed` (duruma göre).

---

## 2. Stale/inconsistent recovery

| Senaryo | Durum | Detay |
|---------|-------|-------|
| a) task=running, no lease, no runner | ✅ Kısmen | Repair scripti stuck `running` task'ları buluyor ama process liveness kontrolü yapmıyor — sadece süre bazlı |
| **b) task=cancel_requested, no lease, no runner** | ❌ Eksik | Repair scripti `cancel_requested` durumunu tanımıyor |
| **c) Lease exists ama task zaten terminal** | ❌ Eksik | Ne worker ne repair orphan lease temizliği yapıyor |
| **d) Ticket yok ama task non-terminal** | ❌ Eksik | Orphan task detection yok |

**Gerekli düzeltmeler:**
- Repair: `cancel_requested` → `cancelled`'a çevirmeli
- Repair: terminal task'lara ait orphan lease'leri temizlemeli
- Repair: ticket+lease'i olmayan non-terminal task'ları raporlamalı

---

## 3. Repair script

| Gereksinim | Durum | Detay |
|-----------|-------|-------|
| Inconsistent task scan | ✅ Kapsandı | Stuck running/queued task'ları buluyor |
| Deterministic repair | ✅ Kapsandı | Açık durum değişikliği |
| Safe to run multiple times | ✅ Kapsandı | Sadece non-terminal task'lara dokunuyor |
| Terminal task'ları bozmuyor | ✅ Kapsandı | Status kontrolü var |
| Log kaydı | ✅ Kapsandı | stdout + control-plane.log |
| **Orphan lease temizliği** | ❌ Eksik | |
| **cancel_requested handling** | ❌ Eksik | |
| **Dead-letter raporu** | ✅ Kapsandı | Sayı raporlanıyor |

---

## 4. Logging ve observability

| Gereksinim | Durum | Detay |
|-----------|-------|-------|
| task.json güncellenir | ✅ | |
| events.jsonl event düşer | ✅ | |
| worker.log sebep yazar | ✅ | |
| **Event name: `task_failed_recovered`** | ❌ | Mevcut: `task_failed_by_worker` — semantik olarak aynı ama isimlendirme farklı |
| **Event name: `task_cancelled_recovered`** | ❌ | cancel_requested recovery yok |
| **Event name: `stale_lease_removed`** | ❌ | orphan lease temizliği yok |
| **Event name: `inconsistent_state_detected`** | ❌ | genel inconsistency event yok |

---

## 5. Acceptance criteria

| Kriter | Durum |
|--------|-------|
| A. Runner exits 0 ama task running → detect + force terminal | ❌ Eksik |
| B. Runner exits non-zero ama task running → force failed | ✅ Geçti |
| C. Stale running task → repair detects + fixes | ✅ Kısmen (süre bazlı, process check yok) |
| D. Stale lease on terminal task → remove | ❌ Eksik |
| E. Idempotency — repair 2x safe | ✅ Geçti |
| F. Visibility — stuck/inconsistent görünür | ✅ Kısmen (deadLetterTickets var, stuck count yok) |

---

## 6. Smoke tests

| Test | Durum |
|------|-------|
| 1. Simulated runner crash | ✅ Çalıştırıldı ve geçti |
| 2. Runner exit 0 ama task non-terminal | ❌ Test yok, implementasyon yok |
| 3. Stale running task | ✅ Repair DryRun ile test edildi |
| 4. Stale lease on terminal task | ❌ Test yok, implementasyon yok |
| 5. Repair 2x idempotent | ✅ Kısmen (explicit olarak gösterilmedi) |

---

## 7. Aksiyon planı — eksikleri kapatmak için

### Patch 1: Worker post-run validation (Kriter A)
Worker'da runner exit sonrası task status kontrolü — exit code'dan bağımsız:
```
runner çıktı → task.json oku → status hâlâ non-terminal?
  → exit 0 ise: force 'succeeded' + event 'task_succeeded_recovered'
  → exit != 0 ise: force 'failed' + event 'task_failed_recovered' (mevcut davranış, event adı güncelle)
```

### Patch 2: Repair script genişletme (Kriter C, D)
- `cancel_requested` → `cancelled` handling
- Orphan lease temizliği (terminal task'a ait lease → sil + event `stale_lease_removed`)
- Orphan task detection (ticket+lease yok, non-terminal → raporla)
- `inconsistent_state_detected` event

### Patch 3: Healthcheck genişletme (Kriter F)
- `stuckRunningTasks` sayacı
- `orphanLeases` sayacı

### Patch 4: Event name standardizasyonu
- `task_failed_by_worker` → `task_failed_recovered`
- Yeni: `task_succeeded_recovered`, `task_cancelled_recovered`, `stale_lease_removed`, `inconsistent_state_detected`

### Patch 5: Smoke test tamamlama
- Test 2: runner exit 0 + task non-terminal simülasyonu
- Test 4: terminal task + orphan lease simülasyonu
- Test 5: repair 2x explicit idempotency doğrulama

---

## 8. Mevcut durumun özet puanlaması

| Alan | Kapsam | Not |
|------|--------|-----|
| Çekirdek fail recovery | %80 | Runner non-zero case tam, exit 0 case eksik |
| Stale recovery | %40 | Süre bazlı repair var, lease/ticket orphan yok |
| Repair script | %60 | Temel çalışıyor, edge case'ler eksik |
| Logging | %70 | Mekanizma tam, event isimlendirme farklı |
| Smoke tests | %50 | 2/5 tam geçti, 3 eksik |

**Genel hüküm:** Çekirdek mekanizma sağlam ve canlıda doğrulanmış. GPT'nin spesifikasyonundaki edge case'leri kapatmak 5 lokalize patch gerektirir — mimari değişiklik yok.
