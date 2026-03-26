<#
.SYNOPSIS
    Register (or update) the VezirWslGuardian scheduled task.
    Replaces the legacy WSLKeepAlive task.

.NOTES
    Run once from an elevated (admin) PowerShell prompt.
    Idempotent: re-running updates the existing task.
    Location: C:\Users\AKCA\oc\bin\register-wsl-guardian-task.ps1
#>

param(
    [string]$TaskName   = "VezirWslGuardian",
    [string]$ScriptPath = "$env:USERPROFILE\oc\bin\oc-wsl-guardian.ps1"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Guardian script not found: $ScriptPath"
    exit 1
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument @"
-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$ScriptPath"
"@

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($existing) {
    Write-Host "[wsl-guardian-task] Updating existing task: $TaskName"
    Set-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal | Out-Null
} else {
    Write-Host "[wsl-guardian-task] Registering new task: $TaskName"
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal | Out-Null
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Write-Host "[wsl-guardian-task] Registered:"
Write-Host "  Name:      $($task.TaskName)"
Write-Host "  State:     $($task.State)"
Write-Host "  Trigger:   AtLogOn ($env:USERNAME)"
Write-Host "  TimeLimit: Unlimited (runs indefinitely)"
Write-Host "  Restart:   3 retries, 1 min interval"

# Remove legacy WSLKeepAlive task if it exists
$oldTask = Get-ScheduledTask -TaskName 'WSLKeepAlive' -ErrorAction SilentlyContinue
if ($oldTask) {
    Unregister-ScheduledTask -TaskName 'WSLKeepAlive' -Confirm:$false
    Write-Host "[wsl-guardian-task] Removed legacy WSLKeepAlive task."
}

Write-Host ""
Write-Host "[wsl-guardian-task] To start now:  pwsh -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
