# Third-Party Notices

## Frida

This project loads the plugin with Frida at runtime.

- Project: `frida/frida`
- Source: https://github.com/frida/frida
- Runtime requirement: `frida` Python package and `frida-server` on the Android device.

The repository does not claim ownership of Frida. Refer to the upstream
project for license terms.

## Frida Java Bridge

`work/frida-agent/bundle.js` is a bundled build of the Frida Java bridge used
to call `java.lang.Runtime.load0`.

- Project: `frida/frida-java-bridge`
- Source: https://github.com/frida/frida-java-bridge

## Android Bionic Stubs

`work/tools/libc_arm64.so` and `work/tools/libdl_arm64.so` are used only as
link-time stubs for the ARM64 build.

- Project: Android Open Source Project
- Source: https://android.googlesource.com/platform/bionic/
- License: Apache License 2.0
