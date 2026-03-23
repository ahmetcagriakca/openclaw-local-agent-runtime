param(
    [Parameter(Mandatory=$true)]
    [string]$App,

    [string]$ExecutionMode = 'launch_return'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$App = $App.Trim().ToLowerInvariant()
$ExecutionMode = $ExecutionMode.Trim().ToLowerInvariant()

if ([string]::IsNullOrWhiteSpace($App)) {
    throw "App value is empty."
}

if ($ExecutionMode -ne 'launch_return' -and $ExecutionMode -ne 'launch_wait_exit') {
    throw "Invalid executionMode: $ExecutionMode. Must be launch_return or launch_wait_exit."
}

$allowedApps = @{
    "notepad"  = "C:\Windows\System32\notepad.exe"
    "calc"     = "C:\Windows\System32\calc.exe"
    "mspaint"  = "C:\Windows\System32\mspaint.exe"
    "explorer" = "C:\Windows\explorer.exe"
}

if (-not $allowedApps.ContainsKey($App)) {
    throw "App not allowed: $App"
}

$target = $allowedApps[$App]

if (-not (Test-Path -LiteralPath $target)) {
    throw "Target executable not found: $target"
}

if ($ExecutionMode -eq 'launch_wait_exit') {
    $proc = Start-Process -FilePath $target -PassThru
    Write-Output "LAUNCHED:$App PID:$($proc.Id) MODE:launch_wait_exit"
    $proc.WaitForExit()
    $exitCode = $proc.ExitCode
    Write-Output "EXITED:$App PID:$($proc.Id) EXIT_CODE:$exitCode"
    exit $exitCode
}

Start-Process -FilePath $target | Out-Null
Write-Output "OK:$App MODE:launch_return"
exit 0