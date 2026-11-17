# Changelog

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
