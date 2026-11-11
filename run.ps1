$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$forwardArgs = @($args)
if ($forwardArgs.Count -eq 0) {
    & (Join-Path $Root "run-overlay.ps1")
    exit 0
}

$env:PYTHONPATH = $Root
python (Join-Path $Root "plugin.py") @forwardArgs
