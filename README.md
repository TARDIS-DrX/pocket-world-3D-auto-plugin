# 我爱拼模型（Pocket World）快速拼装插件

面向 TapTap MuMu 版《我爱拼模型 / Pocket World 3D》的本地浮窗助手。它通过 Frida 把 ARM64 插件加载进游戏的 IL2CPP 进程，在 Unity 主线程调用游戏原有的功能路径。

![Windows](https://img.shields.io/badge/platform-Windows-0078D4)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
![Game](https://img.shields.io/badge/Pocket%20World%203D-3.3.0-2ea44f)

我不想再看到别人因为游戏道具被限制了，我希望大家都能开心自在的享受游戏，所以请看好了，我的**插件**！<img width="20" height="20" alt="00513ADC" src="https://github.com/user-attachments/assets/ec9aa7b6-0726-4dba-b7e9-323b43d345d1" />


>回归游戏本身的乐趣

## 功能

- **自动拼完**：降低 `battlePanel.autoPuzzleSpeed`，再调用 `PuzzleManager.StartAutoFinishPuzzle()`，保留逐件动画和连击计分。
- **金币 / 钻石不消耗**：阻止 Coin/Diamond 的消耗同步，并让 `CostGoods` 保留当前余额。
- **广告破解**：调用游戏自己的去广告路径，并触发广告奖励回调。
- **VIP 会员**：写入 VIP 标志，并调用月卡/VIP 成功回调。
- **解锁当前主题**：只解锁当前打开的主题详情页。
- **单实例浮窗**：跟随游戏启动和退出，展开后可以拖动。

## 目录

```text
run.ps1                     启动浮窗；带参数时转发给插件 CLI
run-overlay.ps1             兼容入口，等同 run.ps1
bootstrap.ps1               环境检查
enable-root-mode.ps1        给 MuMu 打开 root
disable-root-mode.ps1       关闭 root
work/plugin/
  pw3dmod.c                 ARM64 插件源码
  libpw3dmod.so             预编译插件
  build.ps1                 交叉编译脚本
  pw3d_plugin.py            部署、加载、命令、日志
  floating_ui.ps1           WPF 浮窗
  watch_game.ps1            游戏进程检测
  install_autostart.ps1     登录自启动
work/frida-agent/bundle.js  Frida Java bridge
work/tools/                 编译用 bionic 存根库
```

## 使用

1. 关闭 TapTap 和 MuMu，运行：

```powershell
.\enable-root-mode.ps1
```

2. 重新打开 TapTap、MuMu 和游戏。
3. 检查环境：

```powershell
.\bootstrap.ps1
```

4. 启动浮窗：

```powershell
.\run.ps1
```

5. 点击悬浮球展开面板。首次会自动部署并加载插件。

命令行：

```powershell
.\run.ps1 ensure
.\run.ps1 cmd auto
.\run.ps1 cmd free:1
.\run.ps1 cmd ads:1
.\run.ps1 cmd vip:1
.\run.ps1 log
```

## 它是怎么工作的

```text
Python 写命令文件
  → ARM64 插件读取命令
  → GameManager.Update 的 MethodInfo 入口切到插件
  → 在 Unity 主线程调用游戏自己的方法
  → 结果写回 pw3d.result
```

关键目标：

- 自动拼装：`PuzzleManager.StartAutoFinishPuzzle()`、`battlePanel.autoPuzzleSpeed`
- 免消耗：`PlayerDataManager.CostGoods`、`GoodItemsManager.synGoodsList`
- 广告：`PlayerDataManager.UpdateRemoveAdData`、`AdsMgr.HandleRewardBasedVideoRewarded`
- VIP：`UserDataManager.SetInt("IsVipAndMonthCardPlayerKey")`、`VipDataManager.BuyMonthCardSuccess`
- 主题：`KitInfoPanel.kit`、`UnLockKitLevelByKit`、`UpdateLevelKitDataIsUnlock`

如果主线程入口 2 秒内没有收到 tick，会自动回退到工作线程执行，并在日志里写 `worker thread fallback`。

## 日志

```text
/sdcard/Android/data/com.puzzle.miniworld.cn/files/pw3dmod.log
```

## 版本支持

| 游戏版本 | 状态 |
| --- | --- |
| `3.3.0` | 已核对方法名与字段；金币/钻石、VIP、广告命令实测通过 |
| `3.2.9` | 代码地图与自动拼链路已分析 |

## 编译

需要 Zig 0.13+（`zig` 在 PATH，或设置 `ZIG` 环境变量）：

```powershell
.\work\plugin\build.ps1
```

## 安全边界

- 只支持 TapTap MuMu 实例，包名 `com.puzzle.miniworld.cn`。
- 需要 root 和 `/data/local/tmp/frida-server-x86_64`。
- 仓库不包含游戏 APK、账号数据或付费内容。
- 仅用于个人学习、测试与已授权环境；请遵守游戏条款和当地法律。

## 开发

```powershell
python -m py_compile work\plugin\pw3d_plugin.py
```

项目代码采用 MIT License。第三方组件说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
