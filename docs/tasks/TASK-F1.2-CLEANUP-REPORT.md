# Task F1.2-cleanup — Startup/Logon/Watchdog Split Cleanup: Report

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `oc-task-runtime-bootstrap-v3.4.ps1` | Config heredoc: `Supervisor*` → `Watchdog*` + `Preflight*`. Health heredoc: `supervisorTaskState` → `watchdogTaskState` + `preflightTaskState`. Supervisor script heredoc kaldirildi, yerine watchdog/preflight live-file deploy. Supervisor task registration → watchdog + preflight registration. Legacy supervisor removal kodu eklendi. Report output guncellendi. |
| `bin/oc-runtime-supervisor.ps1` | DEPRECATED header ve `Write-Warning` eklendi |
| `bin/oc-runtime-startup-preflight.ps1` | "deferred to logon/supervisor" → "deferred to logon worker and watchdog" |
| `docs/ARCHITECTURE.md` | 3 satir: "supervisor" → "watchdog, preflight" referanslari |
| `.claude/settings.local.json` | 3 izin satiri: supervisor path/task → watchdog path/task |

---

## Tam Patch

### Bootstrap (`oc-task-runtime-bootstrap-v3.4.ps1`)

**1. Path degiskenleri (satir ~141)**
```diff
-$SupervisorPath = Join-Path $BinPath 'oc-runtime-supervisor.ps1'
+$WatchdogPath = Join-Path $BinPath 'oc-runtime-watchdog.ps1'
+$PreflightPath = Join-Path $BinPath 'oc-runtime-startup-preflight.ps1'
```

**2. Embedded config heredoc (satir ~194)**
```diff
-        SupervisorScriptPath = Join-Path $script:OcBinPath 'oc-runtime-supervisor.ps1'
-        SchedulerTaskName = 'OpenClawTaskWorker'
-        SupervisorTaskName = 'OpenClawRuntimeSupervisor'
+        WatchdogScriptPath = Join-Path $script:OcBinPath 'oc-runtime-watchdog.ps1'
+        PreflightScriptPath = Join-Path $script:OcBinPath 'oc-runtime-startup-preflight.ps1'
+        SchedulerTaskName = 'OpenClawTaskWorker'
+        WatchdogTaskName = 'OpenClawRuntimeWatchdog'
+        PreflightTaskName = 'OpenClawStartupPreflight'
```

**3. Embedded health heredoc (satir ~1416)**
```diff
-$supervisorTaskState = 'not_registered'
-try {
-    $supervisorTask = Get-ScheduledTask -TaskName $config.SupervisorTaskName ...
-    ...supervisorTaskState = [string]$supervisorTask.State
-}
+$watchdogTaskState = 'not_registered'
+try {
+    $watchdogTask = Get-ScheduledTask -TaskName $config.WatchdogTaskName ...
+    ...watchdogTaskState = [string]$watchdogTask.State
+}
+
+$preflightTaskState = 'not_registered'
+try { ... }
```

```diff
-    supervisorTaskState = $supervisorTaskState
+    watchdogTaskState = $watchdogTaskState
+    preflightTaskState = $preflightTaskState
```

**4. Supervisor heredoc tamamen kaldirildi (~220 satir), yerine comment:**
```powershell
# NOTE: watchdog and preflight scripts are deployed from their live files on disk,
# not from embedded heredocs.
```

**5. Deploy satiri:**
```diff
-Deploy-OcFile -Path (Join-Path $BinPath 'oc-runtime-supervisor.ps1') -Content $supervisorScript -Label 'bin/oc-runtime-supervisor.ps1'
+$watchdogScript = [System.IO.File]::ReadAllText($WatchdogPath, ...)
+Deploy-OcFile -Path $WatchdogPath -Content $watchdogScript -Label 'bin/oc-runtime-watchdog.ps1'
+$preflightScript = [System.IO.File]::ReadAllText($PreflightPath, ...)
+Deploy-OcFile -Path $PreflightPath -Content $preflightScript -Label 'bin/oc-runtime-startup-preflight.ps1'
```

**6. Task registration (satir ~3192) — tamamen yeniden yazildi:**
- Legacy `OpenClawRuntimeSupervisor` otomatik olarak kaldirilir
- `OpenClawRuntimeWatchdog` kaydedilir (periodic-only, S4U, her 15 dk)
- `OpenClawStartupPreflight` kaydedilir (AtStartup, S4U)
- Her ikisi idempotent (mevcut ise kontrol eder, degismemisse skip)

**7. Report output:**
```diff
-Write-Output ('Supervisor task: ' + $supervisorTaskMessage)
+Write-Output ('Watchdog task  : ' + $watchdogTaskMessage)
+Write-Output ('Preflight task : ' + $preflightTaskMessage)
-Utility scripts: ... oc-runtime-supervisor.ps1
+Utility scripts: ... oc-runtime-watchdog.ps1, oc-runtime-startup-preflight.ps1
```

### Deprecated supervisor script
```diff
+# DEPRECATED — This script is superseded by oc-runtime-watchdog.ps1 (F1.2).
+# It is retained for backward compatibility only. No scheduled task references it.
+Write-Warning 'oc-runtime-supervisor.ps1 is DEPRECATED. Use oc-runtime-watchdog.ps1 instead.'
```

### Preflight log message fix
```diff
-Not kicking at startup — deferred to logon/supervisor.
+Not kicking at startup — deferred to logon worker and watchdog.
```

### ARCHITECTURE.md
```diff
-orchestration, control-plane, supervisor, health, bootstrap scripts
+orchestration, control-plane, watchdog, preflight, health, bootstrap scripts

-worker, control-plane, supervisor, and health-related logs
+worker, control-plane, watchdog, preflight, and health-related logs

-Did startup/supervisor run?
+Did startup preflight / watchdog run?
```

---

## Grep Komutlari ve Ciktilari

### Canonical script'lerde stale Supervisor referansi var mi?

```
grep -r "SupervisorScriptPath\|SupervisorTaskName\|OpenClawRuntimeSupervisor" bin/*.ps1
```

Sonuc: Sadece deprecated `bin/oc-runtime-supervisor.ps1` icinde (beklenen).

### Bootstrap'ta stale Supervisor referansi var mi?

```
grep -n "Supervisor\|supervisor" oc-task-runtime-bootstrap-v3.4.ps1
```

Sonuc: Sadece `$legacySupervisorName = 'OpenClawRuntimeSupervisor'` (eski task'i kaldirma kodu, dogru davranis).

### ARCHITECTURE.md'de stale Supervisor referansi var mi?

```
grep -n "Supervisor\|supervisor" docs/ARCHITECTURE.md
```

Sonuc: 0 match (temiz).

### Settings'de stale referans var mi?

```
grep "supervisor" .claude/settings.local.json
```

Sonuc: 0 match (temiz).

---

## Smoke Test Komutlari

```powershell
# Test 1: Watchdog
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-watchdog.ps1

# Test 2: Preflight
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-startup-preflight.ps1

# Test 3: Health
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-task-health.ps1

# Test 4: Deprecated supervisor shows warning
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-supervisor.ps1

# Test 5: Scheduled task durumu
Get-ScheduledTask -TaskName "OpenClawStartupPreflight" | Select TaskName, State
Get-ScheduledTask -TaskName "OpenClawTaskWorker" | Select TaskName, State
Get-ScheduledTask -TaskName "OpenClawRuntimeWatchdog" | Select TaskName, State

# Test 6: Legacy supervisor task yok
Get-ScheduledTask -TaskName "OpenClawRuntimeSupervisor" -ErrorAction SilentlyContinue
```

---

## Observed Output

### Test 1: Watchdog — tum 3 task Ready

```json
{
    "phase": "watchdog",
    "checks": [
        "layout: all directories present",
        "scripts: all present",
        "manifest: present and parseable",
        "worker scheduled task: OpenClawTaskWorker (Ready)",
        "watchdog scheduled task: OpenClawRuntimeWatchdog (Ready)",
        "preflight scheduled task: OpenClawStartupPreflight (Ready)",
        "leases: no stale leases",
        "stuck tasks: 1 (threshold: 60 min)",
        "worker was not active with 1 pending tickets - kicked"
    ]
}
```

### Test 2: Preflight — tum 3 task Ready

```json
{
    "phase": "startup-preflight",
    "checks": [
        "layout: all directories present",
        "scripts: all required scripts present",
        "manifest: parseable, 13 actions",
        "task definitions: 4 valid",
        "worker scheduled task: OpenClawTaskWorker (Ready)",
        "watchdog scheduled task: OpenClawRuntimeWatchdog (Ready)",
        "preflight scheduled task: OpenClawStartupPreflight (Ready)",
        "leases: no stale leases",
        "stuck tasks: 1 (threshold: 60 min)",
        "worker: active"
    ]
}
```

### Test 3: Health — watchdog + preflight alanlari mevcut

```json
{
    "scheduledTaskState": "Ready",
    "watchdogTaskState": "Ready",
    "preflightTaskState": "Ready"
}
```

### Test 4: Deprecated supervisor — WARNING gosterir

```
WARNING: oc-runtime-supervisor.ps1 is DEPRECATED. Use oc-runtime-watchdog.ps1 instead.
```
Sonra `SupervisorTaskName` property bulunamadigi icin hata verir — config'den kaldirilmis.

### Test 5-6: Scheduled task durumu

```
OpenClawStartupPreflight  Ready  MSFT_TaskBootTrigger
OpenClawTaskWorker        Ready  MSFT_TaskLogonTrigger
OpenClawRuntimeWatchdog   Ready  MSFT_TaskTimeTrigger
OpenClawRuntimeSupervisor → NOT FOUND (kaldirilmis)
```

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | **Deprecated supervisor script hala diskte** | `bin/oc-runtime-supervisor.ps1` DEPRECATED header ile mevcut ama artik hicbir canonical path tarafindan referans edilmiyor. Guvenle silinebilir. |
| 2 | **Bootstrap heredoc'lar guncel degil** | Bootstrap'taki diger heredoc'lar (enqueue, retry, cancel, health vb.) F1.3 rejection envelope degisikliklerini icermiyor. Bootstrap v3.5 ile hepsi guncellenebilir. |
| 3 | **Rapor dosyalari (F1.1, F1.2) eski terminoloji iceriyor** | `docs/TASK-F1.1-REPORT.md` ve `docs/TASK-F1.2-REPORT.md` tarihsel kayit olarak supervisor referanslari iceriyor. Bunlar historical record, canonical degil. |
| 4 | **`oc-runtime-supervisor.ps1.bak-*` dosyalari** | Bootstrap'in olusturdugu backup dosyalari mevcut olabilir. Temizlik gerektirmiyor. |
