Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')
$ocConfig = Get-OcRuntimeConfig

$manifestPath = $ocConfig.ManifestPath

if (-not (Test-Path $manifestPath)) {
    throw "Manifest not found: $manifestPath"
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

if (-not $manifest.actionsRoot) {
    throw "actionsRoot is missing."
}

$actionsRootFull = [System.IO.Path]::GetFullPath([string]$manifest.actionsRoot).TrimEnd('\')

if (-not (Test-Path $actionsRootFull)) {
    throw "actionsRoot not found: $actionsRootFull"
}

if ($null -eq $manifest.actions -or @($manifest.actions).Count -eq 0) {
    throw "No actions defined in manifest."
}

$names = @{}
foreach ($action in @($manifest.actions)) {
    if (-not $action.name) {
        throw "Action name is missing."
    }

    $name = [string]$action.name

    if ($names.ContainsKey($name)) {
        throw "Duplicate action name: $name"
    }
    $names[$name] = $true

    if (-not $action.scriptPath) {
        throw "scriptPath is missing for action: $name"
    }

    $scriptPathFull = [System.IO.Path]::GetFullPath([string]$action.scriptPath)

    if (-not ($scriptPathFull.StartsWith($actionsRootFull + '\', [System.StringComparison]::OrdinalIgnoreCase) -or $scriptPathFull.Equals($actionsRootFull, [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "Action script is outside actionsRoot: $name -> $scriptPathFull"
    }

    if (-not (Test-Path $scriptPathFull)) {
        throw "Action script not found: $name -> $scriptPathFull"
    }

    if ($null -ne $action.parameters) {
        $paramNames = @{}
        foreach ($param in @($action.parameters)) {
            if (-not $param.name) {
                throw "Parameter name missing in action: $name"
            }

            $paramName = [string]$param.name

            if ($paramNames.ContainsKey($paramName)) {
                throw "Duplicate parameter name in action $name : $paramName"
            }
            $paramNames[$paramName] = $true

            if ($paramName -notmatch '^[A-Za-z][A-Za-z0-9_]*$') {
                throw "Invalid parameter name in action $name : $paramName"
            }
        }
    }

    Write-Host "OK ACTION=$name SCRIPT=$scriptPathFull"
}

Write-Host "MANIFEST VALID"