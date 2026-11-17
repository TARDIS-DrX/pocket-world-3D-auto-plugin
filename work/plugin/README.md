# Pocket World 3D 拼模型助手 v3

## 功能

- 自动拼完：把 `battlePanel.autoPuzzleSpeed` 调到 `0.3`，再调用 `PuzzleManager.StartAutoFinishPuzzle()`，走游戏自己的逐件动画和计分流程。
- 金币 / 钻石不消耗：把 `GoodItemsManager.synGoodsList` 里的 Coin/Diamond 移除，阻止消耗同步到服务器；同时把 `CostGoods` 的扣减指令改成保留当前值。
- 广告破解：调用游戏自己的去广告路径 `UpdateRemoveAdData`，并触发 `HandleRewardBasedVideoRewarded(true)`。
- VIP 会员：写入 `IsVipAndMonthCardPlayerKey`，并调用 `VipDataManager.BuyMonthCardSuccess()`。
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
python work\plugin\pw3d_plugin.py cmd ads:1
python work\plugin\pw3d_plugin.py cmd vip:1
python work\plugin\pw3d_plugin.py cmd theme
python work\plugin\pw3d_plugin.py log
```

## 主线程调度

插件加载后把 `GameManager.Update` 的 `MethodInfo.methodPointer` 换成自己的入口。命令在 Unity 主线程执行，避免非主线程发通知导致游戏重启。若 2 秒内没有收到 Update tick，会自动回退到工作线程执行。

## 编译

需要 Zig 0.13+（`zig` 在 PATH，或设置 `ZIG` 环境变量）：

```powershell
.\work\plugin\build.ps1
```

## 已知限制

- `CostGoods` 的补丁按 3.3.0 的指令特征匹配；换版本后若特征不存在，会退回“定时把余额恢复为初始值”的兜底方案。
- 主题解锁需要先进入某个主题详情页。
- 所有修改都是本地行为；服务器恢复数据后可能需要重新点一次开关。

日志：`/sdcard/Android/data/com.puzzle.miniworld.cn/files/pw3dmod.log`
