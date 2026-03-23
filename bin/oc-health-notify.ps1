<#
.SYNOPSIS
    Compares current health snapshot with previous notification state,
    decides whether to send a Telegram notification, and updates state.

.NOTES
    Location: C:\Users\AKCA\oc\bin\oc-health-notify.ps1
    Exit code: always 0
#>

param(
    [Parameter(Mandatory)][ValidateSet('watchdog','startup')][string]$Mode
)

$ErrorActionPreference = 'Continue'
$scriptRoot = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $scriptRoot
$logsPath = Join-Path $repoRoot 'logs'
$snapshotPath = Join-Path $logsPath 'health-snapshot.json'
$notifyStatePath = Join-Path $logsPath 'notification-state.json'
$notifyScript = Join-Path $scriptRoot 'oc-telegram-notify.ps1'

# Emoji constants — constructed via ConvertFromUtf32 to avoid PowerShell BMP encoding errors
$Emoji = @{
    GreenCircle  = [char]::ConvertFromUtf32(0x1F7E2)
    YellowCircle = [char]::ConvertFromUtf32(0x1F7E1)
    RedCircle    = [char]::ConvertFromUtf32(0x1F534)
    Clipboard    = [char]::ConvertFromUtf32(0x1F4CB)
    CheckMark    = [char]::ConvertFromUtf32(0x2705)
    CrossMark    = [char]::ConvertFromUtf32(0x274C)
    Warning      = [char]::ConvertFromUtf32(0x26A0)
    SkipForward  = [char]::ConvertFromUtf32(0x23ED)
    Bullet       = [char]::ConvertFromUtf32(0x2022)
    EmDash       = [char]::ConvertFromUtf32(0x2014)
    VariantSel   = [char]0xFE0F
}

# --- Component labels and icons -----------------------------------------------
$componentLabels = [ordered]@{
    wmcp           = 'WMCP Server'
    wsl            = 'WSL Instance'
    openclaw       = 'OpenClaw Gateway'
    runtime        = 'oc Runtime'
    bridge         = 'Bridge'
    scheduledTasks = 'Scheduled Tasks'
}

function Get-StatusIcon([string]$s) {
    switch ($s) {
        'ok'       { return $Emoji.CheckMark }
        'degraded' { return $Emoji.Warning + $Emoji.VariantSel }
        'error'    { return $Emoji.CrossMark }
        'skipped'  { return $Emoji.SkipForward + $Emoji.VariantSel }
        default    { return '?' }
    }
}

function Get-OverallIcon([string]$s) {
    switch ($s) {
        'ok'       { return $Emoji.GreenCircle }
        'degraded' { return $Emoji.YellowCircle }
        'error'    { return $Emoji.RedCircle }
        default    { return $Emoji.RedCircle }
    }
}

function Send-Notification([string]$Text) {
    if (-not (Test-Path -LiteralPath $notifyScript)) { return }
    try {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File $notifyScript -Message $Text -ParseMode HTML 2>&1 | Out-Null
    } catch { }
}

function Build-ComponentLines($components, [bool]$issuesOnly = $false, [bool]$healthyOnly = $false) {
    $lines = @()
    foreach ($key in $componentLabels.Keys) {
        $comp = $components.$key
        if (-not $comp) { continue }
        $s = [string]$comp.status
        $d = [string]$comp.detail
        $icon = Get-StatusIcon $s
        $label = $componentLabels[$key]

        if ($issuesOnly -and ($s -eq 'ok')) { continue }
        if ($healthyOnly -and ($s -ne 'ok')) { continue }

        $lines += "$label`: $icon $($s.ToUpper()) $(if($d){$Emoji.EmDash + ' ' + $d})"
    }
    return $lines
}

try {
    # --- Read current health snapshot ------------------------------------------
    $snapshot = $null
    if (Test-Path -LiteralPath $snapshotPath) {
        $snapshot = Get-Content -Raw -LiteralPath $snapshotPath | ConvertFrom-Json
    }

    $currentOverall = 'error'
    $components = $null
    $timestamp = [DateTime]::UtcNow.ToString('yyyy-MM-dd HH:mm:ss')

    if ($snapshot) {
        $currentOverall = [string]$snapshot.overall
        $components = $snapshot.components
        if ($snapshot.timestamp) {
            try { $timestamp = ([DateTime]::Parse($snapshot.timestamp)).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') } catch { }
        }
    }

    # --- Read previous notification state --------------------------------------
    $prevState = $null
    if (Test-Path -LiteralPath $notifyStatePath) {
        try { $prevState = Get-Content -Raw -LiteralPath $notifyStatePath | ConvertFrom-Json } catch { }
    }

    $previousOverall = if ($prevState) { [string]$prevState.lastOverall } else { 'unknown' }
    $consecutiveAlertCount = if ($prevState -and $prevState.consecutiveAlertCount) { [int]$prevState.consecutiveAlertCount } else { 0 }

    # --- Build current component status map ------------------------------------
    $currentComponents = [ordered]@{}
    if ($components) {
        foreach ($key in $componentLabels.Keys) {
            $comp = $components.$key
            $currentComponents[$key] = if ($comp) { [string]$comp.status } else { 'unknown' }
        }
    }

    # --- Decision logic --------------------------------------------------------
    $notificationType = $null
    $messageText = $null

    if ($Mode -eq 'startup') {
        # Always send startup report
        $notificationType = 'startup'
        $overallIcon = Get-OverallIcon $currentOverall
        $allLines = Build-ComponentLines $components
        $body = @(
            "$($Emoji.Clipboard) <b>System Startup Report</b>"
            ""
            "Overall: $overallIcon $($currentOverall.ToUpper())"
            ""
        )
        $body += $allLines
        $body += @("", "Time: $timestamp UTC")
        $messageText = $body -join "`n"
        $consecutiveAlertCount = 0
    }
    elseif ($Mode -eq 'watchdog') {
        if ($previousOverall -eq 'ok' -and $currentOverall -eq 'ok') {
            # Case 1: all good, no notification
            $notificationType = 'none'
        }
        elseif ($previousOverall -eq 'ok' -and $currentOverall -ne 'ok') {
            # Case 2: new issue
            $notificationType = 'alert'
            $consecutiveAlertCount = 1
            $overallIcon = Get-OverallIcon $currentOverall
            $issueLines = Build-ComponentLines $components -issuesOnly $true
            $healthyLines = Build-ComponentLines $components -healthyOnly $true

            $body = @(
                "$($Emoji.RedCircle) <b>System Health Alert</b>"
                ""
                "Overall: $overallIcon $($currentOverall.ToUpper())"
                ""
                "Issues:"
            )
            foreach ($l in $issueLines) { $body += "$($Emoji.Bullet) $l" }
            $body += ""
            $body += "Healthy:"
            foreach ($l in $healthyLines) { $body += "$($Emoji.Bullet) $l" }
            $body += @("", "Time: $timestamp UTC")
            $messageText = $body -join "`n"
        }
        elseif ($previousOverall -ne 'ok' -and $previousOverall -ne 'unknown' -and $currentOverall -ne 'ok') {
            # Case 3: ongoing issue
            $notificationType = 'ongoing'
            $consecutiveAlertCount++
            $durationMinutes = $consecutiveAlertCount * 15
            $overallIcon = Get-OverallIcon $currentOverall
            $issueLines = Build-ComponentLines $components -issuesOnly $true

            $body = @(
                "$($Emoji.Warning)$($Emoji.VariantSel) <b>System Health $($Emoji.EmDash) Issue Persists</b> (alert #$consecutiveAlertCount)"
                ""
                "Overall: $overallIcon $($currentOverall.ToUpper())"
                ""
                "Issues:"
            )
            foreach ($l in $issueLines) { $body += "$($Emoji.Bullet) $l" }
            $body += @("", "Duration: ~$durationMinutes minutes ($consecutiveAlertCount consecutive alerts)")
            $body += @("", "Time: $timestamp UTC")
            $messageText = $body -join "`n"
        }
        elseif ($previousOverall -ne 'ok' -and $previousOverall -ne 'unknown' -and $currentOverall -eq 'ok') {
            # Case 4: recovery
            $notificationType = 'recovery'
            $durationMinutes = $consecutiveAlertCount * 15

            $body = @(
                "$($Emoji.GreenCircle) <b>System Health Recovered</b>"
                ""
                "Overall: $($Emoji.GreenCircle) OK $($Emoji.EmDash) All components healthy"
                ""
                "Previous issue duration: ~$durationMinutes minutes ($consecutiveAlertCount alerts)"
                ""
                "Time: $timestamp UTC"
            )
            $messageText = $body -join "`n"
            $consecutiveAlertCount = 0
        }
        else {
            # Unknown previous state, treat as first run
            $notificationType = 'none'
            if ($currentOverall -ne 'ok') {
                # First run with issues — send alert
                $notificationType = 'alert'
                $consecutiveAlertCount = 1
                $overallIcon = Get-OverallIcon $currentOverall
                $issueLines = Build-ComponentLines $components -issuesOnly $true
                $healthyLines = Build-ComponentLines $components -healthyOnly $true

                $body = @(
                    "$($Emoji.RedCircle) <b>System Health Alert</b>"
                    ""
                    "Overall: $overallIcon $($currentOverall.ToUpper())"
                    ""
                    "Issues:"
                )
                foreach ($l in $issueLines) { $body += "$($Emoji.Bullet) $l" }
                $body += ""
                $body += "Healthy:"
                foreach ($l in $healthyLines) { $body += "$($Emoji.Bullet) $l" }
                $body += @("", "Time: $timestamp UTC")
                $messageText = $body -join "`n"
            }
        }
    }

    # --- Send notification (if any) --------------------------------------------
    if ($messageText -and $notificationType -ne 'none') {
        Send-Notification -Text $messageText
    }

    # --- Update notification state ---------------------------------------------
    $newState = [ordered]@{
        lastOverall           = $currentOverall
        lastComponents        = $currentComponents
        lastNotificationUtc   = [DateTime]::UtcNow.ToString('o')
        lastNotificationType  = if ($notificationType) { $notificationType } else { 'none' }
        consecutiveAlertCount = $consecutiveAlertCount
    }
    $stateJson = $newState | ConvertTo-Json -Depth 10
    if (-not (Test-Path -LiteralPath $logsPath)) {
        New-Item -ItemType Directory -Path $logsPath -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($notifyStatePath, $stateJson, [System.Text.UTF8Encoding]::new($false))

} catch {
    Write-Warning "[health-notify] Unexpected error: $($_.Exception.Message)"
}

exit 0
