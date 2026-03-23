# Task F1.4 — Stuck Task Policy Freeze + Safe Recovery Integration: Report

## Tasarim Ozeti

ARCHITECTURE.md'de tanimlanan uc durumlu stuck-task policy'si (Case A/B/C) watchdog, preflight ve health'e entegre edildi.

| Case | Kosul | Aksiyon | Uygulayan |
|------|-------|---------|-----------|
| A — Safe stuck | Non-terminal, age > 60dk, worker YOK, lease YOK | Auto-fail (veya auto-cancel), event yaz, log yaz | Watchdog |
| B — Ambiguous | Non-terminal, age > 60dk, worker AKTIF veya lease VAR | Sadece raporla, degraded, mutasyon yok | Watchdog, Preflight, Health |
| C — Terminal stale | Task terminal ama lease hala mevcut | Lease sil, event yaz | Watchdog |

**Temel tasarim kararlari:**
- Watchdog Case A'da otomatik fail yapar — conservative ve guvenli (worker yok, lease yok, terk edilmis)
- Watchdog Case B'de hicbir sey degistirmez — sadece raporlar, manual repair gerektirir
- Watchdog Case C'de stale lease'i siler — terminal task'in lease'i olmamali
- Preflight stuck task'lari siniflandirir ama MUTASYON YAPMAZ (boot aninda guvenli)
- Health artik stuckCaseA ve stuckCaseB sayilarini raporlar
- Hicbir yerde auto-retry yok

---

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `bin/oc-runtime-watchdog.ps1` | Phase 6: Case C (terminal stale lease cleanup) eklendi. Phase 7: stuck task detection → A/B/C classification + Case A auto-fail. Summary'ye `stuckSafeRecovered`, `stuckAmbiguous`, `staleLeaseCleaned` alanlari eklendi. |
| `bin/oc-runtime-startup-preflight.ps1` | Phase 7: stuck task detection → A/B classification (observe-only). Summary'ye `stuckCaseA`, `stuckCaseB` alanlari eklendi. |
| `bin/oc-task-health.ps1` | Stuck task scan → A/B classification. `stuckCaseA`, `stuckCaseB` alanlari ciktiya eklendi. |
| `docs/ARCHITECTURE.md` | Section 8.1: FROZEN (F1.4) etiketi, her case'e uygulayan/event/log detaylari, preflight davranisi, health visibility notu eklendi. |

---

## Tam Patch

### Watchdog: Phase 6 — Case C (Terminal stale lease cleanup)

Stale lease recovery'den (phase 5) sonra, mevcut lease'lerin terminal task'lara ait olup olmadigini kontrol eder. Terminal ise lease'i siler ve event yazar.

```powershell
# -- 6. Terminal task stale lease/ticket cleanup (Case C) -----------------------
$staleLeaseCleaned = 0
$currentLeaseFiles = @()
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    $currentLeaseFiles = @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File)
}
foreach ($lf in $currentLeaseFiles) {
    try {
        $ticket = Get-Content -Raw -LiteralPath $lf.FullName | ConvertFrom-Json
        $leaseTaskId = [string](Get-OcPropertyValue -Object $ticket -Name 'taskId')
        if ([string]::IsNullOrWhiteSpace($leaseTaskId)) { continue }
        $tp = Get-OcTaskPaths -TaskId $leaseTaskId -RuntimeConfig $config
        if (-not (Test-Path -LiteralPath $tp.TaskJsonPath)) { continue }
        $leaseTask = Get-Content -Raw -LiteralPath $tp.TaskJsonPath | ConvertFrom-Json
        $leaseStatus = [string](Get-OcPropertyValue -Object $leaseTask -Name 'status')
        if ($leaseStatus -eq 'failed' -or $leaseStatus -eq 'succeeded' -or $leaseStatus -eq 'cancelled') {
            Remove-Item -LiteralPath $lf.FullName -Force
            # ... append stale_lease_removed event with recoveredBy=watchdog ...
            $staleLeaseCleaned++
        }
    }
    catch { }
}
```

### Watchdog: Phase 7 — Stuck task policy (Case A / Case B)

Worker mutex ve lease index kullanarak siniflandirma yapar.

```powershell
# -- 7. Stuck task policy (Case A / Case B) ------------------------------------
$workerActive = Test-OcWorkerActive -MutexName $config.WorkerMutexName

# Build lease index: taskId -> lease file name
$leaseIndex = @{}
# ... populate from queue/leases/ ...

foreach ($td in $taskDirs) {
    # ... age check ...
    $hasLease = $leaseIndex.ContainsKey($taskId)

    # Case B — Ambiguous: worker active or lease still held
    if ($workerActive -or $hasLease) {
        $ambiguousCount++
        # ... log only, no mutation ...
        continue
    }

    # Case A — Safe stuck: no worker, no lease, abandoned
    $targetStatus = 'failed'  # or 'cancelled' if cancel_requested
    $tj.status = $targetStatus
    $tj.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $tj.lastError = 'Stuck task auto-failed by watchdog (Case A). ...'
    Save-OcJson -Path $tjp -Object $tj
    # ... append stuck_task_auto_failed event with policy='Case A' ...
}
```

### Preflight: Phase 7 — Classification only (no mutations)

```diff
-# -- 7. Stuck task detection (count only)
+# -- 7. Stuck task classification (observe-only, no mutations at boot)
+$workerActiveForStuck = Test-OcWorkerActive -MutexName $config.WorkerMutexName
+# Build lease index, classify into caseA/caseB
+# Log each stuck task with its classification
+# Report stuckCaseA and stuckCaseB in summary
```

### Health: Stuck classification

```diff
+$stuckCaseA = 0
+$stuckCaseB = 0
+# ... classify using workerActive and leaseIndex ...
+    stuckCaseA = $stuckCaseA
+    stuckCaseB = $stuckCaseB
```

### ARCHITECTURE.md Section 8.1

FROZEN (F1.4) etiketi eklendi. Her case icin uygulayan script, event adi, log formati detaylari eklendi.

---

## Smoke Test Komutlari

```powershell
# Test 1: Watchdog — Case A auto-recovery
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-watchdog.ps1

# Test 2: Verify auto-failed task
$tj = Get-Content -Raw "$env:USERPROFILE\oc\tasks\task-20260322-082753368-4778\task.json" | ConvertFrom-Json
$tj.status        # -> failed
$tj.lastError     # -> "Stuck task auto-failed by watchdog (Case A)..."
Get-Content "$env:USERPROFILE\oc\tasks\task-20260322-082753368-4778\events.jsonl" -Tail 1
# -> stuck_task_auto_failed event

# Test 3: Preflight — classification without mutation
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-startup-preflight.ps1

# Test 4: Health — stuck categories
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-task-health.ps1

# Test 5: Watchdog log entries
Get-Content "$env:USERPROFILE\oc\logs\control-plane.log" -Tail 10 | Where-Object { $_ -match "Case [ABC]" }

# Test 6: Second watchdog run — idempotent (no more stuck tasks)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-watchdog.ps1
```

---

## Observed Output

### Test 1: Watchdog — Case A auto-recovery

```json
{
    "phase": "watchdog",
    "status": "degraded",
    "checks": [
        "layout: all directories present",
        "scripts: all present",
        "manifest: present and parseable",
        "worker scheduled task: OpenClawTaskWorker (Ready)",
        "watchdog scheduled task: OpenClawRuntimeWatchdog (Ready)",
        "preflight scheduled task: OpenClawStartupPreflight (Ready)",
        "leases: no stale leases",
        "stuck tasks: 1 (Case A auto-resolved: 1)",
        "worker: not active (no pending tickets)"
    ],
    "repairs": [
        "Case A: task-20260322-082753368-4778 running -> failed"
    ],
    "stuckTasks": 1,
    "stuckSafeRecovered": 1,
    "stuckAmbiguous": 0,
    "staleLeaseCleaned": 0
}
```

### Test 2: Verify auto-failed task

```
status: failed
lastError: Stuck task auto-failed by watchdog (Case A). Status was running, age 325 min. No active worker, no lease.
finishedUtc: 2026-03-22T16:53:28.6154034Z

Event: stuck_task_auto_failed
  previousStatus: running
  stuckMinutes: 325
  recoveredBy: watchdog
  policy: Case A — safe stuck
```

### Test 3: Preflight — after recovery, no stuck tasks

```json
{
    "phase": "startup-preflight",
    "status": "ok",
    "stuckTasks": 0,
    "stuckCaseA": 0,
    "stuckCaseB": 0
}
```

### Test 4: Health — after recovery, clean

```json
{
    "status": "ok",
    "stuckTasks": 0,
    "stuckCaseA": 0,
    "stuckCaseB": 0
}
```

### Test 5: Watchdog log entries

```json
{"level":"warn","message":"[watchdog] Case A (safe stuck): task-20260322-082753368-4778 running -> failed (age=325min)"}
{"level":"warn","message":"[watchdog] Stuck tasks: total=1 safeRecovered=1 ambiguous=0"}
```

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | **Case B resolution manual** | Ambiguous stuck task'lar watchdog tarafindan cozulmuyor. `oc-task-repair.ps1 -StuckMinutes 60` ile manual cozum gerekiyor. Bu tasarim geregi — belirsiz durumda otomatik mutasyon tehlikeli. |
| 2 | **Auto-retry yok** | Case A auto-fail sonrasinda auto-retry yapilmiyor. Tasarim geregi — retry ayri bir karar. |
| 3 | **Case C sadece lease temizler** | Terminal task'in pending ticket'i varsa temizlenmiyor (sadece lease). Pending ticket terminal task icin nadir bir durum. |
| 4 | **Stuck threshold sabit 60 dk** | Watchdog ve preflight'ta threshold 60 dk, health'te 30 dk. Health daha erken uyari veriyor. Konfigurasyon dosyasindan okunmuyor. |
| 5 | **Event'teki em-dash encoding** | `policy` alanindaki "Case A — safe stuck" em-dash karakteri bazi terminallerde bozuk gorunebilir. Fonksiyonel etki yok. |
| 6 | **Bootstrap heredoc guncel degil** | Bootstrap'taki watchdog/health heredoc'lari F1.4 degisikliklerini icermiyor. |
