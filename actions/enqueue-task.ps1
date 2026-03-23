param(
    [Parameter(Mandatory = $true)][string]$taskName,
    [string]$inputJson = '{}',
    [int]$priority = 0
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'bin\oc-task-enqueue.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task enqueue script was not found.'
}

$inputB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($inputJson))
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -TaskName $taskName -InputBase64 $inputB64 -Priority $priority
exit $LASTEXITCODE