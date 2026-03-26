<#
.SYNOPSIS
    Register (or update) a Windows Scheduled Task that starts the windows-mcp
    server at user logon. Server runs in-process (no child window).

.NOTES
    Run once from an elevated (admin) PowerShell prompt.
    Idempotent: re-running updates the existing task.
    Location: C:\Users\AKCA\oc\bin\register-wmcp-task.ps1
#>

param(
    [string]$TaskName   = "VezirWmcpServer",
    [string]$ScriptPath = "$env:USERPROFILE\oc\bin\start-wmcp-server.ps1"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Startup script not found: $ScriptPath"
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
    Write-Host "[wmcp-task] Updating existing task: $TaskName"
    Set-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal | Out-Null
} else {
    Write-Host "[wmcp-task] Registering new task: $TaskName"
    Register-ScheduledTask -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal | Out-Null
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Write-Host "[wmcp-task] Registered:"
Write-Host "  Name:      $($task.TaskName)"
Write-Host "  State:     $($task.State)"
Write-Host "  Trigger:   AtLogOn ($env:USERNAME)"
Write-Host "  TimeLimit: Unlimited (server runs indefinitely)"
Write-Host "  Restart:   3 retries, 1 min interval"
Write-Host ""
Write-Host "[wmcp-task] To start now:  pwsh -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
