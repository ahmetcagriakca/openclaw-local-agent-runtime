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

$result = [ordered]@{
    version     = [int]$manifest.version
    actionsRoot = [string]$manifest.actionsRoot
    actions     = @(
        foreach ($action in @($manifest.actions)) {
            [ordered]@{
                name             = [string]$action.name
                description      = [string]$action.description
                enabled          = [bool]$action.enabled
                approvalRequired = [bool]$action.approvalRequired
                riskLevel        = [string]$action.riskLevel
                timeoutSec       = [int]$action.timeoutSec
                scriptPath       = [string]$action.scriptPath
                parameters       = @(
                    foreach ($param in @($action.parameters)) {
                        [ordered]@{
                            name        = [string]$param.name
                            type        = [string]$param.type
                            required    = [bool]$param.required
                            description = [string]$param.description
                        }
                    }
                )
            }
        }
    )
}

$result | ConvertTo-Json -Depth 10