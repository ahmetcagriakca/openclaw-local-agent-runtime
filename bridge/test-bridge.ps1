# test-bridge.ps1
# Minimal validation utility simulating Vezir behavior.
# Not Vezir implementation. Validation-only.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('all', 'startup', 'validation', 'submit', 'poll', 'cancel', 'health')]
    [string]$Suite
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$bridgeScript = Join-Path (Split-Path -Parent $PSCommandPath) 'oc-bridge.ps1'
$bridgeRoot = Split-Path -Parent $PSCommandPath
$allowlistPath = Join-Path $bridgeRoot 'allowlist.json'
$testResults = @()
$testsPassed = 0
$testsFailed = 0

function Invoke-Bridge {
    param([string]$Json)

    $pwshExe = 'C:\Program Files\PowerShell\7\pwsh.exe'
    if (-not (Test-Path -LiteralPath $pwshExe)) { $pwshExe = 'pwsh' }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $pwshExe
    $escapedJson = $Json.Replace('"', '\"')
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$bridgeScript`" -RequestJson `"$escapedJson`""
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit(60000) | Out-Null

    $parsed = $null
    try { $parsed = $stdout.Trim() | ConvertFrom-Json } catch { }

    return @{
        ExitCode = $proc.ExitCode
        Stdout = $stdout.Trim()
        Stderr = $stderr.Trim()
        Parsed = $parsed
    }
}

function Invoke-BridgeWithBadAllowlist {
    param([string]$AllowlistFile, [string]$Json)

    $pwshExe = 'C:\Program Files\PowerShell\7\pwsh.exe'
    if (-not (Test-Path -LiteralPath $pwshExe)) { $pwshExe = 'pwsh' }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $pwshExe
    $escapedJson = $Json.Replace('"', '\"')
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$bridgeScript`" -RequestJson `"$escapedJson`" -AllowlistPath `"$AllowlistFile`""
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit(30000) | Out-Null

    return @{ ExitCode = $proc.ExitCode; Stdout = $stdout.Trim(); Stderr = $stderr.Trim() }
}

function Assert-Test {
    param([string]$Name, [bool]$Condition, [string]$Detail = '')
    if ($Condition) {
        $script:testsPassed++
        Write-Host "  PASS: $Name" -ForegroundColor Green
    }
    else {
        $script:testsFailed++
        Write-Host "  FAIL: $Name -- $Detail" -ForegroundColor Red
    }
}

# ======================================================================
# TEST SUITES
# ======================================================================

function Test-Startup {
    Write-Host "`n=== STARTUP FAIL-CLOSED TESTS ===" -ForegroundColor Cyan

    # Test: missing allowlist
    $r = Invoke-BridgeWithBadAllowlist -AllowlistFile 'C:\nonexistent\allowlist.json' -Json '{"operation":"get_health","source":"test","sourceUserId":"test-user-001","requestId":"req-s1"}'
    Assert-Test 'Missing allowlist -> exit 2' ($r.ExitCode -eq 2) ('ExitCode=' + $r.ExitCode)

    # Test: empty allowlist
    $emptyFile = Join-Path $bridgeRoot 'test-empty-allowlist.json'
    '{"allowedUserIds":[]}' | Set-Content -Path $emptyFile -Encoding UTF8
    $r = Invoke-BridgeWithBadAllowlist -AllowlistFile $emptyFile -Json '{"operation":"get_health","source":"test","sourceUserId":"test-user-001","requestId":"req-s2"}'
    Assert-Test 'Empty allowlist -> exit 2' ($r.ExitCode -eq 2) ('ExitCode=' + $r.ExitCode)
    Remove-Item -LiteralPath $emptyFile -Force -ErrorAction SilentlyContinue

    # Test: unparseable allowlist
    $badFile = Join-Path $bridgeRoot 'test-bad-allowlist.json'
    'NOT JSON{{{' | Set-Content -Path $badFile -Encoding UTF8
    $r = Invoke-BridgeWithBadAllowlist -AllowlistFile $badFile -Json '{"operation":"get_health","source":"test","sourceUserId":"test-user-001","requestId":"req-s3"}'
    Assert-Test 'Unparseable allowlist -> exit 2' ($r.ExitCode -eq 2) ('ExitCode=' + $r.ExitCode)
    Remove-Item -LiteralPath $badFile -Force -ErrorAction SilentlyContinue
}

function Test-Validation {
    Write-Host "`n=== VALIDATION TESTS ===" -ForegroundColor Cyan

    # Missing fields
    $r = Invoke-Bridge -Json '{"operation":"get_health"}'
    Assert-Test 'Missing source/sourceUserId/requestId -> rejected' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'INVALID_INPUT') ($r.Stdout)

    # Unknown operation
    $r = Invoke-Bridge -Json '{"operation":"hack","source":"test","sourceUserId":"test-user-001","requestId":"req-v2"}'
    Assert-Test 'Unknown operation -> rejected INVALID_INPUT' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'INVALID_INPUT') ($r.Stdout)

    # Unauthorized user
    $r = Invoke-Bridge -Json '{"operation":"get_health","source":"test","sourceUserId":"UNAUTHORIZED","requestId":"req-v3"}'
    Assert-Test 'Unauthorized sourceUserId -> SOURCE_NOT_ALLOWED' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'SOURCE_NOT_ALLOWED') ($r.Stdout)

    # Pending approval
    $r = Invoke-Bridge -Json '{"operation":"submit_task","taskName":"create_note","arguments":{},"source":"test","sourceUserId":"test-user-001","requestId":"req-v4","approvalStatus":"pending"}'
    Assert-Test 'approvalStatus=pending -> APPROVAL_REQUIRED' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'APPROVAL_REQUIRED') ($r.Stdout)

    # Missing taskId for get_task_status
    $r = Invoke-Bridge -Json '{"operation":"get_task_status","source":"test","sourceUserId":"test-user-001","requestId":"req-v5"}'
    Assert-Test 'Missing taskId -> INVALID_INPUT' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'INVALID_INPUT') ($r.Stdout)

    # Invalid taskId format
    $r = Invoke-Bridge -Json '{"operation":"get_task_status","taskId":"bad-id","source":"test","sourceUserId":"test-user-001","requestId":"req-v6"}'
    Assert-Test 'Invalid taskId format -> INVALID_INPUT' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'INVALID_INPUT') ($r.Stdout)

    # Malformed JSON
    $r = Invoke-Bridge -Json 'NOT-JSON{{{'
    Assert-Test 'Malformed JSON -> rejected INVALID_INPUT' ($null -ne $r.Parsed -and $r.Parsed.status -eq 'rejected') ($r.Stdout)
}

function Test-Submit {
    Write-Host "`n=== SUBMIT TASK TEST ===" -ForegroundColor Cyan

    $r = Invoke-Bridge -Json '{"operation":"submit_task","taskName":"create_note","arguments":{"filename":"bridge-test.txt","content":"Bridge Phase 1.5-E OK"},"source":"telegram","sourceUserId":"test-user-001","requestId":"req-submit-1","approvalStatus":"preapproved"}'
    Assert-Test 'submit_task -> accepted' ($r.Parsed.status -eq 'accepted') ($r.Stdout)
    $hasTaskId = ($null -ne $r.Parsed.PSObject.Properties['taskId'] -and -not [string]::IsNullOrWhiteSpace([string]$r.Parsed.taskId))
    Assert-Test 'submit_task -> has taskId' $hasTaskId ($r.Stdout)
    Assert-Test 'submit_task -> requestId echoed' ($r.Parsed.requestId -eq 'req-submit-1') ($r.Stdout)

    if ($r.Parsed.status -eq 'accepted') {
        $script:submittedTaskId = [string]$r.Parsed.taskId
        Write-Host "  Submitted taskId: $($script:submittedTaskId)" -ForegroundColor Yellow
    }

    # Unknown task
    $r = Invoke-Bridge -Json '{"operation":"submit_task","taskName":"nonexistent_task","arguments":{},"source":"telegram","sourceUserId":"test-user-001","requestId":"req-submit-2","approvalStatus":"approved"}'
    Assert-Test 'submit_task unknown task -> UNKNOWN_TASK' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'UNKNOWN_TASK') ($r.Stdout)
}

function Test-Poll {
    Write-Host "`n=== POLLING TEST ===" -ForegroundColor Cyan

    if ([string]::IsNullOrWhiteSpace($script:submittedTaskId)) {
        Write-Host "  SKIP: No submitted task to poll." -ForegroundColor Yellow
        return
    }

    $taskId = $script:submittedTaskId
    $maxPolls = 15
    $pollCount = 0
    $finalStatus = ''

    while ($pollCount -lt $maxPolls) {
        $pollCount++
        Start-Sleep -Seconds 2

        $r = Invoke-Bridge -Json ('{"operation":"get_task_status","taskId":"' + $taskId + '","source":"telegram","sourceUserId":"test-user-001","requestId":"req-poll-' + $pollCount + '"}')

        if ($null -eq $r.Parsed) {
            Write-Host "  Poll $pollCount : unparseable response" -ForegroundColor Red
            continue
        }

        $pollStatus = [string]$r.Parsed.status
        Write-Host "  Poll $pollCount : status=$pollStatus taskStatus=$([string]$r.Parsed.taskStatus)" -ForegroundColor Gray

        if ($pollStatus -eq 'completed') {
            $finalStatus = [string]$r.Parsed.taskStatus
            break
        }

        if ($pollStatus -eq 'not_found' -or $pollStatus -eq 'error') {
            break
        }
    }

    Assert-Test 'Polling reached terminal state' ($finalStatus -in @('succeeded', 'failed', 'cancelled')) ('finalStatus=' + $finalStatus)

    if ($finalStatus -eq 'succeeded') {
        $lastPoll = $r.Parsed
        Assert-Test 'Terminal succeeded has result' ($null -ne $lastPoll.result) ''
        Assert-Test 'Terminal succeeded has summary' (-not [string]::IsNullOrWhiteSpace([string]$lastPoll.result.summary)) ''
        Assert-Test 'Terminal succeeded has no failureReason' ($null -eq $lastPoll.PSObject.Properties['failureReason'] -or [string]::IsNullOrWhiteSpace([string]$lastPoll.failureReason)) ''
    }
    elseif ($finalStatus -eq 'failed' -or $finalStatus -eq 'cancelled') {
        $lastPoll = $r.Parsed
        Assert-Test 'Terminal failed/cancelled has failureReason' (-not [string]::IsNullOrWhiteSpace([string]$lastPoll.failureReason)) ''
    }
}

function Test-Cancel {
    Write-Host "`n=== CANCEL TEST ===" -ForegroundColor Cyan

    # Cancel nonexistent task
    $r = Invoke-Bridge -Json '{"operation":"cancel_task","taskId":"task-99990101-000000000-0000","source":"telegram","sourceUserId":"test-user-001","requestId":"req-cancel-1"}'
    Assert-Test 'Cancel nonexistent -> TASK_NOT_FOUND' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'TASK_NOT_FOUND') ($r.Stdout)

    # Cancel already terminal (use submitted task if available)
    if (-not [string]::IsNullOrWhiteSpace($script:submittedTaskId)) {
        $r = Invoke-Bridge -Json ('{"operation":"cancel_task","taskId":"' + $script:submittedTaskId + '","source":"telegram","sourceUserId":"test-user-001","requestId":"req-cancel-2"}')
        Assert-Test 'Cancel terminal task -> CANCEL_REJECTED' ($r.Parsed.status -eq 'rejected' -and $r.Parsed.errorCode -eq 'CANCEL_REJECTED') ($r.Stdout)
    }
}

function Test-Health {
    Write-Host "`n=== HEALTH TEST ===" -ForegroundColor Cyan

    $r = Invoke-Bridge -Json '{"operation":"get_health","source":"telegram","sourceUserId":"test-user-001","requestId":"req-health-1"}'
    Assert-Test 'get_health -> status ok' ($r.Parsed.status -eq 'ok') ($r.Stdout)
    Assert-Test 'get_health -> has health field' ($r.Parsed.health -in @('ok', 'degraded', 'error')) ($r.Stdout)
    Assert-Test 'get_health -> has requestId' ($r.Parsed.requestId -eq 'req-health-1') ($r.Stdout)

    # Verify no internal fields leaked
    $internalFields = @('basePath', 'runtimeRoot', 'workerActive', 'scheduledTaskState', 'pendingTickets', 'stuckTasks', 'statusReasons')
    $leaked = @($internalFields | Where-Object { $null -ne $r.Parsed.PSObject.Properties[$_] })
    Assert-Test 'get_health -> no internal fields leaked' ($leaked.Count -eq 0) ('Leaked: ' + ($leaked -join ', '))
}

# ======================================================================
# EXECUTION
# ======================================================================

$script:submittedTaskId = ''

switch ($Suite) {
    'startup'    { Test-Startup }
    'validation' { Test-Validation }
    'submit'     { Test-Submit }
    'poll'       { Test-Submit; Test-Poll }
    'cancel'     { Test-Submit; Test-Poll; Test-Cancel }
    'health'     { Test-Health }
    'all'        { Test-Startup; Test-Validation; Test-Submit; Test-Poll; Test-Cancel; Test-Health }
}

Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "Passed: $testsPassed" -ForegroundColor Green
Write-Host "Failed: $testsFailed" -ForegroundColor $(if ($testsFailed -gt 0) { 'Red' } else { 'Green' })

if ($testsFailed -gt 0) { exit 1 }
exit 0
