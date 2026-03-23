$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'Stop'

$target = "$env:TEMP\oc-notepad-test.txt"
'OC_WMCP_NOTEPAD_OK' | Set-Content -Path $target -Encoding UTF8

Start-Process notepad $target | Out-Null

Write-Output 'OK'
exit 0
