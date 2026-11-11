$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Compiler = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$Source = Join-Path $Root "overlay.cs"
$Executable = Join-Path $Root "PocketWorldOverlay.exe"

if (-not (Test-Path -LiteralPath $Compiler)) {
    throw "C# compiler was not found: $Compiler"
}

if (
    -not (Test-Path -LiteralPath $Executable) -or
    (Get-Item -LiteralPath $Source).LastWriteTime -gt (Get-Item -LiteralPath $Executable).LastWriteTime
) {
    & $Compiler /nologo /target:winexe /optimize+ "/out:$Executable" `
        /reference:System.Windows.Forms.dll `
        /reference:System.Drawing.dll `
        $Source
    if ($LASTEXITCODE -ne 0) {
        throw "Overlay compilation failed."
    }
}

Start-Process -FilePath $Executable
