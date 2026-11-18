$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Version = "0.3.0"
$Dist = Join-Path $Root "dist"
$Stage = Join-Path $env:TEMP ("pw3d-release-" + [guid]::NewGuid().ToString("N"))

$RootFiles = @(
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
    "run.ps1",
    "run-overlay.ps1",
    "bootstrap.ps1",
    "enable-root-mode.ps1",
    "disable-root-mode.ps1",
    "open_emulator.py"
)

$PluginFiles = @(
    "libpw3dmod.so",
    "pw3d_plugin.py",
    "floating_ui.ps1",
    "watch_game.ps1",
    "monitor_game.ps1",
    "monitor_game.bat",
    "install_autostart.ps1",
    "uninstall_autostart.ps1",
    "install_autostart.bat",
    "uninstall_autostart.bat",
    "run.bat",
    "run_ui.bat",
    "watch_game.bat",
    "requirements.txt",
    "README.md",
    "pw3dmod.c",
    "build.ps1"
)

New-Item -ItemType Directory -Force -Path $Stage, (Join-Path $Stage "work\plugin"), (Join-Path $Stage "work\frida-agent"), (Join-Path $Stage "work\tools"), $Dist | Out-Null

foreach ($name in $RootFiles) {
    $source = Join-Path $Root $name
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing release file: $source"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $Stage $name) -Force
}

foreach ($name in $PluginFiles) {
    $source = Join-Path $Root "work\plugin\$name"
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing plugin file: $source"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $Stage "work\plugin\$name") -Force
}

$bundle = Join-Path $Root "work\frida-agent\bundle.js"
if (-not (Test-Path -LiteralPath $bundle)) {
    throw "Missing Frida bridge: $bundle"
}
Copy-Item -LiteralPath $bundle -Destination (Join-Path $Stage "work\frida-agent\bundle.js") -Force

foreach ($name in @("libc_arm64.so", "libdl_arm64.so")) {
    $source = Join-Path $Root "work\tools\$name"
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing build stub: $source"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $Stage "work\tools\$name") -Force
}

$versioned = Join-Path $Dist "pocket-world-quick-assembly-$Version.zip"
$latest = Join-Path $Dist "pocket-world-quick-assembly-github.zip"
Remove-Item -LiteralPath $versioned, $latest -Force -ErrorAction SilentlyContinue

Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $versioned -CompressionLevel Optimal
Copy-Item -LiteralPath $versioned -Destination $latest -Force
Remove-Item -LiteralPath $Stage -Recurse -Force

Get-Item -LiteralPath $versioned, $latest | Select-Object FullName, Length
