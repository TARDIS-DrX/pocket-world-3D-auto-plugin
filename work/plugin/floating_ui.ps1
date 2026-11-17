$ErrorActionPreference = "Stop"
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

$mutex = New-Object System.Threading.Mutex($false, "Global\PW3D-UI")
if (-not $mutex.WaitOne(0)) {
    exit
}

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$adb = "D:\TapTap\Support\android_emulator\engine\nx_device\12.0\shell\adb.exe"
$device = "127.0.0.1:16416"
$python = (Get-Command python).Source
$logDir = Join-Path $root "work\plugin"
$outLog = Join-Path $logDir "ui_run.out.log"
$errLog = Join-Path $logDir "ui_run.err.log"
$cfgPath = "/sdcard/Android/data/com.puzzle.miniworld.cn/files/pw3d.cfg"

$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="拼模型助手" Width="64" Height="64"
        WindowStyle="None" AllowsTransparency="True" Background="Transparent"
        Topmost="True" ShowInTaskbar="False" ResizeMode="NoResize">
  <Grid>
    <Border x:Name="Ball" CornerRadius="32" Background="#D91F2329"
            BorderBrush="#414751" BorderThickness="1">
      <Grid>
        <TextBlock Text="拼" Foreground="#F2F2F2" FontFamily="Microsoft YaHei UI"
                   FontSize="20" FontWeight="Bold"
                   HorizontalAlignment="Center" VerticalAlignment="Center"/>
        <Ellipse x:Name="Dot" Width="10" Height="10" Fill="#E05252"
                 HorizontalAlignment="Right" VerticalAlignment="Bottom"
                 Margin="0,0,6,6"/>
      </Grid>
    </Border>

    <Border x:Name="Panel" Visibility="Collapsed" CornerRadius="12"
            Background="#F21F2329" BorderBrush="#414751" BorderThickness="1">
      <Grid Margin="16">
        <TextBlock Text="拼模型助手" Foreground="#F2F2F2"
                   FontFamily="Microsoft YaHei UI" FontSize="13" FontWeight="Bold"
                   VerticalAlignment="Top"/>
        <TextBlock x:Name="CloseBtn" Text="×" Foreground="#9AA0A6"
                   FontFamily="Microsoft YaHei UI" FontSize="16"
                   HorizontalAlignment="Right" VerticalAlignment="Top"
                   Cursor="Hand"/>

        <StackPanel Margin="0,32,0,0">
          <StackPanel Orientation="Horizontal" Margin="0,0,0,8">
            <Ellipse x:Name="PanelDot" Width="9" Height="9" Fill="#E05252"
                     VerticalAlignment="Center" Margin="0,0,7,0"/>
            <TextBlock x:Name="StatusText" Text="检测中..." Foreground="#9AA0A6"
                       FontFamily="Microsoft YaHei UI" FontSize="9"
                       VerticalAlignment="Center"/>
          </StackPanel>

          <Button x:Name="AutoBtn" Content="自动拼完" Height="42"
                  Background="#F0A04B" Foreground="#1B1D21" BorderThickness="0"
                  FontFamily="Microsoft YaHei UI" FontSize="12" FontWeight="Bold"
                  Cursor="Hand" IsEnabled="False"/>

          <CheckBox x:Name="FreeBox" Content="金币 / 钻石不消耗" Foreground="#F2F2F2"
                    FontFamily="Microsoft YaHei UI" FontSize="10"
                    Margin="2,14,0,0" IsEnabled="False"/>

          <StackPanel Orientation="Horizontal" Margin="0,12,0,0">
            <Border Background="#333A44" CornerRadius="6" Width="158" Height="32">
              <Button x:Name="AdsBtn" Content="广告破解" Background="Transparent"
                      Foreground="#F2F2F2" BorderThickness="0"
                      FontFamily="Microsoft YaHei UI" FontSize="10"
                      Cursor="Hand" IsEnabled="False"/>
            </Border>
            <CheckBox x:Name="VipBox" Content="VIP 会员" Foreground="#F2F2F2"
                      FontFamily="Microsoft YaHei UI" FontSize="10"
                      VerticalAlignment="Center" Margin="12,0,0,0"
                      IsEnabled="False"/>
          </StackPanel>

          <Border Background="#333A44" CornerRadius="6" Margin="0,10,0,0" Height="34">
            <Button x:Name="ThemeBtn" Content="解锁当前主题" Background="Transparent"
                    Foreground="#F2F2F2" BorderThickness="0"
                    FontFamily="Microsoft YaHei UI" FontSize="10"
                    Cursor="Hand" IsEnabled="False"/>
          </Border>

          <TextBlock x:Name="ResultText" Text="" Foreground="#9AA0A6"
                     FontFamily="Microsoft YaHei UI" FontSize="8"
                     TextWrapping="Wrap" Margin="0,10,0,0" MaxHeight="30"/>
        </StackPanel>
      </Grid>
    </Border>
  </Grid>
</Window>
"@

$reader = New-Object System.Xml.XmlNodeReader ([xml]$xaml)
$window = [Windows.Markup.XamlReader]::Load($reader)
$ball = $window.FindName("Ball")
$dot = $window.FindName("Dot")
$panel = $window.FindName("Panel")
$panelDot = $window.FindName("PanelDot")
$statusText = $window.FindName("StatusText")
$autoBtn = $window.FindName("AutoBtn")
$freeBox = $window.FindName("FreeBox")
$adsBtn = $window.FindName("AdsBtn")
$vipBox = $window.FindName("VipBox")
$themeBtn = $window.FindName("ThemeBtn")
$resultText = $window.FindName("ResultText")
$closeBtn = $window.FindName("CloseBtn")

function Brush([string]$hex) {
    return [System.Windows.Media.BrushConverter]::new().ConvertFromString($hex)
}

$window.Left = [System.Windows.SystemParameters]::PrimaryScreenWidth * 0.66 - 32
$window.Top = [System.Windows.SystemParameters]::PrimaryScreenHeight * 0.205 - 32

$script:busy = $false
$script:moved = $false
$script:dragStart = $null
$script:runProcess = $null
$script:pendingLabel = ""
$script:ensured = $false
$script:freeOn = $false
$script:adsOn = $false
$script:vipOn = $false
$script:stoppedTicks = 0

function Get-GameState {
    try {
        & $adb connect $device 2>$null | Out-Null
        $devices = (& $adb devices 2>$null) -join "`n"
        if ($devices -notmatch [regex]::Escape($device)) {
            return "offline"
        }
        $pidText = (& $adb -s $device shell "pidof com.puzzle.miniworld.cn" 2>$null) -join ""
        if ($pidText -match "\d+") {
            return "running"
        }
        return "stopped"
    } catch {
        return "offline"
    }
}

function Read-Cfg {
    try {
        $text = (& $adb -s $device shell "su -c 'cat $cfgPath'" 2>$null) -join "`n"
        $script:freeOn = $text -match "free=1"
        $script:adsOn = $text -match "ads=1"
        $script:vipOn = $text -match "vip=1"
    } catch {
    }
}

function Update-ToggleVisuals {
    if ($script:adsOn) {
        $adsBtn.Content = "广告破解：已开启"
        $adsBtn.Foreground = Brush "#48C774"
    } else {
        $adsBtn.Content = "广告破解"
        $adsBtn.Foreground = Brush "#F2F2F2"
    }
    $freeBox.IsChecked = $script:freeOn
    $vipBox.IsChecked = $script:vipOn
}

function Set-Controls([bool]$enabled) {
    $autoBtn.IsEnabled = $enabled
    $themeBtn.IsEnabled = $enabled
    $adsBtn.IsEnabled = $enabled
    $freeBox.IsEnabled = $enabled
    $vipBox.IsEnabled = $enabled
}

function Update-Status {
    if ($script:busy) {
        return
    }
    $state = Get-GameState
    if ($state -eq "running") {
        $script:stoppedTicks = 0
        $dot.Fill = Brush "#48C774"
        $panelDot.Fill = Brush "#48C774"
        if (-not $script:ensured) {
            $statusText.Text = "正在加载插件..."
            Start-Command "ensure" "插件已加载"
            return
        }
        $statusText.Text = "游戏运行中"
        Set-Controls $true
    } elseif ($state -eq "stopped") {
        $dot.Fill = Brush "#E05252"
        $panelDot.Fill = Brush "#E05252"
        $statusText.Text = "游戏未启动"
        $script:ensured = $false
        Set-Controls $false
        $script:stoppedTicks++
        if ($script:stoppedTicks -ge 3) {
            $window.Close()
            return
        }
    } else {
        $dot.Fill = Brush "#E05252"
        $panelDot.Fill = Brush "#E05252"
        $statusText.Text = "模拟器未连接"
        $script:ensured = $false
        Set-Controls $false
    }
}

function Start-Command([string]$command, [string]$label) {
    if ($script:busy) {
        return
    }
    $script:busy = $true
    Set-Controls $false
    $script:pendingLabel = $label
    $resultText.Text = "执行中：$label"
    Remove-Item $outLog, $errLog -ErrorAction SilentlyContinue
    if ($command -eq "ensure") {
        $cliArgs = @("work\plugin\pw3d_plugin.py", "ensure")
    } else {
        $cliArgs = @("work\plugin\pw3d_plugin.py", "cmd", $command)
    }
    $script:runProcess = Start-Process -FilePath $python `
        -ArgumentList $cliArgs `
        -WorkingDirectory $root -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog
}

$timer = New-Object System.Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromSeconds(3)
$timer.Add_Tick({ Update-Status })
$timer.Start()

$ball.Add_MouseLeftButtonDown({
    $script:dragStart = $_.GetPosition($window)
    $script:moved = $false
})
$ball.Add_MouseMove({
    if ($script:dragStart -eq $null -or $_.LeftButton -ne "Pressed") {
        return
    }
    $point = $_.GetPosition($window)
    if ([Math]::Abs($point.X - $script:dragStart.X) + [Math]::Abs($point.Y - $script:dragStart.Y) -gt 2) {
        $script:moved = $true
        $window.DragMove()
        $script:dragStart = $null
    }
})
$ball.Add_MouseLeftButtonUp({
    if (-not $script:moved) {
        $window.Width = 300
        $window.Height = 380
        $ball.Visibility = "Collapsed"
        $panel.Visibility = "Visible"
        Read-Cfg
        Update-ToggleVisuals
        Update-Status
    }
    $script:dragStart = $null
    $script:moved = $false
})
$ball.Add_MouseRightButtonUp({ $window.Close() })
$panel.Add_MouseRightButtonUp({ $window.Close() })
$panel.Add_MouseLeftButtonDown({
    $source = $_.OriginalSource
    if ($source -is [System.Windows.Controls.Button] -or
        $source -is [System.Windows.Controls.CheckBox]) {
        return
    }
    try {
        $window.DragMove()
    } catch {
    }
})

$closeBtn.Add_MouseLeftButtonUp({
    $window.Width = 64
    $window.Height = 64
    $panel.Visibility = "Collapsed"
    $ball.Visibility = "Visible"
})
$closeBtn.Add_MouseLeftButtonDown({ $_.Handled = $true })

$autoBtn.Add_Click({ Start-Command "auto" "自动拼完" })
$themeBtn.Add_Click({ Start-Command "theme" "解锁当前主题" })

$freeBox.Add_Click({
    if ($script:busy) {
        $freeBox.IsChecked = $script:freeOn
        return
    }
    if ($freeBox.IsChecked) {
        Start-Command "free:1" "开启金币钻石不消耗"
    } else {
        Start-Command "free:0" "关闭金币钻石不消耗"
    }
})

$adsBtn.Add_Click({
    if ($script:busy) { return }
    if ($script:adsOn) {
        Start-Command "ads:0" "关闭广告破解"
    } else {
        Start-Command "ads:1" "开启广告破解"
    }
})

$vipBox.Add_Click({
    if ($script:busy) {
        $vipBox.IsChecked = $script:vipOn
        return
    }
    if ($vipBox.IsChecked) {
        Start-Command "vip:1" "开启 VIP 会员"
    } else {
        Start-Command "vip:0" "关闭 VIP 会员"
    }
})

$runTimer = New-Object System.Windows.Threading.DispatcherTimer
$runTimer.Interval = [TimeSpan]::FromMilliseconds(400)
$runTimer.Add_Tick({
    if ($script:runProcess -eq $null -or -not $script:runProcess.HasExited) {
        return
    }
    $runTimer.Stop()
    $text = ""
    if (Test-Path $outLog) {
        $text = (Get-Content $outLog -Tail 2 -ErrorAction SilentlyContinue) -join " "
    }
    if ([string]::IsNullOrWhiteSpace($text) -and (Test-Path $errLog)) {
        $text = (Get-Content $errLog -Tail 3 -ErrorAction SilentlyContinue) -join " "
    }
    if ([string]::IsNullOrWhiteSpace($text)) {
        $text = "已执行"
    }
    $text = $text.Trim()
    $script:runProcess = $null

    if ($script:pendingLabel -eq "插件已加载") {
        $script:ensured = $true
        Read-Cfg
        Update-ToggleVisuals
        $resultText.Text = "插件已就绪"
    } else {
        if ($text -eq "free:on") {
            $script:freeOn = $true
            $resultText.Text = "金币钻石不再消耗"
        } elseif ($text -eq "free:off") {
            $script:freeOn = $false
            $resultText.Text = "已恢复金币钻石消耗"
        } elseif ($text -eq "ads:on") {
            $script:adsOn = $true
            $resultText.Text = "广告破解已开启"
        } elseif ($text -eq "ads:off") {
            $script:adsOn = $false
            $resultText.Text = "广告破解已关闭"
        } elseif ($text -eq "vip:on") {
            $script:vipOn = $true
            $resultText.Text = "VIP 会员已开启"
        } elseif ($text -eq "vip:off") {
            $script:vipOn = $false
            $resultText.Text = "VIP 会员已关闭"
        } elseif ($text -match "^theme:(\d+)") {
            $resultText.Text = "已解锁主题 $($matches[1])"
        } elseif ($text -eq "auto:started") {
            $resultText.Text = "已开始逐件自动拼装"
        } elseif ($text -eq "auto:done") {
            $resultText.Text = "已自动拼完"
        } else {
            $resultText.Text = $text
        }
        Update-ToggleVisuals
    }
    $script:busy = $false
    Update-Status
    $runTimer.Start()
})
$runTimer.Start()

$window.Add_Closed({
    try { $mutex.ReleaseMutex() } catch {}
})

$window.ShowDialog() | Out-Null
try { $mutex.ReleaseMutex() } catch {}
