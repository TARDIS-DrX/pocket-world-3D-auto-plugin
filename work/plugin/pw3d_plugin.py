# -*- coding: utf-8 -*-
"""Pocket World 3D plugin control tool.

Flow:
  Frida (x64) -> Java Runtime.load0 -> ARM64 libpw3dmod.so
  libpw3dmod worker -> reads pw3d.cmd -> main-thread action via GameManager.Update

Usage:
  python work/plugin/pw3d_plugin.py deploy
  python work/plugin/pw3d_plugin.py ensure
  python work/plugin/pw3d_plugin.py cmd auto
  python work/plugin/pw3d_plugin.py cmd free:1
  python work/plugin/pw3d_plugin.py cmd free:0
  python work/plugin/pw3d_plugin.py cmd ads:1
  python work/plugin/pw3d_plugin.py cmd vip:1
  python work/plugin/pw3d_plugin.py cmd theme
  python work/plugin/pw3d_plugin.py auto
  python work/plugin/pw3d_plugin.py log
  python work/plugin/pw3d_plugin.py hotkey
"""
import ctypes
import ctypes.wintypes
import json
import os
import re
import subprocess
import sys
import time

import frida

PACKAGE = "com.puzzle.miniworld.cn"
ADB = os.environ.get(
    "PW3D_ADB",
    r"D:\TapTap\Support\android_emulator\engine\nx_device\12.0\shell\adb.exe",
)
DEVICE = os.environ.get("PW3D_DEVICE", "127.0.0.1:16416")
FILES = "/sdcard/Android/data/com.puzzle.miniworld.cn/files"
TRIGGER = FILES + "/auto.trigger"
LOG = FILES + "/pw3dmod.log"
CMD = FILES + "/pw3d.cmd"
RESULT = FILES + "/pw3d.result"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(ROOT, "work", "plugin", "libpw3dmod.so")
BUNDLE = os.path.join(ROOT, "work", "frida-agent", "bundle.js")


def adb(*args, check=False):
    command = [ADB, "-s", DEVICE] + list(args)
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def shell(command, root=False, check=False):
    if root:
        command = "su -c " + json.dumps(command)
    return adb("shell", command, check=check)


def app_pid():
    result = shell("pidof " + PACKAGE)
    match = re.search(r"\d+", result.stdout)
    return int(match.group(0)) if match else None


def start_app():
    shell("am start -n %s/com.puzzle.miniworld.UnityPlayerActivity" % PACKAGE)
    for _ in range(20):
        pid = app_pid()
        if pid:
            return pid
        time.sleep(1)
    raise RuntimeError("game process not found")


def ensure_frida():
    result = shell("ps -A | grep -i frida | grep -v grep", root=True)
    if "frida-server" not in result.stdout:
        shell(
            "nohup /data/local/tmp/frida-server-x86_64 -l 0.0.0.0:27042 "
            ">/data/local/tmp/fs.log 2>&1 &",
            root=True,
        )
        time.sleep(3)


def native_lib_dir():
    result = shell("pm path " + PACKAGE, check=True)
    line = result.stdout.strip().splitlines()[0]
    apk = line.split(":", 1)[1]
    base_dir = os.path.dirname(apk)
    return base_dir + "/lib/arm64"


def deploy():
    if not os.path.exists(LIB):
        raise SystemExit("missing " + LIB)
    adb("push", LIB, "/data/local/tmp/libpw3dmod.so", check=True)
    lib_dir = native_lib_dir()
    target = lib_dir + "/libpw3dmod.so"
    shell(
        "cp /data/local/tmp/libpw3dmod.so '%s'; "
        "chown system:system '%s'; chmod 644 '%s'; restorecon '%s'"
        % (target, target, target, target),
        root=True,
        check=True,
    )
    print("deployed:", target)
    return target


def load():
    ensure_frida()
    pid = app_pid() or start_app()
    target = native_lib_dir() + "/libpw3dmod.so"
    with open(BUNDLE, "r", encoding="utf-8") as handle:
        bundle = handle.read()
    tail = r"""
setTimeout(function () {
    Java.perform(function () {
        try {
            var Runtime = Java.use('java.lang.Runtime');
            var Activity = Java.use('com.puzzle.miniworld.UnityPlayerActivity');
            Runtime.getRuntime().load0(Activity.class, __LIB__);
            send({stage: 'loaded'});
        } catch (e) {
            var text = String(e);
            if (text.indexOf('already loaded') !== -1) {
                send({stage: 'loaded', already: true});
            } else {
                send({stage: 'load_error', error: text});
            }
        }
    });
}, 100);
""".replace("__LIB__", json.dumps(target))

    try:
        device = frida.get_usb_device(timeout=10)
    except Exception:
        device = frida.get_device("127.0.0.1:27042", timeout=10)
    session = device.attach(pid)
    messages = []

    def on_message(message, data):
        messages.append(message)
        print(json.dumps(message, ensure_ascii=False))

    script = session.create_script(bundle + tail)
    script.on("message", on_message)
    script.load()
    deadline = time.time() + 15
    while time.time() < deadline:
        if any(m.get("payload", {}).get("stage") in ("loaded", "load_error") for m in messages):
            break
        time.sleep(0.2)
    session.detach()
    ok = any(m.get("payload", {}).get("stage") == "loaded" for m in messages)
    if not ok:
        raise SystemExit("load failed; see messages above")


def trigger():
    shell(
        "printf 'auto' > '%s'; chown 10042:10042 '%s'" % (TRIGGER, TRIGGER),
        root=True,
        check=True,
    )
    print("triggered")
    time.sleep(1.2)
    print(log_tail())


def log_tail(lines=20):
    result = shell("cat '%s' 2>/dev/null" % LOG, root=True)
    rows = result.stdout.strip().splitlines()
    return "\n".join(rows[-lines:])


def app_uid():
    result = shell("stat -c %%u '%s'" % FILES, root=True)
    match = re.search(r"\d+", result.stdout)
    return match.group(0) if match else "10042"


def send_cmd(command, timeout=12.0):
    uid = app_uid()
    shell("rm -f '%s'" % RESULT, root=True)
    shell(
        "printf '%%s' '%s' > '%s'; chown %s:%s '%s'"
        % (command, CMD, uid, uid, CMD),
        root=True,
        check=True,
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        text = shell("cat '%s' 2>/dev/null" % RESULT, root=True).stdout.strip()
        if text:
            return text
        time.sleep(0.25)
    return "timeout"


def ensure():
    deploy()
    if send_cmd("status", timeout=3.0) != "timeout":
        return
    load()
    send_cmd("status", timeout=10.0)


def hotkey():
    user32 = ctypes.windll.user32
    VK_F8 = 0x77
    MOD_NOREPEAT = 0x4000
    if not user32.RegisterHotKey(None, 1, MOD_NOREPEAT, VK_F8):
        raise SystemExit("F8 is already registered")
    print("plugin ready: focus the game and press F8 to auto-assemble; Ctrl+C to exit")
    try:
        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312:
                try:
                    trigger()
                except Exception as exc:
                    print("trigger failed:", exc)
    finally:
        user32.UnregisterHotKey(None, 1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    command = sys.argv[1]
    if command == "deploy":
        deploy()
    elif command == "load":
        load()
    elif command == "ensure":
        ensure()
        print("ready")
    elif command == "cmd":
        if len(sys.argv) < 3:
            raise SystemExit("usage: pw3d_plugin.py cmd <auto|free:0|free:1|ads:0|ads:1|vip:0|vip:1|theme>")
        print(send_cmd(sys.argv[2]))
    elif command == "auto":
        print(send_cmd("auto"))
    elif command == "run":
        deploy()
        load()
        print(send_cmd("auto"))
    elif command == "log":
        print(log_tail(50))
    elif command == "hotkey":
        hotkey()
    else:
        raise SystemExit("unknown command: " + command)


if __name__ == "__main__":
    main()
