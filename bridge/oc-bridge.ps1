# oc-bridge.ps1
# Phase 1.5-E Bridge implementation.
# Stateless PowerShell script entrypoint. Not a persistent server.
# OpenClaw invokes this script per-request with -RequestJson parameter.
#
# Physical form: single-invocation script.
# Each call processes one external request and exits.
# No state is held between invocations.
# Bridge is never an orchestrator.
param(
    [Parameter(Mandatory = $true)]
    [string]$RequestJson,

    [string]$AllowlistPath = '',
    [string]$AuditLogPath = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# --- Resolve paths ---
$bridgeRoot = Split-Path -Parent $PSCommandPath
$ocRoot = Split-Path -Parent $bridgeRoot
$binPath = Join-Path $ocRoot 'bin'

if ([string]::IsNullOrWhiteSpace($AllowlistPath)) {
    $AllowlistPath = $env:OC_BRIDGE_ALLOWLIST_PATH
}
if ([string]::IsNullOrWhiteSpace($AllowlistPath)) {
    $AllowlistPath = Join-Path $bridgeRoot 'allowlist.json'
}

if ([string]::IsNullOrWhiteSpace($AuditLogPath)) {
    $AuditLogPath = $env:OC_BRIDGE_AUDIT_LOG
}
if ([string]::IsNullOrWhiteSpace($AuditLogPath)) {
    $AuditLogPath = Join-Path $bridgeRoot 'logs' 'bridge-audit.jsonl'
}

$runtimeTimeoutSeconds = 30

# --- Audit helper ---
function Write-BridgeAudit {
    param(
        [string]$RequestId = '',
        [string]$Source = '',
        [string]$SourceUserId = '',
        [string]$Operation = '',
        [string]$TaskName = '',
        [string]$ApprovalStatus = '',
        [string]$Outcome = '',
        [string]$ErrorCode = '',
        [string]$RuntimeTaskId = '',
        [string]$Detail = ''
    )

    $entry = [ordered]@{
        ts            = [DateTime]::UtcNow.ToString('o')
        requestId     = $RequestId
        source        = $Source
        sourceUserId  = $SourceUserId
        operation     = $Operation
        taskName      = $TaskName
        approvalStatus = $ApprovalStatus
        outcome       = $Outcome
        errorCode     = $ErrorCode
        runtimeTaskId = $RuntimeTaskId
        detail        = $Detail
    }

    $dir = Split-Path -Parent $AuditLogPath
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $line = $entry | ConvertTo-Json -Compress -Depth 10
    [System.IO.File]::AppendAllText($AuditLogPath, $line + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

# --- Response helpers ---
function New-BridgeResponse {
    param([hashtable]$Fields)
    return ($Fields | ConvertTo-Json -Depth 20)
}

function New-RejectionResponse {
    param(
        [string]$ErrorCode,
        [string]$ErrorMessage,
        [string]$RequestId = '',
        [string]$TaskName = '',
        [string]$TaskId = ''
    )
    $resp = [ordered]@{
        status       = 'rejected'
        errorCode    = $ErrorCode
        errorMessage = $ErrorMessage
        requestId    = $RequestId
    }
    if (-not [string]::IsNullOrWhiteSpace($TaskName)) { $resp['taskName'] = $TaskName }
    if (-not [string]::IsNullOrWhiteSpace($TaskId)) { $resp['taskId'] = $TaskId }
    return ($resp | ConvertTo-Json -Depth 20)
}

function New-ErrorResponse {
    param(
        [string]$ErrorCode,
        [string]$ErrorMessage,
        [string]$RequestId = ''
    )
    return ([ordered]@{
        status       = 'error'
        errorCode    = $ErrorCode
        errorMessage = $ErrorMessage
        requestId    = $RequestId
    } | ConvertTo-Json -Depth 20)
}

# --- Allowlist loading (fail-closed) ---
# Bridge must refuse to start if allowlist is missing, empty, or unparseable.
# Uses [Console]::Error to avoid PowerShell overriding the exit code.
if (-not (Test-Path -LiteralPath $AllowlistPath)) {
    [Console]::Error.WriteLine("BRIDGE STARTUP FAILED: Allowlist file not found: $AllowlistPath")
    [Environment]::Exit(2)
}

$allowlistRaw = $null
try {
    $allowlistRaw = Get-Content -Raw -LiteralPath $AllowlistPath | ConvertFrom-Json
}
catch {
    [Console]::Error.WriteLine("BRIDGE STARTUP FAILED: Allowlist file is not valid JSON: $AllowlistPath")
    [Environment]::Exit(2)
}

$allowedUsers = @()
if ($null -ne $allowlistRaw -and $null -ne $allowlistRaw.PSObject.Properties['allowedUserIds']) {
    $allowedUsers = @($allowlistRaw.allowedUserIds)
}

if ($allowedUsers.Count -eq 0) {
    [Console]::Error.WriteLine("BRIDGE STARTUP FAILED: Allowlist is empty (zero entries): $AllowlistPath")
    [Environment]::Exit(2)
}

# --- Parse request ---
$req = $null
try {
    $req = $RequestJson | ConvertFrom-Json
}
catch {
    $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'Request is not valid JSON.'
    Write-BridgeAudit -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Unparseable JSON'
    Write-Output $r
    exit 1
}

# --- Extract common fields ---
$operation = ''
$source = ''
$sourceUserId = ''
$requestId = ''

if ($null -ne $req.PSObject.Properties['operation']) { $operation = [string]$req.operation }
if ($null -ne $req.PSObject.Properties['source']) { $source = [string]$req.source }
if ($null -ne $req.PSObject.Properties['sourceUserId']) { $sourceUserId = [string]$req.sourceUserId }
if ($null -ne $req.PSObject.Properties['requestId']) { $requestId = [string]$req.requestId }

# --- Step 1: Structural validation ---
$missingFields = @()
if ([string]::IsNullOrWhiteSpace($operation)) { $missingFields += 'operation' }
if ([string]::IsNullOrWhiteSpace($source)) { $missingFields += 'source' }
if ([string]::IsNullOrWhiteSpace($sourceUserId)) { $missingFields += 'sourceUserId' }
if ([string]::IsNullOrWhiteSpace($requestId)) { $missingFields += 'requestId' }

if ($missingFields.Count -gt 0) {
    $msg = 'Missing required fields: ' + ($missingFields -join ', ')
    $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage $msg -RequestId $requestId
    Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail $msg
    Write-Output $r
    exit 1
}

# --- Step 2: Operation validation ---
$validOperations = @('submit_task', 'get_task_status', 'cancel_task', 'get_health')
if ($operation -notin $validOperations) {
    $msg = 'Unknown operation: ' + $operation
    $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage $msg -RequestId $requestId
    Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail $msg
    Write-Output $r
    exit 1
}

# --- Step 3: Allowlist enforcement ---
if ($sourceUserId -notin $allowedUsers) {
    $r = New-RejectionResponse -ErrorCode 'SOURCE_NOT_ALLOWED' -ErrorMessage 'User is not authorized.' -RequestId $requestId
    Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'SOURCE_NOT_ALLOWED'
    Write-Output $r
    exit 1
}

# --- Runtime invocation helper ---
function Invoke-RuntimeScript {
    param(
        [string]$ScriptName,
        [string[]]$Arguments = @(),
        [int]$TimeoutSeconds = $script:runtimeTimeoutSeconds
    )

    $scriptPath = Join-Path $script:binPath $ScriptName
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        return @{ ExitCode = -1; Stdout = ''; TimedOut = $false; Error = "Script not found: $ScriptName" }
    }

    $pwshExe = 'C:\Program Files\PowerShell\7\pwsh.exe'
    if (-not (Test-Path -LiteralPath $pwshExe)) { $pwshExe = 'pwsh' }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $pwshExe
    $quotedArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $scriptPath + '"'))
    foreach ($arg in $Arguments) {
        if ($arg.StartsWith('-')) {
            $quotedArgs += $arg
        } else {
            $quotedArgs += ('"' + $arg.Replace('"', '\"') + '"')
        }
    }
    $psi.Arguments = $quotedArgs -join ' '
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $finished = $proc.WaitForExit($TimeoutSeconds * 1000)

    if (-not $finished) {
        try { $proc.Kill() } catch { }
        return @{ ExitCode = -2; Stdout = $stdout; TimedOut = $true; Error = "Timed out after ${TimeoutSeconds}s" }
    }

    return @{ ExitCode = $proc.ExitCode; Stdout = $stdout; TimedOut = $false; Error = $stderr }
}

# ======================================================================
# OPERATION DISPATCH
# ======================================================================

switch ($operation) {

    # ------------------------------------------------------------------
    'submit_task' {
        # Step 4: Operation-specific field validation
        $taskName = ''
        $approvalStatus = ''
        $arguments = $null

        if ($null -ne $req.PSObject.Properties['taskName']) { $taskName = [string]$req.taskName }
        if ($null -ne $req.PSObject.Properties['approvalStatus']) { $approvalStatus = [string]$req.approvalStatus }
        if ($null -ne $req.PSObject.Properties['arguments']) { $arguments = $req.arguments }

        if ([string]::IsNullOrWhiteSpace($taskName)) {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'Missing required field: taskName.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Missing taskName'
            Write-Output $r; exit 1
        }

        if ($taskName -notmatch '^[A-Za-z0-9_-]+$' -or $taskName.Length -gt 128) {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'Invalid taskName format.' -RequestId $requestId -TaskName $taskName
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Invalid taskName'
            Write-Output $r; exit 1
        }

        if ($null -eq $arguments) {
            $arguments = [ordered]@{}
        }
        if (-not ($arguments -is [System.Management.Automation.PSCustomObject] -or $arguments -is [System.Collections.IDictionary])) {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'arguments must be a JSON object.' -RequestId $requestId -TaskName $taskName
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Invalid arguments type'
            Write-Output $r; exit 1
        }

        # Validate approvalStatus
        $validApproval = @('approved', 'preapproved', 'pending')
        if ([string]::IsNullOrWhiteSpace($approvalStatus)) {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'Missing required field: approvalStatus.' -RequestId $requestId -TaskName $taskName
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Missing approvalStatus'
            Write-Output $r; exit 1
        }
        if ($approvalStatus -notin $validApproval) {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage ('Invalid approvalStatus: ' + $approvalStatus) -RequestId $requestId -TaskName $taskName
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -ApprovalStatus $approvalStatus -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Invalid approvalStatus value'
            Write-Output $r; exit 1
        }

        # Step 5: Approval pre-validation
        if ($approvalStatus -eq 'pending') {
            $r = New-RejectionResponse -ErrorCode 'APPROVAL_REQUIRED' -ErrorMessage 'Task requires approval before submission. approvalStatus is pending.' -RequestId $requestId -TaskName $taskName
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -ApprovalStatus $approvalStatus -Outcome 'rejected' -ErrorCode 'APPROVAL_REQUIRED'
            Write-Output $r; exit 1
        }

        # Step 6: Map to runtime — encode arguments as base64 JSON
        $inputJson = $arguments | ConvertTo-Json -Depth 20 -Compress
        $inputBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($inputJson))

        $rtArgs = @('-TaskName', $taskName, '-InputBase64', $inputBase64, '-Source', $source)
        $rtResult = Invoke-RuntimeScript -ScriptName 'oc-task-enqueue.ps1' -Arguments $rtArgs

        if ($rtResult.TimedOut) {
            $r = New-ErrorResponse -ErrorCode 'RUNTIME_UNAVAILABLE' -ErrorMessage 'Runtime did not respond in time.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -ApprovalStatus $approvalStatus -Outcome 'error' -ErrorCode 'RUNTIME_UNAVAILABLE' -Detail 'Timeout'
            Write-Output $r; exit 1
        }

        if ($rtResult.ExitCode -ne 0) {
            # Map runtime rejection to external rejection
            $rtResp = $null
            try { $rtResp = $rtResult.Stdout | ConvertFrom-Json } catch { }

            if ($null -ne $rtResp -and [string]$rtResp.status -eq 'rejected') {
                $extCode = switch ([string]$rtResp.reasonCode) {
                    'UNKNOWN_TASK'       { 'UNKNOWN_TASK' }
                    'INVALID_TASK_INPUT' { 'INVALID_INPUT' }
                    'TASK_POLICY_DENIED' { 'TASK_DISABLED' }
                    'APPROVAL_REQUIRED'  { 'APPROVAL_REQUIRED' }
                    default              { 'INVALID_INPUT' }
                }
                $r = New-RejectionResponse -ErrorCode $extCode -ErrorMessage ([string]$rtResp.message) -RequestId $requestId -TaskName $taskName
                Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -ApprovalStatus $approvalStatus -Outcome 'rejected' -ErrorCode $extCode -Detail ([string]$rtResp.reasonCode)
                Write-Output $r; exit 1
            }

            $r = New-ErrorResponse -ErrorCode 'RUNTIME_UNAVAILABLE' -ErrorMessage 'Runtime returned an unexpected error.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -ApprovalStatus $approvalStatus -Outcome 'error' -ErrorCode 'RUNTIME_UNAVAILABLE' -Detail ('Exit ' + $rtResult.ExitCode)
            Write-Output $r; exit 1
        }

        # Success
        $rtResp = $null
        try { $rtResp = $rtResult.Stdout | ConvertFrom-Json } catch { }

        $runtimeTaskId = ''
        if ($null -ne $rtResp) { $runtimeTaskId = [string]$rtResp.taskId }

        $r = New-BridgeResponse -Fields ([ordered]@{
            status    = 'accepted'
            taskId    = $runtimeTaskId
            taskName  = $taskName
            requestId = $requestId
        })

        Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -TaskName $taskName -ApprovalStatus $approvalStatus -Outcome 'allowed' -RuntimeTaskId $runtimeTaskId
        Write-Output $r; exit 0
    }

    # ------------------------------------------------------------------
    'get_task_status' {
        $taskId = ''
        if ($null -ne $req.PSObject.Properties['taskId']) { $taskId = [string]$req.taskId }

        if ([string]::IsNullOrWhiteSpace($taskId)) {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'Missing required field: taskId.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Missing taskId'
            Write-Output $r; exit 1
        }

        if ($taskId -notmatch '^task-[0-9]{8}-[0-9]{9}-[0-9]{4}$') {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'Invalid taskId format.' -RequestId $requestId -TaskId $taskId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Invalid taskId format'
            Write-Output $r; exit 1
        }

        # Query runtime for task snapshot
        $rtResult = Invoke-RuntimeScript -ScriptName 'oc-task-get.ps1' -Arguments @('-TaskId', $taskId)

        if ($rtResult.TimedOut) {
            $r = New-ErrorResponse -ErrorCode 'RUNTIME_UNAVAILABLE' -ErrorMessage 'Runtime did not respond in time.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'error' -ErrorCode 'RUNTIME_UNAVAILABLE' -RuntimeTaskId $taskId -Detail 'Timeout'
            Write-Output $r; exit 1
        }

        if ($rtResult.ExitCode -ne 0) {
            $r = New-RejectionResponse -ErrorCode 'TASK_NOT_FOUND' -ErrorMessage 'No task exists with this ID.' -RequestId $requestId -TaskId $taskId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'TASK_NOT_FOUND' -RuntimeTaskId $taskId
            Write-Output $r; exit 1
        }

        $taskSnap = $null
        try { $taskSnap = $rtResult.Stdout | ConvertFrom-Json } catch { }

        if ($null -eq $taskSnap) {
            $r = New-ErrorResponse -ErrorCode 'RUNTIME_UNAVAILABLE' -ErrorMessage 'Runtime returned unparseable task data.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'error' -ErrorCode 'RUNTIME_UNAVAILABLE' -RuntimeTaskId $taskId -Detail 'Unparseable task snapshot'
            Write-Output $r; exit 1
        }

        $taskStatus = [string]$taskSnap.status
        $taskName = [string]$taskSnap.taskName
        $lastError = $null
        if ($null -ne $taskSnap.PSObject.Properties['lastError']) {
            $lastError = $taskSnap.lastError
        }

        $terminalStatuses = @('succeeded', 'failed', 'cancelled')
        $isTerminal = ($taskStatus -in $terminalStatuses)

        if (-not $isTerminal) {
            # Non-terminal: in_progress
            $r = New-BridgeResponse -Fields ([ordered]@{
                status     = 'in_progress'
                taskId     = $taskId
                taskStatus = $taskStatus
                requestId  = $requestId
            })
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'allowed' -RuntimeTaskId $taskId -Detail ('in_progress: ' + $taskStatus)
            Write-Output $r; exit 0
        }

        # Terminal: build completed response
        $resp = [ordered]@{
            status     = 'completed'
            taskId     = $taskId
            taskStatus = $taskStatus
            requestId  = $requestId
        }

        if ($taskStatus -eq 'succeeded') {
            # Multi-call assembly: get output
            $outResult = Invoke-RuntimeScript -ScriptName 'oc-task-output.ps1' -Arguments @('-TaskId', $taskId)

            $outputPreview = $null
            if (-not $outResult.TimedOut -and $outResult.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($outResult.Stdout)) {
                $outputPreview = $outResult.Stdout
                if ($outputPreview.Length -gt 2000) {
                    $outputPreview = $outputPreview.Substring(0, 2000)
                }
            }

            $result = [ordered]@{
                summary = 'Task completed successfully.'
            }
            if ($null -ne $outputPreview) {
                $result['outputPreview'] = $outputPreview
            }
            $resp['result'] = $result
        }
        else {
            # failed or cancelled
            $failureReason = 'Task ' + $taskStatus + '.'
            if (-not [string]::IsNullOrWhiteSpace([string]$lastError)) {
                $failureReason = [string]$lastError
            }
            $resp['failureReason'] = $failureReason
        }

        $r = New-BridgeResponse -Fields $resp
        Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'allowed' -RuntimeTaskId $taskId -Detail ('completed: ' + $taskStatus)
        Write-Output $r; exit 0
    }

    # ------------------------------------------------------------------
    'cancel_task' {
        $taskId = ''
        if ($null -ne $req.PSObject.Properties['taskId']) { $taskId = [string]$req.taskId }

        if ([string]::IsNullOrWhiteSpace($taskId)) {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'Missing required field: taskId.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Missing taskId'
            Write-Output $r; exit 1
        }

        if ($taskId -notmatch '^task-[0-9]{8}-[0-9]{9}-[0-9]{4}$') {
            $r = New-RejectionResponse -ErrorCode 'INVALID_INPUT' -ErrorMessage 'Invalid taskId format.' -RequestId $requestId -TaskId $taskId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode 'INVALID_INPUT' -Detail 'Invalid taskId format'
            Write-Output $r; exit 1
        }

        $rtResult = Invoke-RuntimeScript -ScriptName 'oc-task-cancel.ps1' -Arguments @('-TaskId', $taskId, '-Source', $source)

        if ($rtResult.TimedOut) {
            $r = New-ErrorResponse -ErrorCode 'RUNTIME_UNAVAILABLE' -ErrorMessage 'Runtime did not respond in time.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'error' -ErrorCode 'RUNTIME_UNAVAILABLE' -RuntimeTaskId $taskId -Detail 'Timeout'
            Write-Output $r; exit 1
        }

        $rtResp = $null
        try { $rtResp = $rtResult.Stdout | ConvertFrom-Json } catch { }

        if ($rtResult.ExitCode -ne 0) {
            if ($null -ne $rtResp -and [string]$rtResp.status -eq 'rejected') {
                $extCode = switch ([string]$rtResp.reasonCode) {
                    'TASK_STATE_INVALID' { 'CANCEL_REJECTED' }
                    'UNKNOWN_TASK'       { 'TASK_NOT_FOUND' }
                    'INVALID_TASK_INPUT' { 'INVALID_INPUT' }
                    default              { 'CANCEL_REJECTED' }
                }
                $r = New-RejectionResponse -ErrorCode $extCode -ErrorMessage ([string]$rtResp.message) -RequestId $requestId -TaskId $taskId
                Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'rejected' -ErrorCode $extCode -RuntimeTaskId $taskId -Detail ([string]$rtResp.reasonCode)
                Write-Output $r; exit 1
            }

            $r = New-ErrorResponse -ErrorCode 'RUNTIME_UNAVAILABLE' -ErrorMessage 'Runtime returned an unexpected error.' -RequestId $requestId
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'error' -ErrorCode 'RUNTIME_UNAVAILABLE' -RuntimeTaskId $taskId -Detail ('Exit ' + $rtResult.ExitCode)
            Write-Output $r; exit 1
        }

        $cancelStatus = 'cancel_requested'
        if ($null -ne $rtResp) { $cancelStatus = [string]$rtResp.status }

        $r = New-BridgeResponse -Fields ([ordered]@{
            status     = 'acknowledged'
            taskId     = $taskId
            requestId  = $requestId
            taskStatus = $cancelStatus
        })
        Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'allowed' -RuntimeTaskId $taskId -Detail ('cancel: ' + $cancelStatus)
        Write-Output $r; exit 0
    }

    # ------------------------------------------------------------------
    'get_health' {
        $rtResult = Invoke-RuntimeScript -ScriptName 'oc-task-health.ps1'

        if ($rtResult.TimedOut) {
            $r = New-BridgeResponse -Fields ([ordered]@{
                status    = 'error'
                errorCode = 'RUNTIME_UNAVAILABLE'
                errorMessage = 'Runtime health check timed out.'
                requestId = $requestId
            })
            Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'error' -ErrorCode 'RUNTIME_UNAVAILABLE' -Detail 'Health timeout'
            Write-Output $r; exit 1
        }

        $rtResp = $null
        try { $rtResp = $rtResult.Stdout | ConvertFrom-Json } catch { }

        $healthLevel = 'error'
        if ($null -ne $rtResp -and $null -ne $rtResp.PSObject.Properties['status']) {
            $healthLevel = [string]$rtResp.status
        }

        $r = New-BridgeResponse -Fields ([ordered]@{
            status    = 'ok'
            health    = $healthLevel
            requestId = $requestId
        })
        Write-BridgeAudit -RequestId $requestId -Source $source -SourceUserId $sourceUserId -Operation $operation -Outcome 'allowed' -Detail ('health: ' + $healthLevel)
        Write-Output $r; exit 0
    }
}
