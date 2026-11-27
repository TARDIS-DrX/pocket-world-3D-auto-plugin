# Changelog

## 0.3.0

- 广告破解改为 v8：预置去广告权益，并内联替换广告就绪检查与 Show 入口。
- 奖励与关闭事件延后到下一帧主线程发送，避免 AdsMgr 状态被提前清空。
- 实测商店“AD 免费领取”不播放广告即可完成领取流程；剩余次数从 2 变为 1，余额不变。
- 保留自动拼完、金币/钻石守护、VIP 旧路径和主题解锁。
- 已知：VIP 开关仍写辅助 key 并调用月卡成功回调，需要下一版改成月卡时间戳预置。

## 0.2.0

- Replaced the APK 4-byte patch flow with a Frida + ARM64 native plugin.
- Added Unity main-thread dispatch through `GameManager.Update`.
- Added infinite coin/diamond, ad crack, VIP member and current-theme unlock.
- Added single-instance floating overlay with expanded-panel dragging.
- Added automatic overlay shutdown when the game exists.

## 0.1.0

- Added version-aware APK patch detection.
- Added automatic IL2CPP re-analysis for new game versions.
- Added `3.2.9 / 30011290` patch data.
- Added byte verification and `restore`.
- Added patch-table self-tests.
- Added Windows setup scripts and GitHub Actions CI.
