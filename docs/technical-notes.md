# Technical Notes

## Runtime

- Game process: x86_64 under MuMu.
- Game native code: ARM64 `libil2cpp.so`, translated by Houdini.
- Plugin: ARM64 shared library loaded with `java.lang.Runtime.load0`.
- Control channel: text files under the game external files directory.

## Main Thread

`GameManager.Update` is called every frame. The plugin saves the original
`MethodInfo.methodPointer` and replaces it with its own entry. Commands run
inside that entry, then the original method runs.

If no tick arrives within two seconds, the plugin restores the original pointer
and executes commands on the attached worker thread.

## Free Currency

The A-plan guard reads `PlayerDataManager.GetGoods` on the main thread. When a
balance drops, it opens a five-second purchase window and writes the target
value back with `SetGoods` at 300 ms intervals. The client display stays high,
but the server can still reject or deduct based on the real balance.

The older `CostGoods` instruction patch and `GoodItemsManager.synGoodsList`
removal are kept only as fallback paths in older builds.

## Ads

The v8 ad path writes the remove-ad entitlement with
`PlayerDataManager.SetBuyRemoveAdNum(1)` and `UpdateRemoveAdData()`. It then
replaces four native entries:

- `SDKSAdManager.IsRewardedVideoReady`
- `AdsMgr.checkRewardedVideoAdIsReady()` with zero arguments
- `AdsMgr.checkRewardedVideoAdIsReady(string)` with one argument
- `SDKSAdManager.ShowRewardedVideoAd`

The show hook returns success and sets a pending flag. The next
`GameManager.Update` tick calls `AdsMgr.HandleRewardBasedVideoRewarded(true)` and
`AdsMgr.HandleRewardBasedVideoClosed()`. The delay lets the AdsMgr wrapper finish
its state update before the reward event is sent.

## Auto Assemble

The plugin finds the active `battlePanel`, sets `autoPuzzleSpeed` to `0.3`, and
calls `PuzzleManager.StartAutoFinishPuzzle()`. The game then runs its own
per-piece animation and combo scoring.

## VIP

The current VIP switch writes `IsVipAndMonthCardPlayerKey` and calls
`VipDataManager.BuyMonthCardSuccess()`. The callback updates local month-card
timestamps and UI. It must run on the Unity main thread.

The next version should pre-seed the month-card start and end timestamps and
clear them on disable. The auxiliary key alone does not make
`VipDataManager.IsVip()` return true.

## Limits

- A game update can move method signatures or change field layouts.
- Server-side balance checks still apply to purchases.
- Ad rewards can still be rejected if the server requires an ad receipt.
- VIP changes are client-side; server-issued monthly rewards may not arrive.
- Theme unlock requires an open theme detail page.
