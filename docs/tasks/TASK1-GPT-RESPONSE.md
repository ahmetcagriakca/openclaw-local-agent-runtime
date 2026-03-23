# Görev 1: Worker Fail Recovery — Claude Implementation Report

Bu doküman GPT'nin Görev 1 spesifikasyonundaki her acceptance criteria'yı nasıl karşıladığımı, exact dosya değişikliklerini ve smoke test komutlarını içerir.

---

## 1. Root cause ve recovery modeli

**Sorunlar:**
- Worker `finally` bloğunda lease'i koşulsuz siliyordu → fail'de ticket kayboluyordu
- Runner crash'te (`pwsh` bulunamaz, syntax error vs.) task `running`'de kalıyordu
- Runner exit 0 dönüp task'ı `succeeded`'a çekmeyi başaramadığında (snapshot yazma hatası) task `running`'de kalıyordu
- Orphan lease'ler (terminal task'a ait) birikiyordu
- `cancel_requested` durumundaki task'lar repair'de handle edilmiyordu

**Recovery modeli:**
1. **Worker post-run validation:** Runner çıkışından sonra, exit code'dan bağımsız olarak, task.json okunur. Non-terminal ise:
   - exit 0 → `succeeded` + event `task_succeeded_recovered`
   - exit != 0 → `failed` + event `task_failed_recovered`
2. **Dead-letter queue:** Fail eden ticket silinmez, `queue\dead-letter\`'e taşınır
3. **Repair script:** Offline bakım — stuck task'ları force-terminal, orphan lease'leri temizle, dead-letter raporla

---

## 2. Dosya değişiklikleri

| Dosya | Değişiklik |
|-------|-----------|
| `oc-task-worker.ps1` | Post-run validation: exit 0 + non-terminal ve exit != 0 + non-terminal handling. Dead-letter queue. pwsh tam yol fallback |
| `oc-task-common.ps1` | `QueueDeadLetterPath` config'e eklendi. `Initialize-OcRuntimeLayout`'a dead-letter dizini eklendi |
| `oc-task-health.ps1` | `deadLetterTickets` ve `stuckNonTerminal` sayaçları eklendi |
| `oc-task-repair.ps1` | Yeni. Phase 1: stuck task repair (running/queued/cancel_requested). Phase 2: orphan lease cleanup. DryRun desteği. İdempotent |
| Bootstrap | `queue\dead-letter\` dizin oluşturma. v3.2 versiyon |

---

## 3. Acceptance criteria karşılama

### A. Runner exits 0 but task remains running
**Karşılandı.** Worker post-run validation task.json'ı okur. Status non-terminal ise `succeeded`'a zorlar.
- Event: `task_succeeded_recovered`
- Log: `Task recovered to succeeded: <taskId> (was running)`

### B. Runner exits non-zero and task remains running
**Karşılandı.** Worker post-run validation task'ı `failed`'a zorlar.
- Event: `task_failed_recovered`
- Log: `Task force-failed by worker: <taskId> (was running, exit N)`

### C. Stale running task
**Karşılandı.** `oc-task-repair.ps1` süre bazlı scan yapar:
- `running` → `failed` + event `task_failed_recovered`
- `queued` → `failed` + event `task_failed_recovered`
- `cancel_requested` → `cancelled` + event `task_cancelled_recovered`

### D. Stale lease on terminal task
**Karşılandı.** `oc-task-repair.ps1` Phase 2:
- Lease'in referans ettiği task'ı okur
- Task terminal ise lease'i siler + event `stale_lease_removed`
- Task yoksa lease'i dead-letter'a taşır

### E. Idempotency
**Karşılandı.** Repair sadece non-terminal task'lara dokunur. Terminal olanları atlar. İkinci çalıştırma `Repaired: 0` döner.

### F. Visibility
**Karşılandı.** Healthcheck'te:
- `deadLetterTickets` — fail sonrası dead-letter'a düşen ticket sayısı
- `stuckNonTerminal` — şu an non-terminal durumda olan task sayısı
- `leaseTickets` — aktif lease sayısı

---

## 4. Event isimlendirme

| Event | Ne zaman |
|-------|----------|
| `task_failed_recovered` | Worker: runner fail + task non-terminal. Repair: stuck running/queued |
| `task_succeeded_recovered` | Worker: runner exit 0 + task non-terminal |
| `task_cancelled_recovered` | Repair: stuck cancel_requested |
| `stale_lease_removed` | Repair: terminal task'a ait lease temizlendi |

---

## 5. Smoke test komutları

### Test 1: Normal task (regression)
```powershell
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"recovery-ok.txt","content":"normal flow works"}'))
$raw = powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 $b64
$tid = ($raw | ConvertFrom-Json).taskId
Start-Sleep -Seconds 8
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-get.ps1 -TaskId $tid | ConvertFrom-Json | Select-Object taskId, status, lastError
Test-Path $env:USERPROFILE\oc\results\recovery-ok.txt
```
Beklenen: `succeeded`, `True`

### Test 2: Runner crash (exit non-zero, Kriter B)
```powershell
$rf = "$env:USERPROFILE\oc\bin\oc-task-runner.ps1"
$backup = Get-Content -Raw $rf
"throw 'SIMULATED CRASH'" | Set-Content -Encoding UTF8 $rf

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"no-file.txt","content":"nope"}'))
$raw = powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 $b64
$failTid = ($raw | ConvertFrom-Json).taskId
Start-Sleep -Seconds 8

powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-get.ps1 -TaskId $failTid | ConvertFrom-Json | Select-Object taskId, status, lastError
Get-ChildItem $env:USERPROFILE\oc\queue\dead-letter\*.json -ErrorAction SilentlyContinue | Select-Object Name
Get-Content $env:USERPROFILE\oc\logs\worker.log | Select-Object -Last 5
Test-Path $env:USERPROFILE\oc\results\no-file.txt

$backup | Set-Content -Encoding UTF8 $rf
```
Beklenen: `failed`, `Worker-level failure`, dead-letter'da ticket, dosya `False`

### Test 3: Runner exit 0 ama task non-terminal simülasyonu (Kriter A)
```powershell
$rf = "$env:USERPROFILE\oc\bin\oc-task-runner.ps1"
$backup = Get-Content -Raw $rf
"exit 0" | Set-Content -Encoding UTF8 $rf

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"exit0-test.txt","content":"exit0"}'))
$raw = powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 $b64
$zeroTid = ($raw | ConvertFrom-Json).taskId
Start-Sleep -Seconds 8

powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-get.ps1 -TaskId $zeroTid | ConvertFrom-Json | Select-Object taskId, status, lastError
Get-Content $env:USERPROFILE\oc\logs\worker.log | Select-Object -Last 3

$backup | Set-Content -Encoding UTF8 $rf
```
Beklenen: `succeeded` (recovered), worker log `Task recovered to succeeded`

### Test 4: Stale lease on terminal task (Kriter D)
```powershell
# Yapay orphan lease oluştur
$fakeTicket = '{"taskId":"task-20260322-030920061-7549","taskName":"create_note","priority":5}'
$fakeTicket | Set-Content -Encoding UTF8 "$env:USERPROFILE\oc\queue\leases\p05-fake-orphan.json"

# Repair — orphan lease'i temizlemeli
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-repair.ps1 -StuckMinutes 0

# Lease silinmiş mi?
Test-Path "$env:USERPROFILE\oc\queue\leases\p05-fake-orphan.json"
```
Beklenen: `Leases repaired: 1`, lease `False` (silindi)

### Test 5: Repair idempotency (Kriter E)
```powershell
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-repair.ps1 -StuckMinutes 0
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-repair.ps1 -StuckMinutes 0
```
Beklenen: İlk çalıştırma ne bulursa düzeltir. İkinci çalıştırma `Tasks repaired: 0, Leases repaired: 0`

### Test 6: Healthcheck visibility (Kriter F)
```powershell
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-health.ps1
```
Beklenen: `deadLetterTickets`, `stuckNonTerminal`, `leaseTickets` alanları görünür

---

## 6. Kalan sınırlamalar

| Sınırlama | Açıklama |
|-----------|----------|
| Process liveness check yok | Repair süre bazlı çalışır, aktif runner process'i kontrol etmez. Bir task gerçekten çalışıyor olsa bile `StuckMinutes` aşıldıysa force-fail olur. Varsayılan 60 dakika yeterince güvenli |
| Dead-letter cleanup yok | Dead-letter birikir. Manuel temizleme veya TTL bazlı purge henüz yok |
| Retry henüz yok | ~~Görev 2'nin konusu~~ → **Tamamlandı (v3.3).** Bkz. `RETRY-TASK-CANONICAL.md` |

---

## 7. Versiyon

v3.2 — Worker fail recovery tam kapsam.
