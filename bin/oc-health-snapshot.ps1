<#
.SYNOPSIS
    Calls oc-system-health.ps1, writes snapshot + appends history line.
    Intended to be called by the watchdog every 15 minutes.

.NOTES
    Location: C:\Users\AKCA\oc\bin\oc-health-snapshot.ps1
    Output:   logs/health-snapshot.json  (overwritten each time)
              logs/health-history.jsonl  (append-only, one JSON line per check)
#>

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $scriptRoot
$logsPath = Join-Path $repoRoot 'logs'

if (-not (Test-Path -LiteralPath $logsPath)) {
    New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
}

$healthScript = Join-Path $scriptRoot 'oc-system-health.ps1'
$healthJson = & pwsh -NoProfile -ExecutionPolicy Bypass -File $healthScript 2>&1 | Out-String
$healthJson = $healthJson.Trim()

# Write full snapshot (overwrite)
$snapshotPath = Join-Path $logsPath 'health-snapshot.json'
[System.IO.File]::WriteAllText($snapshotPath, $healthJson, [System.Text.Encoding]::UTF8)

# Parse and build history line
try {
    $healthObj = $healthJson | ConvertFrom-Json
    $c = $healthObj.components

    $historyLine = [ordered]@{
        timestamp = $healthObj.timestamp
        overall   = $healthObj.overall
        wmcp      = $c.wmcp.status
        wsl       = $c.wsl.status
        openclaw  = $c.openclaw.status
        runtime   = $c.runtime.status
        bridge    = $c.bridge.status
        tasks     = $c.scheduledTasks.detail
    } | ConvertTo-Json -Compress

    $historyPath = Join-Path $logsPath 'health-history.jsonl'
    Add-Content -LiteralPath $historyPath -Value $historyLine -Encoding UTF8
} catch {
    Write-Warning "[health-snapshot] Failed to write history line: $_"
}

Write-Host "[health-snapshot] Snapshot written to $snapshotPath"
exit 0
