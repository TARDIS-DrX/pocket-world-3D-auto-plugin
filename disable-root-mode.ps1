$ErrorActionPreference = "Stop"

$Manager = "D:\TapTap\Support\android_emulator\engine\nx_main\MuMuManager.exe"
$VmIndex = "1"

if (-not (Test-Path -LiteralPath $Manager)) {
    throw "MuMuManager.exe was not found: $Manager"
}

& $Manager control --vmindex $VmIndex shutdown | Out-Null
Start-Sleep -Seconds 4
& $Manager setting --vmindex $VmIndex --key root_permission --value false
Write-Host "Root mode disabled. Start TapTap normally to use the emulator."
