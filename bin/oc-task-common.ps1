Set-StrictMode -Version Latest

$script:OcBinPath = Split-Path -Parent $PSCommandPath
if ([string]::IsNullOrWhiteSpace($script:OcBinPath)) {
    $script:OcBinPath = Join-Path $env:USERPROFILE 'oc\bin'
}
$script:OcRuntimeRoot = Split-Path -Parent $script:OcBinPath
$script:OcBasePath = Split-Path -Parent $script:OcRuntimeRoot

function Get-OcRuntimeConfig {
    return [ordered]@{
        BasePath = $script:OcBasePath
        RuntimeRoot = $script:OcRuntimeRoot
        BinPath = $script:OcBinPath
        ActionsPath = Join-Path $script:OcRuntimeRoot 'actions'
        TaskDefsPath = Join-Path $script:OcRuntimeRoot 'defs\tasks'
        QueuePendingPath = Join-Path $script:OcRuntimeRoot 'queue\pending'
        QueueLeasesPath = Join-Path $script:OcRuntimeRoot 'queue\leases'
        QueueDeadLetterPath = Join-Path $script:OcRuntimeRoot 'queue\dead-letter'
        TasksPath = Join-Path $script:OcRuntimeRoot 'tasks'
        LogsPath = Join-Path $script:OcRuntimeRoot 'logs'
        ResultsPath = Join-Path $script:OcRuntimeRoot 'results'
        ActionRunnerPath = Join-Path $script:OcBinPath 'oc-run-action.ps1'
        RunFilePath = Join-Path $script:OcBinPath 'oc-run-file.ps1'
        WmcpCallPath = Join-Path $script:OcBinPath 'wmcp-call.ps1'
        ManifestPath = Join-Path $script:OcRuntimeRoot 'actions\manifest.json'
        WorkerScriptPath = Join-Path $script:OcBinPath 'oc-task-worker.ps1'
        RunnerScriptPath = Join-Path $script:OcBinPath 'oc-task-runner.ps1'
        WatchdogScriptPath = Join-Path $script:OcBinPath 'oc-runtime-watchdog.ps1'
        PreflightScriptPath = Join-Path $script:OcBinPath 'oc-runtime-startup-preflight.ps1'
        RebootValidatePath = Join-Path $script:OcBinPath 'oc-reboot-validate.ps1'
        SchedulerTaskName = 'OpenClawTaskWorker'
        WatchdogTaskName = 'OpenClawRuntimeWatchdog'
        PreflightTaskName = 'OpenClawStartupPreflight'
        WorkerMutexName = 'Global\OpenClawTaskWorker'
        StuckWarningMinutes = 30
        StuckRecoveryMinutes = 60
        StaleLeaseMinutes = 30
    }
}

function Initialize-OcRuntimeLayout {
    $config = Get-OcRuntimeConfig
    $dirs = @(
        $config.RuntimeRoot,
        $config.BinPath,
        $config.ActionsPath,
        $config.ResultsPath,
        $config.TaskDefsPath,
        $config.QueuePendingPath,
        $config.QueueLeasesPath,
        $config.QueueDeadLetterPath,
        $config.TasksPath,
        $config.LogsPath
    )

    foreach ($dir in $dirs) {
        Ensure-OcDirectory -Path $dir
    }

    return $config
}

function Ensure-OcDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-OcUtf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}

function Append-OcUtf8NoBomLine {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Line
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    [System.IO.File]::AppendAllText($Path, $Line + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

function Read-OcJson {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw ('JSON file was not found: ' + $Path)
    }
    return (Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json)
}

function Save-OcJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Object
    )

    $json = $Object | ConvertTo-Json -Depth 20
    Write-OcUtf8NoBom -Path $Path -Content $json
}

function Get-OcPropertyValue {
    param(
        [Parameter(Mandatory = $true)][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }

    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) {
            return $Object[$Name]
        }
        return $null
    }

    $prop = $Object.PSObject.Properties[$Name]
    if ($null -ne $prop) {
        return $prop.Value
    }

    return $null
}

function Get-OcNestedValue {
    param(
        [Parameter(Mandatory = $true)][object]$Root,
        [Parameter(Mandatory = $true)][string[]]$Segments
    )

    $current = $Root
    foreach ($segment in $Segments) {
        $current = Get-OcPropertyValue -Object $current -Name $segment
        if ($null -eq $current) {
            return $null
        }
    }

    return $current
}

function Resolve-OcReferenceToken {
    param(
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][object]$TaskObject,
        [Parameter(Mandatory = $true)][object]$RuntimeConfig
    )

    if ($Token -eq 'nowUtc') {
        return [DateTime]::UtcNow.ToString('o')
    }

    $parts = $Token.Split('.')
    if ($parts.Count -eq 0) {
        return $null
    }

    $head = $parts[0]
    $tail = @()
    if ($parts.Count -gt 1) {
        $tail = $parts[1..($parts.Count - 1)]
    }

    switch ($head) {
        'input' {
            return Get-OcNestedValue -Root (Get-OcPropertyValue -Object $TaskObject -Name 'input') -Segments $tail
        }
        'task' {
            return Get-OcNestedValue -Root $TaskObject -Segments $tail
        }
        'paths' {
            $pathsObject = [ordered]@{
                base = $RuntimeConfig.BasePath
                runtimeRoot = $RuntimeConfig.RuntimeRoot
                tasks = $RuntimeConfig.TasksPath
                ocResults = $RuntimeConfig.ResultsPath
                pending = $RuntimeConfig.QueuePendingPath
                leases = $RuntimeConfig.QueueLeasesPath
                logs = $RuntimeConfig.LogsPath
            }
            return Get-OcNestedValue -Root $pathsObject -Segments $tail
        }
        default {
            return $null
        }
    }
}

function Resolve-OcTemplateValue {
    param(
        [Parameter(Mandatory = $true)][object]$Value,
        [Parameter(Mandatory = $true)][object]$TaskObject,
        [Parameter(Mandatory = $true)][object]$RuntimeConfig
    )

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [string]) {
        if ($Value -eq '$nowUtc') {
            return [DateTime]::UtcNow.ToString('o')
        }

        if ($Value -match '^\$(input|task|paths)\.[A-Za-z0-9_.-]+$') {
            return Resolve-OcReferenceToken -Token $Value.Substring(1) -TaskObject $TaskObject -RuntimeConfig $RuntimeConfig
        }

        if ($Value.Contains('${')) {
            return ([System.Text.RegularExpressions.Regex]::Replace($Value, '\$\{([^}]+)\}', {
                param($match)
                $resolved = Resolve-OcReferenceToken -Token $match.Groups[1].Value -TaskObject $TaskObject -RuntimeConfig $RuntimeConfig
                if ($null -eq $resolved) {
                    return ''
                }
                return [string]$resolved
            }))
        }

        return $Value
    }

    if ($Value -is [System.Array]) {
        $items = New-Object System.Collections.ArrayList
        foreach ($item in $Value) {
            [void]$items.Add((Resolve-OcTemplateValue -Value $item -TaskObject $TaskObject -RuntimeConfig $RuntimeConfig))
        }
        return @($items)
    }

    if ($Value -is [System.Collections.IDictionary]) {
        $map = [ordered]@{}
        foreach ($key in $Value.Keys) {
            $map[$key] = Resolve-OcTemplateValue -Value $Value[$key] -TaskObject $TaskObject -RuntimeConfig $RuntimeConfig
        }
        return $map
    }

    if ($null -ne $Value.PSObject -and @($Value.PSObject.Properties).Count -gt 0) {
        $map = [ordered]@{}
        foreach ($prop in $Value.PSObject.Properties) {
            $map[$prop.Name] = Resolve-OcTemplateValue -Value $prop.Value -TaskObject $TaskObject -RuntimeConfig $RuntimeConfig
        }
        return $map
    }

    return $Value
}

function New-OcTaskId {
    return ('task-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfff') + '-' + (Get-Random -Minimum 1000 -Maximum 9999))
}

function Get-OcTaskPaths {
    param(
        [Parameter(Mandatory = $true)][string]$TaskId,
        [Parameter(Mandatory = $true)][object]$RuntimeConfig
    )

    $taskDir = Join-Path $RuntimeConfig.TasksPath $TaskId
    return [ordered]@{
        TaskDir = $taskDir
        TaskJsonPath = Join-Path $taskDir 'task.json'
        EventsPath = Join-Path $taskDir 'events.jsonl'
        ArtifactsDir = Join-Path $taskDir 'artifacts'
    }
}

function Append-OcTaskEvent {
    param(
        [Parameter(Mandatory = $true)][string]$EventsPath,
        [Parameter(Mandatory = $true)][string]$EventName,
        [Parameter(Mandatory = $true)][string]$TaskId,
        [hashtable]$Data
    )

    $event = [ordered]@{
        ts = [DateTime]::UtcNow.ToString('o')
        event = $EventName
        taskId = $TaskId
    }

    if ($null -ne $Data) {
        foreach ($key in $Data.Keys) {
            $event[$key] = $Data[$key]
        }
    }

    Append-OcUtf8NoBomLine -Path $EventsPath -Line ($event | ConvertTo-Json -Compress -Depth 20)
}

function Write-OcRuntimeLog {
    param(
        [Parameter(Mandatory = $true)][string]$LogName,
        [Parameter(Mandatory = $true)][string]$Level,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $config = Get-OcRuntimeConfig
    $logPath = Join-Path $config.LogsPath $LogName
    $entry = [ordered]@{
        ts = [DateTime]::UtcNow.ToString('o')
        level = $Level
        message = $Message
    }
    Append-OcUtf8NoBomLine -Path $logPath -Line ($entry | ConvertTo-Json -Compress -Depth 10)
}

function Get-OcSingleLinePreview {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ''
    }

    $single = ($Text -replace '[\r\n]+', ' ').Trim()
    if ($single.Length -gt 300) {
        return $single.Substring(0, 300)
    }
    return $single
}

function ConvertTo-OcUtcDateTime {
    param([Parameter(Mandatory = $true)][string]$IsoString)
    return [DateTime]::Parse($IsoString).ToUniversalTime()
}

function Get-OcUtcAgeMinutes {
    param([Parameter(Mandatory = $true)][string]$IsoString)
    return ([DateTime]::UtcNow - [DateTime]::Parse($IsoString).ToUniversalTime()).TotalMinutes
}

function New-OcRejection {
    param(
        [Parameter(Mandatory = $true)][string]$ReasonCode,
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$TaskName = '',
        [string]$Source = '',
        [string]$TaskId = ''
    )
    $envelope = [ordered]@{
        status     = 'rejected'
        reasonCode = $ReasonCode
        message    = $Message
    }
    if (-not [string]::IsNullOrWhiteSpace($TaskName)) { $envelope['taskName'] = $TaskName }
    if (-not [string]::IsNullOrWhiteSpace($TaskId))   { $envelope['taskId'] = $TaskId }
    if (-not [string]::IsNullOrWhiteSpace($Source))    { $envelope['source'] = $Source }
    return $envelope
}

function Write-OcRejectionAndExit {
    param(
        [Parameter(Mandatory = $true)][string]$ReasonCode,
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$TaskName = '',
        [string]$Source = '',
        [string]$TaskId = '',
        [string]$LogName = 'control-plane.log'
    )
    $envelope = New-OcRejection -ReasonCode $ReasonCode -Message $Message -TaskName $TaskName -Source $Source -TaskId $TaskId
    Write-OcRuntimeLog -LogName $LogName -Level 'warn' -Message ('[rejection] ' + $ReasonCode + ': ' + $Message)
    $envelope | ConvertTo-Json -Depth 10
    exit 1
}

function Assert-OcTaskId {
    param([Parameter(Mandatory = $true)][string]$TaskId)
    if ($TaskId -notmatch '^task-[0-9]{8}-[0-9]{9}-[0-9]{4}$') {
        throw ('Invalid TaskId format: ' + $TaskId)
    }
}

function Assert-OcTaskName {
    param([Parameter(Mandatory = $true)][string]$TaskName)
    if ([string]::IsNullOrWhiteSpace($TaskName)) {
        throw 'TaskName cannot be empty.'
    }
    if ($TaskName -notmatch '^[A-Za-z0-9_-]+$') {
        throw 'TaskName contains invalid characters.'
    }
    if ($TaskName.Length -gt 128) {
        throw 'TaskName exceeds maximum length of 128 characters.'
    }
}

function Test-OcWorkerActive {
    param([Parameter(Mandatory = $true)][string]$MutexName)
    $testMutex = $null
    try {
        $testMutex = [System.Threading.Mutex]::OpenExisting($MutexName)
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $testMutex) { $testMutex.Dispose() }
    }
}

function Invoke-OcWorkerKick {
    param(
        [Parameter(Mandatory = $true)][object]$RuntimeConfig,
        [string]$Source = 'unknown'
    )

    if (-not (Test-Path -LiteralPath $RuntimeConfig.WorkerScriptPath)) {
        throw 'Worker script was not found.'
    }

    if (Test-OcWorkerActive -MutexName $RuntimeConfig.WorkerMutexName) {
        return
    }

    # Execution-context check: detect whether an interactive desktop is available.
    # GUI-requiring tasks (e.g. open-app launch_wait_exit) will fail silently
    # if the worker is kicked from a non-interactive context (watchdog, SYSTEM).
    $hasInteractiveSession = $false
    try {
        $explorer = Get-Process -Name 'explorer' -ErrorAction SilentlyContinue
        $hasInteractiveSession = ($null -ne $explorer -and @($explorer).Count -gt 0)
    }
    catch { }

    if (-not $hasInteractiveSession) {
        Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message (
            '[worker-kick] No interactive desktop detected. Source: ' + $Source +
            '. GUI-requiring tasks may fail in this context.'
        )
    }

    Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'info' -Message (
        '[worker-kick] Kicking worker. Source: ' + $Source +
        ' InteractiveSession: ' + $hasInteractiveSession
    )

    Start-Process -WindowStyle Hidden -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-WindowStyle', 'Hidden',
        '-File', $RuntimeConfig.WorkerScriptPath,
        '-RunOnce'
    ) | Out-Null
}

function Invoke-OcLogRotate {
    param(
        [Parameter(Mandatory = $true)][string]$LogPath,
        [int]$MaxSizeBytes = 5242880,
        [int]$KeepCount = 3
    )

    if (-not (Test-Path -LiteralPath $LogPath)) { return }
    $fileInfo = Get-Item -LiteralPath $LogPath
    if ($fileInfo.Length -lt $MaxSizeBytes) { return }

    for ($i = $KeepCount; $i -ge 1; $i--) {
        $older = $LogPath + '.' + $i
        $newer = if ($i -eq 1) { $LogPath } else { $LogPath + '.' + ($i - 1) }
        if (Test-Path -LiteralPath $newer) {
            if ($i -eq $KeepCount -and (Test-Path -LiteralPath $older)) {
                Remove-Item -LiteralPath $older -Force
            }
            if ($i -gt 1 -or $true) {
                Move-Item -LiteralPath $newer -Destination $older -Force
            }
        }
    }
}

function Decode-OcBase64Json {
    param([Parameter(Mandatory = $true)][string]$Base64String)
    $bytes = [Convert]::FromBase64String($Base64String)
    $json = [Text.Encoding]::UTF8.GetString($bytes)
    return ($json | ConvertFrom-Json)
}

function Encode-OcJsonToBase64 {
    param([Parameter(Mandatory = $true)][string]$JsonString)
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($JsonString))
}