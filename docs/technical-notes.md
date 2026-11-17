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

`PlayerDataManager.CostGoods` computes `newValue = max(current - cost, 0)`.
The plugin changes the subtraction to keep `current`.

`GoodItemsManager.synGoodsList` controls which goods are sent to the server.
Coin and Diamond are removed from that list so the cost stays local.

If the instruction signature is not found, the plugin restores the balance when
it drops below the value captured when the switch was enabled.

## Auto Assemble

The plugin finds the active `battlePanel`, sets `autoPuzzleSpeed` to `0.3`, and
calls `PuzzleManager.StartAutoFinishPuzzle()`. The game then runs its own
per-piece animation and combo scoring.

## Limits

- A game update can move method signatures or change field layouts.
- Theme unlock requires an open theme detail page.
- Server-side rollback may require using the switch again.
