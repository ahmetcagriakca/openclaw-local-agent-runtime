param(
    [string]$Status,
    [int]$Limit = 20
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout
if ($Limit -lt 1) { $Limit = 1 }
if ($Limit -gt 200) { $Limit = 200 }

$taskDirs = @()
if (Test-Path -LiteralPath $config.TasksPath) {
    $taskDirs = @(Get-ChildItem -LiteralPath $config.TasksPath -Directory | Sort-Object LastWriteTimeUtc -Descending)
}

$items = New-Object System.Collections.ArrayList
foreach ($taskDir in $taskDirs) {
    $taskJsonPath = Join-Path $taskDir.FullName 'task.json'
    if (-not (Test-Path -LiteralPath $taskJsonPath)) {
        continue
    }

    try {
        $task = Read-OcJson -Path $taskJsonPath
    }
    catch {
        continue
    }

    if (-not [string]::IsNullOrWhiteSpace($Status)) {
        if ([string](Get-OcPropertyValue -Object $task -Name 'status') -ne $Status) {
            continue
        }
    }

    $item = [ordered]@{
        taskId = [string](Get-OcPropertyValue -Object $task -Name 'taskId')
        taskName = [string](Get-OcPropertyValue -Object $task -Name 'taskName')
        status = [string](Get-OcPropertyValue -Object $task -Name 'status')
        createdUtc = [string](Get-OcPropertyValue -Object $task -Name 'createdUtc')
        startedUtc = [string](Get-OcPropertyValue -Object $task -Name 'startedUtc')
        finishedUtc = [string](Get-OcPropertyValue -Object $task -Name 'finishedUtc')
        currentStepIndex = [int](Get-OcPropertyValue -Object $task -Name 'currentStepIndex')
        lastError = [string](Get-OcPropertyValue -Object $task -Name 'lastError')
    }
    [void]$items.Add([pscustomobject]$item)

    if ($items.Count -ge $Limit) {
        break
    }
}

$result = [ordered]@{
    count = $items.Count
    items = @($items)
}

$result | ConvertTo-Json -Depth 20
exit 0