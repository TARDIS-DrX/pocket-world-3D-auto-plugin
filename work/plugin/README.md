# Pocket World 3D 拼模型助手 v3（广告破解 v8）

## 功能

- 自动拼完：把 `battlePanel.autoPuzzleSpeed` 调到 `0.3`，再调用 `PuzzleManager.StartAutoFinishPuzzle()`，走游戏自己的逐件动画和计分流程。
- 金币 / 钻石不消耗（A 方案）：主线程周期性读取 `PlayerDataManager.GetGoods`，检测到余额下降后进入 5 秒购买窗口，按 300ms 间隔调用 `SetGoods(type, 999999, 0, false)` 回写。目标值可通过 `target:` 修改。
- 广告破解：`ads:1` 写入去广告权益（`SetBuyRemoveAdNum(1)` + `UpdateRemoveAdData()`），并内联替换广告就绪检查与 Show 入口；奖励和关闭事件延后一帧发送。
- VIP 会员（旧路径）：写入 `IsVipAndMonthCardPlayerKey`，并调用 `VipDataManager.BuyMonthCardSuccess()`。此路径必须在 Unity 主线程执行。
- 解锁当前主题：读取当前打开的 `KitInfoPanel.kit`，只解锁当前主题。
- 单实例浮窗：全局互斥锁保证只开一个；游戏退出后浮窗自动关闭；展开状态下也能拖动。

## 交互

- 悬浮球默认位于屏幕水平 66%、垂直 20.5% 的位置。
- 点击悬浮球展开；展开后按住空白处可拖动。
- 面板包含自动拼完、金币/钻石不消耗、广告破解、VIP 会员、解锁当前主题。
- 右键悬浮球退出。

## 命令

```powershell
python work\plugin\pw3d_plugin.py ensure
python work\plugin\pw3d_plugin.py cmd auto
python work\plugin\pw3d_plugin.py cmd free:1
python work\plugin\pw3d_plugin.py cmd free:0
python work\plugin\pw3d_plugin.py cmd keep:1
python work\plugin\pw3d_plugin.py cmd keep:0
python work\plugin\pw3d_plugin.py cmd target:999999
python work\plugin\pw3d_plugin.py cmd probe
python work\plugin\pw3d_plugin.py cmd dump
python work\plugin\pw3d_plugin.py cmd reset
python work\plugin\pw3d_plugin.py cmd ads:1
python work\plugin\pw3d_plugin.py cmd adshook:1
python work\plugin\pw3d_plugin.py cmd adreward
python work\plugin\pw3d_plugin.py cmd adsstate
python work\plugin\pw3d_plugin.py cmd vip:1
python work\plugin\pw3d_plugin.py cmd theme
python work\plugin\pw3d_plugin.py log
```

## 主线程调度

插件加载后把 `GameManager.Update` 的 `MethodInfo.methodPointer` 换成自己的入口。命令在 Unity 主线程执行，避免非主线程发通知导致游戏重启。若 2 秒内没有收到 Update tick，会自动回退到工作线程执行。

## 监测与报错

- `watch_game.ps1` 在游戏启动时自动启动 `monitor_game.ps1`，也可以双击 `monitor_game.bat` 手动启动。
- 监测脚本只允许一个实例（`Global\PW3D-Monitor`），每 2 秒检查一次游戏进程、`pw3d.result` 和 `ui_run.err.log`。
- 命令返回 `timeout`、插件返回 `error`/`fail`、界面脚本抛出异常时弹出提示框。
- 游戏进程消失时先查 logcat：命中 `FATAL EXCEPTION`、`Fatal signal`、`ANR` 或进程死亡记录，判定为异常退出并弹窗；没有崩溃证据时记为正常关闭，不弹窗。
- 同一条错误 5 分钟内只弹一次。

## 编译

需要 Zig 0.13+（`zig` 在 PATH，或设置 `ZIG` 环境变量）：

```powershell
.\work\plugin\build.ps1
```

## 已知限制

- A 方案只保证客户端显示余额维持在高值；真实购买仍由服务器扣款。
- 超大额探针实测：真实金币低于商品价格时，服务器会返回“金币不足”；A 方案不能绕过服务端余额校验。
- 广告奖励：客户端已能跳过播放并走完领取流程；若服务器要求广告凭证，商品到账仍可能被服务端拒绝。
- VIP 开关：当前仍是旧实现，只写辅助 key 并调用月卡成功回调；不能可靠关闭，且从插件线程调用可能导致游戏退出。下一版改为月卡起止时间戳预置。
- 主题解锁需要先进入某个主题详情页。
- 所有修改都是本地行为；重登后服务器下发真实余额，守护会再次把它抬到目标值。

日志：`/sdcard/Android/data/com.puzzle.miniworld.cn/files/pw3dmod.log`
