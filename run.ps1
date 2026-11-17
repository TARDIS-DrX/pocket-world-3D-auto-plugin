$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Plugin = Join-Path $Root "work\plugin\pw3d_plugin.py"
$Overlay = Join-Path $Root "work\plugin\floating_ui.ps1"

if ($args.Count -gt 0) {
    python $Plugin @args
    exit $LASTEXITCODE
}

Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", $Overlay) `
    -WorkingDirectory $Root -WindowStyle Hidden | Out-Null
