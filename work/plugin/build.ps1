$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$env:ZIG_GLOBAL_CACHE_DIR = Join-Path $root "work\tools\zig-global"
$env:ZIG_LOCAL_CACHE_DIR = Join-Path $root "work\tools\zig-cache"
$zig = $env:ZIG
if (-not $zig) {
    $command = Get-Command zig -ErrorAction SilentlyContinue
    if ($command) {
        $zig = $command.Source
    }
}
if (-not $zig -or -not (Test-Path -LiteralPath $zig)) {
    throw "Zig was not found. Install Zig 0.13+ and add it to PATH, or set the ZIG environment variable."
}
$libc = Join-Path $root "work\tools\libc_arm64.so"
$libdl = Join-Path $root "work\tools\libdl_arm64.so"
$source = Join-Path $root "work\plugin\pw3dmod.c"
$output = Join-Path $root "work\plugin\libpw3dmod.so"

if (-not (Test-Path -LiteralPath $libc) -or -not (Test-Path -LiteralPath $libdl)) {
    throw "ARM64 bionic stub libraries are missing from work\tools."
}

& $zig cc -target aarch64-linux-android -shared -fPIC -nostdlib -o $output $source $libc $libdl "-Wl,--no-as-needed" "-Wl,-z,now"
Get-Item $output | Select-Object FullName,Length
