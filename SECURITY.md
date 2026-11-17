# Security

## Local Tool Boundary

The tool uses a local ADB connection. It does not include a remote service.

The tool requires root access in the MuMu Android instance to copy the ARM64
plugin into the installed app directory and to load it with Frida.

## Data Handling

The tool reads:

- Installed package metadata
- The game process memory through Frida
- IL2CPP class and method metadata at runtime

The tool does not upload these files.

## Before You Report a Vulnerability

Include:

1. The affected command.
2. The game version and version code.
3. The exact error text.
4. The last lines of `pw3dmod.log`.

Do not attach paid content, account data, or proprietary game files.
