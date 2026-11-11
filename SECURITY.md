# Security

## Local Tool Boundary

The tool uses a local ADB connection. It does not include a remote service.

The tool requires root access in the MuMu Android instance to write to the
installed APK.

## Data Handling

The tool reads:

- Installed package metadata
- The installed `base.apk`
- The local TapTap APK
- IL2CPP metadata and native code

The tool does not upload these files.

## Before You Report a Vulnerability

Include:

1. The affected command.
2. The game version and APK size.
3. The exact error text.
4. Whether the tool changed the APK.

Do not attach paid content, account data, or proprietary game files.
