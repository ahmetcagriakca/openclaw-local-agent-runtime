# Task F1.4-cleanup — Stuck Task Policy Deployment + Threshold Drift: Report

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `bin/oc-task-common.ps1` | Config'e `StuckWarningMinutes` (30), `StuckRecoveryMinutes` (60), `StaleLeaseMinutes` (30) eklendi |
| `bin/oc-runtime-watchdog.ps1` | Hardcoded `60` → `$config.StuckRecoveryMinutes`, hardcoded `30` → `$config.StaleLeaseMinutes` |
| `bin/oc-runtime-startup-preflight.ps1` | Hardcoded `60` → `$config.StuckRecoveryMinutes`, hardcoded `30` → `$config.StaleLeaseMinutes` |
| `bin/oc-task-health.ps1` | Hardcoded `30` → `$config.StuckWarningMinutes` |
| `oc-task-runtime-bootstrap-v3.4.ps1` | Config heredoc'a 3 threshold key eklendi. Health heredoc: centralized threshold + Case A/B classification + `stuckCaseA`/`stuckCaseB` alanlari |
| `docs/ARCHITECTURE.md` | Section 8.1: threshold model tablosu eklendi, warning vs recovery ayrimi aciklandi |

---

## Tam Patch

### Config (oc-task-common.ps1)

```diff
         WorkerMutexName = 'Global\OpenClawTaskWorker'
+        StuckWarningMinutes = 30
+        StuckRecoveryMinutes = 60
+        StaleLeaseMinutes = 30
     }
```

### Watchdog

```diff
-    if ($leaseAge -ge 30) {
+    if ($leaseAge -ge $config.StaleLeaseMinutes) {

-$stuckThreshold = 60
+$stuckThreshold = $config.StuckRecoveryMinutes
```

### Preflight

```diff
-    if ($leaseAge -ge 30) {
+    if ($leaseAge -ge $config.StaleLeaseMinutes) {

-$stuckThreshold = 60
+$stuckThreshold = $config.StuckRecoveryMinutes
```

### Health

```diff
-$stuckThresholdMinutes = 30
+$stuckThresholdMinutes = $config.StuckWarningMinutes
```

### Bootstrap — config heredoc

```diff
         WorkerMutexName = 'Global\OpenClawTaskWorker'
+        StuckWarningMinutes = 30
+        StuckRecoveryMinutes = 60
+        StaleLeaseMinutes = 30
```

### Bootstrap — health heredoc

Tamamen guncellendi: centralized threshold, lease index, Case A/B classification, stuckCaseA/stuckCaseB alanlari.

### ARCHITECTURE.md — threshold model tablosu

```
| Config key           | Default | Purpose                    | Used by            |
|----------------------|---------|----------------------------|--------------------|
| StuckWarningMinutes  | 30      | Early warning visibility   | health             |
| StuckRecoveryMinutes | 60      | Recovery decision boundary | watchdog, preflight|
| StaleLeaseMinutes    | 30      | Lease age before recovery  | watchdog, preflight|
```

Health surfaces stuck tasks earlier (30 min) for visibility.
Watchdog/preflight only act or classify at recovery threshold (60 min).
This is intentional — warning before action.

---

## Smoke Test Komutlari

```powershell
# Test 1: Watchdog — centralized thresholds
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-watchdog.ps1

# Test 2: Preflight — centralized thresholds
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-startup-preflight.ps1

# Test 3: Health — centralized thresholds
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-task-health.ps1

# Test 4: No hardcoded thresholds remain
grep -n "= 30\|= 60" bin/oc-runtime-watchdog.ps1 bin/oc-runtime-startup-preflight.ps1 bin/oc-task-health.ps1
# Expected: no output
```

---

## Observed Output

### Test 1: Watchdog — ok

```json
{
    "phase": "watchdog",
    "status": "ok",
    "stuckTasks": 0,
    "stuckSafeRecovered": 0,
    "stuckAmbiguous": 0,
    "staleLeaseCleaned": 0,
    "recoveredLeases": 0
}
```

### Test 2: Preflight — ok

```json
{
    "phase": "startup-preflight",
    "status": "ok",
    "stuckTasks": 0,
    "stuckCaseA": 0,
    "stuckCaseB": 0,
    "recoveredLeases": 0
}
```

### Test 3: Health — ok

```json
{
    "status": "ok",
    "stuckTasks": 0,
    "stuckCaseA": 0,
    "stuckCaseB": 0
}
```

### Test 4: No hardcoded thresholds

```
(no output — clean)
```

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | **oc-task-repair.ps1 hala parametre kullanir** | Repair script `[int]$StuckMinutes = 60` parametresi ile calisir, config'den okumuyor. Bu tasarim geregi — repair manual bir arac ve kullanici threshold'u override edebilmeli. |
| 2 | **Bootstrap diger heredoc'lar** | Bootstrap'taki enqueue, retry, cancel heredoc'lari F1.3 rejection envelope degisikliklerini icermiyor. Ayri bir bootstrap-sync task'i gerekli. |
| 3 | **Threshold degisikligi restart gerektirir** | Config degerleri script yuklenmesinde okunur. Calistirma sirasinda degisiklik icin script'in yeniden calistirilmasi gerekir. |
