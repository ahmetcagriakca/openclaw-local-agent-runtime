# Görev 1 — Worker Fail Recovery: Deploy & Smoke Test

## Yapılan değişiklikler

### Worker (`oc-task-worker.ps1`)
- Fail sonrası ticket artık silinmiyor → `queue\dead-letter\` klasörüne taşınıyor
- Runner crash ederse (exit -99) veya non-zero dönerse worker task'ı `failed`'a zorluyor
- `events.jsonl`'e `task_failed_by_worker` event düşüyor
- `worker.log`'a sebep ve exit code yazılıyor
- Başarılı task'larda ticket normal silinir (davranış değişmedi)
- pwsh tam yol fallback eklendi

### Yeni dosya: `oc-task-repair.ps1`
- Stuck `running` veya `queued` task'ları bulur
- Configurable süre eşiği (`-StuckMinutes`, varsayılan 60)
- `-DryRun` ile önce bak, sonra düzelt
- `events.jsonl`'e `task_repaired` event
- `control-plane.log`'a kayıt
- Dead-letter ve orphan lease sayısını raporlar

### Yeni klasör: `queue\dead-letter\`
- Fail eden ticket'lar burada birikir
- Healthcheck'te `deadLetterTickets` sayacı var
- İnceleme sonrası manuel silinir

### Healthcheck
- `deadLetterTickets` sayacı eklendi

## Deploy

```powershell
cd $env:USERPROFILE\oc
powershell -ExecutionPolicy Bypass -File .\oc-task-runtime-bootstrap-v3.1.ps1
```

## WSL wrapper ekle (repair için)

```powershell
$wslBin = "\\wsl$\Ubuntu-E\home\akca\bin"
@'
#!/usr/bin/env bash
set -euo pipefail
WIN_SCRIPT='C:\Users\AKCA\oc\bin\oc-task-repair.ps1'
STUCK="${1:-60}"
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$WIN_SCRIPT" -StuckMinutes "$STUCK"
'@ | Set-Content -Path "$wslBin\oc-task-repair" -Encoding UTF8 -NoNewline

# BOM temizle
$p = Join-Path $wslBin 'oc-task-repair'
$bytes = [System.IO.File]::ReadAllBytes($p)
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    [System.IO.File]::WriteAllBytes($p, $bytes[3..($bytes.Length-1)])
}

wsl -d Ubuntu-E -- chmod +x /home/akca/bin/oc-task-repair
```

## Smoke test 1 — Normal başarılı task (regresyon)

```powershell
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"recovery-ok.txt","content":"normal task works"}'))
$raw = powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 $b64
$tid = ($raw | ConvertFrom-Json).taskId
Start-Sleep -Seconds 8
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-get.ps1 -TaskId $tid
Test-Path $env:USERPROFILE\oc\results\recovery-ok.txt
Write-Output "=== Dead-letter count ==="
(Get-ChildItem $env:USERPROFILE\oc\queue\dead-letter\*.json -ErrorAction SilentlyContinue).Count
```

Beklenen: task `succeeded`, dosya var, dead-letter count 0 (bu task için).

## Smoke test 2 — Yapay fail (runner crash simülasyonu)

```powershell
# Geçici olarak runner'ı boz
$rf = "$env:USERPROFILE\oc\bin\oc-task-runner.ps1"
$backup = Get-Content -Raw $rf
"throw 'SIMULATED CRASH'" | Set-Content -Encoding UTF8 $rf

# Task enqueue
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"should-not-exist.txt","content":"nope"}'))
$raw = powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 $b64
$tid = ($raw | ConvertFrom-Json).taskId
Start-Sleep -Seconds 8

# Kontrol
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-get.ps1 -TaskId $tid
Write-Output "=== File should NOT exist ==="
Test-Path $env:USERPROFILE\oc\results\should-not-exist.txt
Write-Output "=== Dead-letter ==="
Get-ChildItem $env:USERPROFILE\oc\queue\dead-letter\*.json -ErrorAction SilentlyContinue | Select-Object Name
Write-Output "=== Worker log (last 5) ==="
Get-Content $env:USERPROFILE\oc\logs\worker.log | Select-Object -Last 5

# Runner'ı geri yükle
$backup | Set-Content -Encoding UTF8 $rf
Write-Output "Runner restored."
```

Beklenen:
- task status: `failed`
- lastError: `Worker-level failure: runner exited with code 1`
- dosya: `False`
- dead-letter: 1 ticket
- worker.log: `task_failed_by_worker` veya `force-failed` mesajı

## Smoke test 3 — Repair (stuck task simülasyonu)

```powershell
# Dry run
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-repair.ps1 -StuckMinutes 1 -DryRun

# Gerçek repair (1 dakikadan eski stuck task varsa)
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-repair.ps1 -StuckMinutes 1
```

## Smoke test 4 — Healthcheck (dead-letter sayacı)

```powershell
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-health.ps1
```

Beklenen: `deadLetterTickets` > 0 (test 2'den).

## Tüm testleri tek seferde çalıştır

```powershell
# === TEST 1: Normal task ===
Write-Output "=== TEST 1: Normal task ==="
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"recovery-ok.txt","content":"normal task works"}'))
$raw = powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 $b64
$tid1 = ($raw | ConvertFrom-Json).taskId
Start-Sleep -Seconds 8
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-get.ps1 -TaskId $tid1
Test-Path $env:USERPROFILE\oc\results\recovery-ok.txt

# === TEST 2: Simulated crash ===
Write-Output "=== TEST 2: Simulated crash ==="
$rf = "$env:USERPROFILE\oc\bin\oc-task-runner.ps1"
$backup = Get-Content -Raw $rf
"throw 'SIMULATED CRASH'" | Set-Content -Encoding UTF8 $rf

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"should-not-exist.txt","content":"nope"}'))
$raw = powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 $b64
$tid2 = ($raw | ConvertFrom-Json).taskId
Start-Sleep -Seconds 8
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-get.ps1 -TaskId $tid2
Write-Output "File should NOT exist:"
Test-Path $env:USERPROFILE\oc\results\should-not-exist.txt
Write-Output "Dead-letter tickets:"
Get-ChildItem $env:USERPROFILE\oc\queue\dead-letter\*.json -ErrorAction SilentlyContinue | Select-Object Name
Write-Output "Worker log (last 5):"
Get-Content $env:USERPROFILE\oc\logs\worker.log | Select-Object -Last 5
$backup | Set-Content -Encoding UTF8 $rf
Write-Output "Runner restored."

# === TEST 3: Repair dry run ===
Write-Output "=== TEST 3: Repair dry run ==="
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-repair.ps1 -StuckMinutes 1 -DryRun

# === TEST 4: Healthcheck ===
Write-Output "=== TEST 4: Healthcheck ==="
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\oc\bin\oc-task-health.ps1
```
