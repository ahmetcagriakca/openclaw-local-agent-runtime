param(
    [Parameter(Mandatory = $true)][string]$TaskId
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

Assert-OcTaskId -TaskId $TaskId
$config = Initialize-OcRuntimeLayout
$taskPaths = Get-OcTaskPaths -TaskId $TaskId -RuntimeConfig $config
if (-not (Test-Path -LiteralPath $taskPaths.TaskJsonPath)) {
    throw 'Task was not found.'
}

Get-Content -Raw -LiteralPath $taskPaths.TaskJsonPath
exit 0