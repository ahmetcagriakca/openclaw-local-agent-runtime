$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout
$maxSize = 5242880
$keepCount = 3

$logFiles = @(
    (Join-Path $config.LogsPath 'control-plane.log'),
    (Join-Path $config.LogsPath 'worker.log')
)

foreach ($logFile in $logFiles) {
    Invoke-OcLogRotate -LogPath $logFile -MaxSizeBytes $maxSize -KeepCount $keepCount
}

Write-Output 'OK: Log rotation completed.'
exit 0