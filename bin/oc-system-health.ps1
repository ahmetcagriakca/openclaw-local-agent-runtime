<#
.SYNOPSIS
    Comprehensive system health check for all OpenClaw components.
    Outputs a single JSON object to stdout.
    Callable standalone (CLI), by dashboard, watchdog, or Telegram wrapper.

.NOTES
    Location: C:\Users\AKCA\oc\bin\oc-system-health.ps1
    Exit code: always 0 (health status is in JSON, not exit code)
#>

$ErrorActionPreference = 'Continue'
$scriptRoot = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $scriptRoot

$components = [ordered]@{}

# --- 1. WMCP Server -----------------------------------------------------------
try {
    $wmcpResp = Invoke-RestMethod 'http://localhost:8001/openapi.json' -TimeoutSec 5 -ErrorAction Stop
    if ($wmcpResp.info.title -eq 'windows-mcp') {
        $components['wmcp'] = @{ status = 'ok'; detail = 'windows-mcp on :8001' }
    } else {
        $components['wmcp'] = @{ status = 'error'; detail = 'unexpected response from :8001' }
    }
} catch {
    $components['wmcp'] = @{ status = 'error'; detail = $_.Exception.Message -replace '[\r\n]+',' ' }
}

# --- 2. WSL Instance ----------------------------------------------------------
try {
    # wsl --list outputs UTF-16LE; use [Console]::OutputEncoding or test with a direct command
    $wslTest = & wsl -d Ubuntu-E -- echo ok 2>&1 | Out-String
    if ($wslTest -match 'ok') {
        $components['wsl'] = @{ status = 'ok'; detail = 'Ubuntu-E running' }
    } else {
        $components['wsl'] = @{ status = 'error'; detail = 'Ubuntu-E not responding' }
    }
} catch {
    $components['wsl'] = @{ status = 'error'; detail = 'wsl command failed' }
}

# Enhance WSL detail with guardian state if available
$guardianStatePath = Join-Path $repoRoot 'logs' 'wsl-guardian-state.json'
if (Test-Path -LiteralPath $guardianStatePath) {
    try {
        $gState = Get-Content -Raw -LiteralPath $guardianStatePath | ConvertFrom-Json
        $wslRestarts = $gState.wsl.restartCount
        $ocRestarts = $gState.openclaw.restartCount
        if ($wslRestarts -gt 0 -or $ocRestarts -gt 0) {
            $components['wsl']['detail'] += " (WSL restarts: $wslRestarts, OC restarts: $ocRestarts)"
        }
    } catch { }
}

# --- 3. OpenClaw Gateway ------------------------------------------------------
try {
    $pgrepOut = & wsl -d Ubuntu-E -- pgrep -fa openclaw 2>&1 | Out-String
    $procLines = @(($pgrepOut -split "`n") | Where-Object { $_.Trim().Length -gt 0 })
    if ($procLines.Count -gt 0) {
        $components['openclaw'] = @{ status = 'ok'; detail = "$($procLines.Count) processes" }
    } else {
        $components['openclaw'] = @{ status = 'error'; detail = 'no openclaw process found' }
    }
} catch {
    $components['openclaw'] = @{ status = 'error'; detail = 'pgrep command failed' }
}

# --- 4. oc Runtime Health -----------------------------------------------------
try {
    $healthScript = Join-Path $scriptRoot 'oc-task-health.ps1'
    $healthJson = & pwsh -NoProfile -ExecutionPolicy Bypass -File $healthScript 2>&1 | Out-String
    $healthObj = $healthJson | ConvertFrom-Json
    $rtStatus = [string]$healthObj.status
    if ($rtStatus -eq 'ok') {
        $components['runtime'] = @{ status = 'ok'; detail = 'ok' }
    } elseif ($rtStatus -eq 'degraded') {
        $components['runtime'] = @{ status = 'degraded'; detail = 'degraded' }
    } else {
        $components['runtime'] = @{ status = 'error'; detail = $rtStatus }
    }
} catch {
    $components['runtime'] = @{ status = 'error'; detail = 'health script failed' }
}

# --- 5. Bridge Health (via runtime) -------------------------------------------
$allowlistPath = Join-Path $repoRoot 'bridge' 'allowlist.json'
if (Test-Path -LiteralPath $allowlistPath) {
    try {
        $allowlist = Get-Content -Raw -LiteralPath $allowlistPath | ConvertFrom-Json
        $userId = $allowlist.allowedUserIds | Select-Object -First 1
        if ([string]::IsNullOrWhiteSpace($userId)) { throw 'empty allowlist' }

        $bridgeScript = Join-Path $repoRoot 'bridge' 'oc-bridge.ps1'
        $reqObj = @{
            operation    = 'get_health'
            source       = 'system-health'
            sourceUserId = $userId
            requestId    = 'health-' + [DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
        } | ConvertTo-Json -Compress

        $bridgeOut = & pwsh -NoProfile -ExecutionPolicy Bypass -File $bridgeScript -RequestJson $reqObj 2>&1 | Out-String
        $bridgeObj = $bridgeOut | ConvertFrom-Json
        if ($bridgeObj.health -eq 'ok') {
            $components['bridge'] = @{ status = 'ok'; detail = 'health ok' }
        } else {
            $components['bridge'] = @{ status = 'error'; detail = "health: $($bridgeObj.health)" }
        }
    } catch {
        $components['bridge'] = @{ status = 'error'; detail = $_.Exception.Message -replace '[\r\n]+',' ' }
    }
} else {
    $components['bridge'] = @{ status = 'skipped'; detail = 'allowlist.json not found' }
}

# --- 6. Scheduled Tasks -------------------------------------------------------
$taskNames = @(
    'OpenClawTaskWorker',
    'OpenClawRuntimeWatchdog',
    'OpenClawStartupPreflight',
    'OpenClawWmcpServer',
    'OpenClawWslGuardian',
    'OpenClawDashboard'
)
$taskStates = [ordered]@{}
$okCount = 0
$totalCount = $taskNames.Count

foreach ($tn in $taskNames) {
    try {
        $st = Get-ScheduledTask -TaskName $tn -ErrorAction Stop
        $state = [string]$st.State
        $taskStates[$tn] = $state
        if ($state -eq 'Ready' -or $state -eq 'Running') { $okCount++ }
    } catch {
        $taskStates[$tn] = 'missing'
    }
}

$tasksStatus = 'ok'
if ($okCount -lt $totalCount -and $okCount -gt 0) { $tasksStatus = 'degraded' }
elseif ($okCount -eq 0) { $tasksStatus = 'error' }

$components['scheduledTasks'] = @{
    status = $tasksStatus
    detail = "$okCount/$totalCount ready"
    tasks  = $taskStates
}

# --- Overall ------------------------------------------------------------------
$overall = 'ok'
foreach ($c in $components.Values) {
    $s = $c['status']
    if ($s -eq 'error') { $overall = 'error'; break }
    if ($s -eq 'degraded' -or $s -eq 'skipped') {
        if ($overall -ne 'error') { $overall = 'degraded' }
    }
}

$result = [ordered]@{
    timestamp  = [DateTime]::UtcNow.ToString('o')
    overall    = $overall
    components = $components
}

($result | ConvertTo-Json -Depth 10)
exit 0
