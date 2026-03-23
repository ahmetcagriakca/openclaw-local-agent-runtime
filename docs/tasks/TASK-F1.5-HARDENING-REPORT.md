# Task F1.5-hardening — Boot-Correlated Reboot Verification: Report

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `bin/oc-runtime-startup-preflight.ps1` | Preflight sonunda `logs/preflight-state.json` atomik state dosyasi yazilir (preflightRanUtc, bootTimeUtc, result) |
| `bin/oc-task-health.ps1` | Log parsing yerine state file okuma. Yeni alanlar: `preflightBootTimeUtc`, `preflightResult`, `preflightBootCorrelated`, `currentBootTimeUtc` |
| `bin/oc-reboot-validate.ps1` | Post phase'e `preflight boot-correlated` check eklendi — boot time eslemesi zorunlu |

---

## Tam Patch

### Preflight — atomic state file (preflight sonunda)

```powershell
$bootTimeUtc = $null
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $bootTimeUtc = $os.LastBootUpTime.ToUniversalTime().ToString('o')
}
catch { }

$stateFile = [ordered]@{
    preflightRanUtc = [DateTime]::UtcNow.ToString('o')
    bootTimeUtc     = $bootTimeUtc
    result          = $overallStatus
    checksCount     = $checks.Count
    repairsCount    = $repairs.Count
}
Save-OcJson -Path (Join-Path $config.LogsPath 'preflight-state.json') -Object $stateFile
```

### Health — state file okuma + boot correlation

```diff
-# Detect last preflight from logs (200 line scan)
+# Read preflight state file (boot-correlated, atomic)
+$preflightStatePath = Join-Path $config.LogsPath 'preflight-state.json'
+$pfState = Get-Content -Raw $preflightStatePath | ConvertFrom-Json
+$lastPreflightUtc = $pfState.preflightRanUtc
+$preflightBootTimeUtc = $pfState.bootTimeUtc
+$preflightResult = $pfState.result
+
+$currentBootTimeUtc = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
+$preflightBootCorrelated = ($preflightBootTimeUtc -eq $currentBootTimeUtc)

 Output:
+    preflightBootTimeUtc = $preflightBootTimeUtc
+    preflightResult = $preflightResult
+    preflightBootCorrelated = $preflightBootCorrelated
+    currentBootTimeUtc = $currentBootTimeUtc
```

### Reboot-validate post phase — boot correlation check

```diff
+    # 2. Preflight boot-correlated to current session
+    $bootCorrelated = ($health.preflightBootCorrelated -eq $true)
+    Add-Check -Name 'preflight boot-correlated' -Ok $bootCorrelated -Detail ('preflightBoot=' + $health.preflightBootTimeUtc + ' currentBoot=' + $health.currentBootTimeUtc)
```

---

## Smoke Test Komutlari

```powershell
# Test 1: Preflight writes state file
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-runtime-startup-preflight.ps1
Get-Content "$env:USERPROFILE\oc\logs\preflight-state.json"

# Test 2: Health shows boot-correlated fields
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-task-health.ps1

# Test 3: Pre-reboot READY
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-reboot-validate.ps1 -Phase pre

# Test 4: Post-reboot with current boot (correlation PASS)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-reboot-validate.ps1 -Phase post

# Test 5: Anti-cheat — tamper boot time, correlation must FAIL
# (manually set preflight-state.json bootTimeUtc to old date)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File bin\oc-reboot-validate.ps1 -Phase post
```

---

## Observed Output

### Test 1: State file

```json
{
    "preflightRanUtc": "2026-03-22T18:02:00.0928400Z",
    "bootTimeUtc": "2026-03-11T08:47:23.5000000Z",
    "result": "ok",
    "checksCount": 10,
    "repairsCount": 0
}
```

### Test 2: Health — boot-correlated

```json
{
    "status": "ok",
    "lastPreflightUtc": "2026-03-22T18:02:00.0928400Z",
    "preflightBootTimeUtc": "2026-03-11T08:47:23.5000000Z",
    "preflightResult": "ok",
    "preflightBootCorrelated": true,
    "currentBootTimeUtc": "2026-03-11T08:47:23.5000000Z",
    "lastWatchdogUtc": "2026-03-22T18:00:04.7658300Z"
}
```

### Test 3: Pre-reboot — READY (8/8)

```json
{ "phase": "pre", "result": "READY", "pass": 8, "fail": 0 }
```

### Test 4: Post-reboot — NOT_READY (7/8, worker inactive beklenen)

```json
{
    "phase": "post", "result": "NOT_READY", "pass": 7, "fail": 1,
    "checks": [
        { "check": "preflight ran", "result": "PASS" },
        { "check": "preflight boot-correlated", "result": "PASS",
          "detail": "preflightBoot=2026-03-11T08:47:23Z currentBoot=2026-03-11T08:47:23Z" },
        { "check": "health status", "result": "PASS" },
        { "check": "preflight task", "result": "PASS" },
        { "check": "worker task", "result": "PASS" },
        { "check": "watchdog task", "result": "PASS" },
        { "check": "worker active", "result": "FAIL" },
        { "check": "no stuck tasks", "result": "PASS" }
    ]
}
```

### Test 5: Anti-cheat — stale boot time FAIL

```json
{
    "phase": "post", "result": "NOT_READY", "pass": 6, "fail": 2,
    "checks": [
        { "check": "preflight ran", "result": "PASS" },
        { "check": "preflight boot-correlated", "result": "FAIL",
          "detail": "preflightBoot=2026-01-01T00:00:00Z currentBoot=2026-03-11T08:47:23Z" },
        ...
    ]
}
```

Eski bir preflight state dosyasi ile post phase PASS edemez — boot time eslesmesi zorunlu.

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | **Gercek reboot testi yapilmadi** | Boot correlation mekanizmasi kanitlandi ama gercek reboot ile dogrulanmadi. |
| 2 | **State file disk-based** | preflight-state.json silme/bozulmaya karsi korunmuyor. Preflight yeniden calistirilirsa uzerine yazar. |
| 3 | **Watchdog hala log-based** | Watchdog icin state file yok, son calisma log'dan parse ediliyor. |
