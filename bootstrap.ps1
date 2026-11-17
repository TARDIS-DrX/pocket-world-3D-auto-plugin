$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginDir = Join-Path $Root "work\plugin"
$Bundle = Join-Path $Root "work\frida-agent\bundle.js"
$Adb = "D:\TapTap\Support\android_emulator\engine\nx_device\12.0\shell\adb.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found in PATH."
}

$frida = python -c "import frida, sys; print(frida.__version__)" 2>$null
if (-not $frida) {
    throw "Python package 'frida' was not found. Run: pip install -r work\plugin\requirements.txt"
}
Write-Host "frida: $frida"

if (-not (Test-Path -LiteralPath $Adb)) {
    throw "ADB was not found: $Adb"
}
Write-Host "adb: $Adb"

if (-not (Test-Path -LiteralPath $Bundle)) {
    throw "Frida bridge was not found: $Bundle"
}
Write-Host "bridge: $Bundle"

$device = & $Adb devices 2>$null
if ($device -notmatch "127\.0\.0\.1:16416") {
    Write-Host "Warning: device 127.0.0.1:16416 is not connected."
} else {
    Write-Host "device: 127.0.0.1:16416"
}

Write-Host "Bootstrap check complete."
