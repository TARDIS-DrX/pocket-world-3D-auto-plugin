$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Overlay = Join-Path $Root "work\plugin\floating_ui.ps1"

Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", $Overlay) `
    -WorkingDirectory $Root -WindowStyle Hidden | Out-Null
