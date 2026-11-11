# Pocket World Quick Assembly

> 把重复的拼装，交还给游戏自己完成。

![Windows](https://img.shields.io/badge/platform-Windows-0078D4)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
![Game](https://img.shields.io/badge/Pocket%20World%203D-3.2.9-2ea44f)

这是一个面向 TapTap MuMu 版《我爱拼模型 / Pocket World 3D》的本地拼装助手。

它不替你写一套“假拼装”。它找到游戏里原本就存在的自动拼接流程，让那个按钮真正为你工作。

## 为什么做这个

拼模型最舒服的时刻，是看一个场景慢慢成形。

但当零件已经熟悉、关卡开始重复，一次次拖动、对准和等待吸附，就变成了机械劳动。这个项目只处理这段重复过程，让你把时间留给新模型、新场景和收藏本身。

## 它能做什么

- **一键复用游戏原有拼接流程**：不重新实现拼装算法。
- **同时接管两个入口**：自动拼按钮和提示按钮都能直接启动拼接。
- **跟着游戏一起更新**：检测版本号、版本代码和 APK 大小，新版本自动重新分析。
- **尽量少改东西**：每个入口只改 4 字节，不携带 APK 或游戏资源。
- **随时可以恢复**：保存原始字节，运行一次 `restore` 即可还原。

## 快速开始

### 1. 打开调试 root

关闭 TapTap 和 MuMu，然后运行：

```powershell
.\enable-root-mode.ps1
```

完成后重新启动 TapTap、MuMu 和目标游戏。

### 2. 检查环境

```powershell
.\bootstrap.ps1
```

需要 Python 3.10+ 和 .NET 6 Runtime。

### 3. 进入一个拼装关卡

风车村、京都 I，或者任意已解锁模型都可以。

### 4. 启动助手

```powershell
.\run.ps1
```

助手会读取当前游戏版本、准备补丁并应用。进入关卡后，点击自动拼按钮或提示按钮即可。

## 版本支持

| 游戏版本 | Version Code | 状态 |
| --- | ---: | --- |
| `3.2.9` | `30011290` | 已验证补丁表 |

遇到新版本时，助手会优先寻找 TapTap 下载的完整 APK；找不到时再从模拟器拉取。随后自动解包 IL2CPP、定位入口、生成新补丁表。

## 常用命令

```powershell
.\run.ps1            # 检测版本、应用补丁并启动游戏
.\run.ps1 detect     # 只检测版本
.\run.ps1 selftest   # 校验补丁表，不改游戏
.\run.ps1 analyze    # 重新分析当前版本
.\run.ps1 restore    # 恢复原始 APK 字节
```

## 它是怎么工作的

游戏里已经有完整的自动拼接状态机：

```text
PuzzleManager.StartAutoFinishPuzzle()
```

插件把 `AutoFinishBtnClick` 和 `TipBtnCallBack` 的入口转向这段已有逻辑。原本的道具确认和扣费流程不会进入。

说到底，它做的是“把入口接对”，而不是重写游戏。

更多实现细节见 [How It Works](docs/how-it-works.md)，版本适配流程见 [Version Detection](docs/version-detection.md)。

## 安全边界

- 只支持 TapTap MuMu 实例，包名固定为 `com.puzzle.miniworld.cn`。
- 会直接修改已安装 APK 中的 4 字节入口，请先备份重要数据。
- 仓库不包含 APK、游戏资源、账号数据或付费内容。
- 请只在你有权控制的设备与账号上使用，并遵守游戏条款和当地法律。

## 开发

```powershell
python -m unittest discover -s tests -v
python .\plugin.py selftest
```

项目代码采用 MIT License。第三方组件说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
