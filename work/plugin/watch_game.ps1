$ErrorActionPreference = "SilentlyContinue"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$adb = "D:\TapTap\Support\android_emulator\engine\nx_device\12.0\shell\adb.exe"
$device = "127.0.0.1:16416"
$uiScript = Join-Path $PSScriptRoot "floating_ui.ps1"
$monitorScript = Join-Path $PSScriptRoot "monitor_game.ps1"

$mutex = New-Object System.Threading.Mutex($false, "Global\PW3D-Watcher")
if (-not $mutex.WaitOne(0)) {
    exit
}

function Get-GamePid {
    try {
        & $adb connect $device 2>$null | Out-Null
        $devices = (& $adb devices 2>$null) -join "`n"
        if ($devices -notmatch [regex]::Escape($device)) {
            return $null
        }
        $text = (& $adb -s $device shell "pidof com.puzzle.miniworld.cn" 2>$null) -join ""
        if ($text -match "(\d+)") {
            return $matches[1]
        }
    } catch {
    }
    return $null
}

function Find-UI {
    return Get-Process powershell -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -eq "拼模型助手" } |
        Select-Object -First 1
}

function Start-UI {
    if (Find-UI) {
        return
    }
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", $uiScript) `
        -WorkingDirectory $root -WindowStyle Hidden | Out-Null
}

function Start-Monitor {
    Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", $monitorScript) `
        -WorkingDirectory $root -WindowStyle Hidden | Out-Null
}

Start-Monitor

$lastPid = $null
while ($true) {
    $gamePid = Get-GamePid
    if ($gamePid) {
        if ($gamePid -ne $lastPid) {
            $lastPid = $gamePid
            Start-UI
            Start-Monitor
        }
    } else {
        $lastPid = $null
    }
    Start-Sleep -Seconds 2
}
