# How It Works

## Target Callback

The game already contains the full auto-assembly state machine. The relevant
entry point is:

```text
PuzzleManager.StartAutoFinishPuzzle()
```

The normal UI flow calls this method after a prop-cost callback succeeds.

## Button Redirects

The tool changes the first AArch64 instruction of two methods:

```text
battlePanel.AutoFinishBtnClick
battlePanel.TipBtnCallBack
```

The new instruction is an unconditional branch to the existing
`<ShowAutoFinishPropDialog>b__*_1` callback. That callback starts
`StartAutoFinishPuzzle()`.

The normal prop confirmation and cost path is not entered.

## In-Place Patch

`libil2cpp.so` is stored uncompressed in the current APK. The tool calculates
the absolute APK offset from:

```text
ZIP local header offset
+ local header size
+ file name length
+ extra field length
+ libil2cpp.so method offset
```

The tool writes four bytes at each calculated offset. It then reads the bytes
back and compares them with the new branch instruction.

## Restore

The tool saves the original four bytes in `state/<version>.json`. The
`restore` command writes these bytes back to the installed APK.
