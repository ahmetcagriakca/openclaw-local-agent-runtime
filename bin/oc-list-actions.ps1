Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')
$ocConfig = Get-OcRuntimeConfig

$manifestPath = $ocConfig.ManifestPath

if (-not (Test-Path $manifestPath)) {
    throw "Manifest not found: $manifestPath"
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

if ($null -eq $manifest.actions -or @($manifest.actions).Count -eq 0) {
    throw "No actions defined in manifest."
}

$result = foreach ($action in @($manifest.actions)) {
    $paramNames = ''
    $requiredNames = ''

    if ($null -ne $action.parameters -and @($action.parameters).Count -gt 0) {
        $paramNames = (@($action.parameters) | ForEach-Object { [string]$_.name }) -join ','
        $requiredNames = (@($action.parameters) | Where-Object { $_.required -eq $true } | ForEach-Object { [string]$_.name }) -join ','
    }

    [pscustomobject]@{
        Name             = [string]$action.name
        Enabled          = [bool]$action.enabled
        ApprovalRequired = [bool]$action.approvalRequired
        RiskLevel        = [string]$action.riskLevel
        TimeoutSec       = [int]$action.timeoutSec
        Parameters       = $paramNames
        RequiredParams   = $requiredNames
        ScriptPath       = [string]$action.scriptPath
    }
}

$result | Sort-Object Name | Format-Table -AutoSize