<#
.SYNOPSIS
    Register (or update) a Windows Scheduled Task that starts the
    Vezir dashboard server at user logon.

.NOTES
    Run once from an elevated (admin) PowerShell prompt.
    Idempotent: re-running updates the existing task.
    Location: C:\Users\AKCA\oc\bin\register-dashboard-task.ps1
#>

param(
    [string]$TaskName   = "VezirDashboard",
    [string]$ScriptPath = "$env:USERPROFILE\oc\bin\start-dashboard.ps1"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Dashboard script not found: $ScriptPath"
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
    Write-Host "[dashboard-task] Updating existing task: $TaskName"
    Set-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal | Out-Null
} else {
    Write-Host "[dashboard-task] Registering new task: $TaskName"
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal | Out-Null
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Write-Host "[dashboard-task] Registered:"
Write-Host "  Name:      $($task.TaskName)"
Write-Host "  State:     $($task.State)"
Write-Host "  Trigger:   AtLogOn ($env:USERNAME)"
Write-Host "  TimeLimit: Unlimited (server runs indefinitely)"
Write-Host "  Restart:   3 retries, 1 min interval"
Write-Host ""
Write-Host "[dashboard-task] To start now:  pwsh -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
