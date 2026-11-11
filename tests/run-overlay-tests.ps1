$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Compiler = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$Output = Join-Path $env:TEMP "pocket-world-overlay-selftest.exe"

& $Compiler /nologo /target:exe /optimize+ "/out:$Output" `
    /main:PocketWorldQuickAssemblyTests.Program `
    /reference:System.Windows.Forms.dll `
    /reference:System.Drawing.dll `
    (Join-Path $Root "overlay.cs") `
    (Join-Path $Root "tests\overlay_selftest.cs")
if ($LASTEXITCODE -ne 0) {
    throw "Overlay test compilation failed."
}

& $Output $Root
if ($LASTEXITCODE -ne 0) {
    throw "Overlay self-test failed with exit code $LASTEXITCODE."
}

Remove-Item -LiteralPath $Output -Force
Write-Host "Overlay self-test passed."
