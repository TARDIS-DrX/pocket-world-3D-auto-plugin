param(
    [switch]$TestPopup
)

$ErrorActionPreference = "SilentlyContinue"

$adb = if ($env:PW3D_ADB) { $env:PW3D_ADB } else { "D:\TapTap\Support\android_emulator\engine\nx_device\12.0\shell\adb.exe" }
$device = if ($env:PW3D_DEVICE) { $env:PW3D_DEVICE } else { "127.0.0.1:16416" }
$package = "com.puzzle.miniworld.cn"
$logDir = $PSScriptRoot
$logFile = Join-Path $logDir "monitor.log"

$mutex = New-Object System.Threading.Mutex($false, "Global\PW3D-Monitor")
if (-not $mutex.WaitOne(0)) {
    exit
}

$script:seen = @{}
$script:lastPid = $null
$script:lastResult = ""
$script:lastErrHash = ""
$script:lastUiWrite = [DateTime]::MinValue
$script:lastCrashHash = ""

function Write-Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    [System.IO.File]::AppendAllText($logFile, $line + "`r`n", (New-Object System.Text.UTF8Encoding($false)))
    Write-Host $line
}

function Show-Popup([string]$key, [string]$title, [string]$message, [int]$minutes = 5) {
    $now = Get-Date
    if ($script:seen.ContainsKey($key)) {
        if (($now - $script:seen[$key]).TotalMinutes -lt $minutes) {
            return
        }
    }
    $script:seen[$key] = $now
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($message, $title, "OK", "Warning") | Out-Null
}

function Invoke-Adb([string[]]$arguments) {
    return (& $adb -s $device @arguments 2>$null)
}

function Test-Device {
    try {
        $state = (Invoke-Adb @("get-state")) -join ""
        return $state -match "device"
    } catch {
        return $false
    }
}

function Get-GamePid {
    if (-not (Test-Device)) {
        return $null
    }
    $text = (Invoke-Adb @("shell", "pidof $package")) -join ""
    if ($text -match "(\d+)") {
        return $matches[1]
    }
    return $null
}

function Get-RemoteText([string]$path) {
    return ((Invoke-Adb @("shell", "su -c `"cat '$path' 2>/dev/null`"")) -join "").Trim()
}

function Get-CommandRunning {
    $busy = Join-Path $logDir "ui_run.busy"
    if (-not (Test-Path -LiteralPath $busy)) {
        return $false
    }
    $age = (Get-Date) - (Get-Item -LiteralPath $busy).LastWriteTime
    return $age.TotalSeconds -lt 180
}

function Get-CrashLines {
    $text = (Invoke-Adb @("logcat", "-d", "-t", "400")) -join "`n"
    $pattern = "FATAL EXCEPTION|Fatal signal|ANR in com\.puzzle\.miniworld\.cn|has died|Force finishing|Process com\.puzzle\.miniworld\.cn"
    $lines = @()
    foreach ($line in ($text -split "`r?`n")) {
        if ($line -match $pattern) {
            $lines += $line.Trim()
        }
    }
    return ($lines | Select-Object -Last 8)
}

if ($TestPopup) {
    Write-Log "monitor self-test"
    Show-Popup "self-test" "拼模型助手监测" "监测脚本运行正常。`r`n日志：$logFile" 0
    exit
}

Write-Log "monitor started (pid=$PID)"

while ($true) {
    $connected = Test-Device
    $gamePid = Get-GamePid

    if ($null -ne $gamePid) {
        if ($gamePid -ne $script:lastPid) {
            Write-Log "game started pid=$gamePid"
            Invoke-Adb @("logcat", "-c") | Out-Null
            $script:lastPid = $gamePid
            $script:lastResult = ""
            $script:lastErrHash = ""
            $script:lastCrashHash = ""
        }

        $result = Get-RemoteText "/sdcard/Android/data/$package/files/pw3d.result"
        if ($result -and $result -ne $script:lastResult) {
            $script:lastResult = $result
            Write-Log "command result: $result"
            if ($result -match "timeout") {
                Show-Popup "cmd-timeout" "拼模型助手：命令超时" "插件命令超时，游戏可能卡住或未响应。`r`n`r`n请查看：`r`n$logFile`r`n`r`n最近结果：$result"
            } elseif ($result -match "(?i)error|fail|exception") {
                Show-Popup ("cmd-error:" + $result.GetHashCode()) "拼模型助手：命令失败" "插件命令返回错误。`r`n`r`n结果：$result`r`n`r`n日志：$logFile"
            }
        }

        $errPath = Join-Path $logDir "ui_run.err.log"
        if (Test-Path -LiteralPath $errPath) {
            $errText = (Get-Content -LiteralPath $errPath -Tail 12 -ErrorAction SilentlyContinue) -join "`n"
            if (-not [string]::IsNullOrWhiteSpace($errText)) {
                $hash = $errText.GetHashCode().ToString()
                if ($hash -ne $script:lastErrHash) {
                    $script:lastErrHash = $hash
                    Write-Log "ui stderr: $errText"
                    if ($errText -match "(?i)exception|timeout|timed out|ProcessNotResponding|traceback") {
                        Show-Popup ("ui-err:" + $hash) "拼模型助手：界面脚本报错" "浮窗脚本报错。`r`n`r`n$errText`r`n`r`n日志：$logFile"
                    }
                }
            }
        }
    } else {
        if ($null -ne $script:lastPid) {
            $lostPid = $script:lastPid
            $script:lastPid = $null
            $commandRunning = Get-CommandRunning
            $crashes = @()
            if ($connected) {
                $crashes = @(Get-CrashLines)
            }
            $crashText = ($crashes -join "`n").Trim()
            Write-Log "game exited pid=$lostPid commandRunning=$commandRunning crashLines=$($crashes.Count)"

            if ($crashText) {
                $hash = $crashText.GetHashCode().ToString()
                if ($hash -ne $script:lastCrashHash) {
                    $script:lastCrashHash = $hash
                    Write-Log "crash evidence: $crashText"
                    Show-Popup ("crash:" + $hash) "拼模型助手：游戏异常退出" "检测到游戏进程崩溃或无响应退出（非正常关闭）。`r`n`r`n$crashText`r`n`r`n日志：$logFile"
                }
            } elseif ($commandRunning) {
                Show-Popup ("exit-during-command:" + (Get-Date -Format "yyyyMMddHHmm")) "拼模型助手：游戏异常退出" "插件命令执行期间游戏进程消失。`r`n`r`n最后 PID：$lostPid`r`n`r`n日志：$logFile"
            } else {
                Write-Log "game closed normally"
            }
        }
    }

    Start-Sleep -Seconds 2
}
