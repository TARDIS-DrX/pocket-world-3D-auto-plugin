$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Dumper = Join-Path $Root "tools\il2cppdumper\Il2CppDumper.exe"
$SevenZip = "D:\TapTap\Support\android_emulator\engine\tools\7z1602\x64\7za.exe"

if (-not (Test-Path -LiteralPath $Dumper)) {
    throw "Il2CppDumper was not found: $Dumper"
}
if (-not (Test-Path -LiteralPath $SevenZip)) {
    throw "7za.exe was not found: $SevenZip"
}

$Runtimes = dotnet --list-runtimes 2>$null
if ($Runtimes -notmatch "Microsoft\.NETCore\.App 6\.") {
    throw ".NET 6 runtime was not found."
}

python (Join-Path $Root "plugin.py") detect
Write-Host "Bootstrap check complete."
