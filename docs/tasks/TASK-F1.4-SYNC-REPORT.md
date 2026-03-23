# Task F1.4-sync — Bootstrap Heredoc Sync: Report

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `oc-task-runtime-bootstrap-v3.4.ps1` | Common heredoc: `ConvertTo-OcUtcDateTime` ve `Get-OcUtcAgeMinutes` fonksiyonlari eklendi. Worker heredoc: `[DateTime]::Parse($leasedAt)` -> `Get-OcUtcAgeMinutes`. Health heredoc: `[DateTime]::Parse($ref)` -> `Get-OcUtcAgeMinutes`. Repair heredoc: `[DateTime]::Parse($startedUtc/createdUtc)` -> `ConvertTo-OcUtcDateTime`. |

---

## Tam Patch

### Common heredoc — yeni helper fonksiyonlari (satir ~504)

```diff
+function ConvertTo-OcUtcDateTime {
+    param([Parameter(Mandatory = $true)][string]$IsoString)
+    return [DateTime]::Parse($IsoString).ToUniversalTime()
+}
+
+function Get-OcUtcAgeMinutes {
+    param([Parameter(Mandatory = $true)][string]$IsoString)
+    return ([DateTime]::UtcNow - [DateTime]::Parse($IsoString).ToUniversalTime()).TotalMinutes
+}
+
 function Assert-OcTaskId {
```

### Worker heredoc (satir ~1038)

```diff
-                $leaseAge = ([DateTime]::UtcNow - [DateTime]::Parse($leasedAt)).TotalMinutes
+                $leaseAge = (Get-OcUtcAgeMinutes -IsoString $leasedAt)
```

### Health heredoc (satir ~1428)

```diff
-                    $taskAge = ([DateTime]::UtcNow - [DateTime]::Parse($ref)).TotalMinutes
+                    $taskAge = (Get-OcUtcAgeMinutes -IsoString $ref)
```

### Repair heredoc (satir ~1766-1767)

```diff
-        if (-not [string]::IsNullOrWhiteSpace([string]$startedUtc)) { $refTime = [DateTime]::Parse($startedUtc) }
-        elseif (-not [string]::IsNullOrWhiteSpace([string]$createdUtc)) { $refTime = [DateTime]::Parse($createdUtc) }
+        if (-not [string]::IsNullOrWhiteSpace([string]$startedUtc)) { $refTime = ConvertTo-OcUtcDateTime -IsoString $startedUtc }
+        elseif (-not [string]::IsNullOrWhiteSpace([string]$createdUtc)) { $refTime = ConvertTo-OcUtcDateTime -IsoString $createdUtc }
```

---

## Grep Evidence

### Bootstrap — no stale DateTime::Parse (only helpers)

```
grep -n "\[DateTime\]::Parse\(\$" oc-task-runtime-bootstrap-v3.4.ps1
```

```
506:    return [DateTime]::Parse($IsoString).ToUniversalTime()
511:    return ([DateTime]::UtcNow - [DateTime]::Parse($IsoString).ToUniversalTime()).TotalMinutes
```

Sadece helper fonksiyonlar — tum consumer'lar guncellendi.

### Live scripts — no stale DateTime::Parse (only helpers + deprecated)

```
grep -rn "\[DateTime\]::Parse\(\$" bin/*.ps1
```

```
bin/oc-runtime-supervisor.ps1:120:  (DEPRECATED)
bin/oc-runtime-supervisor.ps1:159:  (DEPRECATED)
bin/oc-task-common.ps1:340:  (helper)
bin/oc-task-common.ps1:345:  (helper)
```

Sadece deprecated supervisor ve helper fonksiyonlar.

### Threshold alignment

```
grep -n "StuckWarningMinutes\|StuckRecoveryMinutes\|StaleLeaseMinutes" bin/oc-task-common.ps1 oc-task-runtime-bootstrap-v3.4.ps1
```

Her iki dosyada da ayni degerler: 30, 60, 30.

---

## Smoke Test Komutlari

```powershell
# Test 1-3: All scripts still work
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-watchdog.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-startup-preflight.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-task-health.ps1

# Test 4: Grep — no stale Parse in bootstrap
grep -n "\[DateTime\]::Parse\(\$" oc-task-runtime-bootstrap-v3.4.ps1
# Expected: only lines 506, 511 (helper functions)

# Test 5: Grep — no stale Parse in live canonical scripts
grep -rn "\[DateTime\]::Parse\(\$" bin/oc-runtime-watchdog.ps1 bin/oc-runtime-startup-preflight.ps1 bin/oc-task-health.ps1 bin/oc-task-repair.ps1 bin/oc-task-worker.ps1
# Expected: no output
```

---

## Observed Output

### Test 1: Watchdog — ok
```json
{ "phase": "watchdog", "status": "ok" }
```

### Test 2: Preflight — ok
```json
{ "phase": "startup-preflight", "status": "ok" }
```

### Test 3: Health — ok
```json
{ "status": "ok", "stuckCaseA": 0, "stuckCaseB": 0 }
```

### Test 4-5: Grep — clean
Bootstrap: only helper functions (lines 506, 511).
Live scripts: no stale Parse.

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | **Bootstrap enqueue/retry/cancel heredoc'lari** | F1.3 rejection envelope degisikliklerini icermiyor. Ayri bir bootstrap-sync task'i gerekli. |
| 2 | **Deprecated supervisor** | Hala eski Parse kullaniyor ama canonical degildir. |
