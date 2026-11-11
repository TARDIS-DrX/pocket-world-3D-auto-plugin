# Version Detection

## Detection Values

The plugin uses three values:

```text
versionName
versionCode
installed APK size
```

The APK size protects against a changed APK that keeps the same version number.

## Known Version

If all three values match `patch_manifest.json`, the plugin reuses the saved
offsets.

## New Version

If a value differs, the plugin performs these steps:

1. Find a local TapTap APK with the same byte size.
2. Pull the installed APK if no local match exists.
3. Extract `libil2cpp.so` and `global-metadata.dat`.
4. Run Il2CppDumper.
5. Parse the `battlePanel` class.
6. Locate the two button methods and the shared callback.
7. Calculate branch instructions.
8. Save a new manifest entry.

## Failure Conditions

Automatic analysis stops when:

- The APK is missing.
- `libil2cpp.so` is compressed.
- Il2CppDumper does not create `dump.cs`.
- A method signature changes.
- A branch exceeds the AArch64 `B` range.
- Original bytes do not match the manifest.
