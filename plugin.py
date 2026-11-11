from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import time
import zipfile


ROOT = Path(__file__).resolve().parent
MUMU_ROOT = Path(
    os.environ.get(
        "MUMU_ROOT",
        r"D:\TapTap\Support\android_emulator",
    )
)
ADB = MUMU_ROOT / "engine" / "nx_main" / "adb.exe"
SEVEN_ZIP = MUMU_ROOT / "engine" / "tools" / "7z1602" / "x64" / "7za.exe"
DEVICE = os.environ.get("MUMU_ADB", "127.0.0.1:16416")
PACKAGE = "com.puzzle.miniworld.cn"
ACTIVITY = f"{PACKAGE}/com.puzzle.miniworld.UnityPlayerActivity"
LIB_ENTRY = "lib/arm64-v8a/libil2cpp.so"
MANIFEST_PATH = ROOT / "patch_manifest.json"
STATE_DIR = ROOT / "state"
CACHE_DIR = ROOT / "cache"
DUMPER = ROOT / "tools" / "il2cppdumper" / "Il2CppDumper.exe"


def run(
    arguments: list[str],
    *,
    check: bool = True,
    capture_output: bool = True,
    stdout=None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        check=check,
        text=True,
        capture_output=capture_output,
        stdout=stdout,
        timeout=timeout,
    )


def adb(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(
        [str(ADB), "-s", DEVICE, *arguments],
        check=check,
        capture_output=True,
    )


def adb_shell(command: str, *, check: bool = True) -> str:
    return adb("shell", command, check=check).stdout.strip()


def connect_device(*, require_root: bool) -> None:
    if not ADB.exists():
        raise FileNotFoundError(f"ADB was not found: {ADB}")
    run([str(ADB), "connect", DEVICE], check=False, capture_output=True)
    try:
        run(
            [str(ADB), "-s", DEVICE, "wait-for-device"],
            timeout=6,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("MuMu ADB device is not available") from error
    identity = adb("shell", "id").stdout
    if require_root and "uid=0(root)" not in identity:
        adb("root", check=False)
        time.sleep(2)
        run([str(ADB), "connect", DEVICE], check=False, capture_output=True)
        identity = adb("shell", "id").stdout
    if require_root and "uid=0(root)" not in identity:
        raise RuntimeError(
            "ADB root is not available. Run enable-root-mode.ps1 once."
        )


def installed_package() -> dict[str, object]:
    dump = adb("shell", "dumpsys", "package", PACKAGE).stdout
    version_name = re.search(r"versionName=(\S+)", dump)
    version_code = re.search(r"versionCode=(\d+)", dump)
    if version_name is None or version_code is None:
        raise RuntimeError("Could not read the installed game version")

    path_output = adb("shell", "pm", "path", PACKAGE).stdout.strip()
    if not path_output.startswith("package:"):
        raise RuntimeError("Could not locate the installed game APK")
    remote_apk = path_output.removeprefix("package:").splitlines()[0]
    remote_size = int(
        adb_shell(f"stat -c %s {remote_apk}").splitlines()[-1]
    )
    return {
        "versionName": version_name.group(1),
        "versionCode": int(version_code.group(1)),
        "remoteApk": remote_apk,
        "apkSize": remote_size,
    }


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"package": PACKAGE, "versions": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def find_local_apk(apk_size: int) -> Path | None:
    roots = [
        MUMU_ROOT / "games",
        MUMU_ROOT.parent / "games",
    ]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("*/apk/*.apk"):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if path.stat().st_size == apk_size:
                return path
    return None


def pull_remote_apk(remote_apk: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        subprocess.run(
            [str(ADB), "-s", DEVICE, "exec-out", "cat", remote_apk],
            check=True,
            stdout=stream,
        )


def class_section(source: str, class_name: str) -> str:
    start = re.search(
        rf"^public class {re.escape(class_name)}(?:\s|:|$)",
        source,
        flags=re.MULTILINE,
    )
    if start is None:
        raise RuntimeError(f"Class was not found: {class_name}")
    next_class = re.search(
        r"^(?:public |private |internal |protected )?(?:sealed )?class ",
        source[start.end() :],
        flags=re.MULTILINE,
    )
    end = start.end() + next_class.start() if next_class else len(source)
    return source[start.start() : end]


def method_file_offset(section: str, signature: str) -> int:
    match = re.search(signature, section, flags=re.MULTILINE)
    if match is None:
        raise RuntimeError(f"Method was not found: {signature}")
    offsets = list(
        re.finditer(
            r"// RVA: 0x[0-9A-Fa-f]+ Offset: (0x[0-9A-Fa-f]+) VA:",
            section[: match.start()],
        )
    )
    if not offsets:
        raise RuntimeError(f"Method offset was not found: {signature}")
    return int(offsets[-1].group(1), 16)


def branch_bytes(source: int, target: int) -> bytes:
    displacement = target - source
    if displacement % 4 != 0 or not -(1 << 27) <= displacement < (1 << 27):
        raise RuntimeError("The branch target is outside the AArch64 B range")
    instruction = 0x14000000 | ((displacement >> 2) & 0x03FFFFFF)
    return struct.pack("<I", instruction)


def zip_library_data_offset(apk_path: Path) -> int:
    with zipfile.ZipFile(apk_path) as archive:
        info = archive.getinfo(LIB_ENTRY)
        if info.compress_type != zipfile.ZIP_STORED:
            raise RuntimeError("libil2cpp.so is compressed; in-place patching is unsafe")
        with apk_path.open("rb") as stream:
            stream.seek(info.header_offset)
            header = stream.read(30)
        values = struct.unpack("<IHHHHHIIIHH", header)
        name_length = values[-2]
        extra_length = values[-1]
        return info.header_offset + 30 + name_length + extra_length


def analyze_version(package: dict[str, object], apk_path: Path) -> dict:
    version_name = str(package["versionName"])
    cache = CACHE_DIR / version_name
    input_dir = cache / "input"
    dump_dir = cache / "dump"
    input_dir.mkdir(parents=True, exist_ok=True)
    dump_dir.mkdir(parents=True, exist_ok=True)

    if not SEVEN_ZIP.exists():
        raise FileNotFoundError(f"7za.exe was not found: {SEVEN_ZIP}")
    if not DUMPER.exists():
        raise FileNotFoundError(f"Il2CppDumper was not found: {DUMPER}")

    run(
        [
            str(SEVEN_ZIP),
            "x",
            "-y",
            str(apk_path),
            f"-o{input_dir}",
            LIB_ENTRY,
            r"assets\bin\Data\Managed\Metadata\global-metadata.dat",
        ]
    )
    libil2cpp = input_dir / "lib" / "arm64-v8a" / "libil2cpp.so"
    metadata = (
        input_dir
        / "assets"
        / "bin"
        / "Data"
        / "Managed"
        / "Metadata"
        / "global-metadata.dat"
    )
    run(
        [str(DUMPER), str(libil2cpp), str(metadata), str(dump_dir)],
        check=False,
    )
    dump_file = dump_dir / "dump.cs"
    if not dump_file.exists():
        raise RuntimeError("Il2CppDumper did not create dump.cs")

    source = dump_file.read_text(encoding="utf-8", errors="replace")
    battle_panel = class_section(source, "battlePanel")
    auto_finish_offset = method_file_offset(
        battle_panel,
        r"^\s*public void AutoFinishBtnClick\(\)",
    )
    tip_offset = method_file_offset(
        battle_panel,
        r"^\s*public virtual void TipBtnCallBack\(\)",
    )
    target_offset = method_file_offset(
        battle_panel,
        r"^\s*private void <ShowAutoFinishPropDialog>b__\d+_1\("
        r"CostGoodsCallBackData data\)",
    )

    library = libil2cpp.read_bytes()
    data_offset = zip_library_data_offset(apk_path)
    patches = []
    for name, file_offset in [
        ("AutoFinishBtnClick", auto_finish_offset),
        ("TipBtnCallBack", tip_offset),
    ]:
        expected = library[file_offset : file_offset + 4]
        replace = branch_bytes(file_offset, target_offset)
        patches.append(
            {
                "name": name,
                "fileOffset": file_offset,
                "absoluteOffset": data_offset + file_offset,
                "expected": expected.hex(),
                "replace": replace.hex(),
            }
        )

    entry = {
        "versionName": version_name,
        "versionCode": int(package["versionCode"]),
        "apkSize": int(package["apkSize"]),
        "libEntry": LIB_ENTRY,
        "dataOffset": data_offset,
        "targetFileOffset": target_offset,
        "patches": patches,
    }
    manifest = load_manifest()
    manifest.setdefault("versions", {})[version_name] = entry
    save_manifest(manifest)
    return entry


def get_version_entry(package: dict[str, object], *, auto_analyze: bool) -> dict:
    manifest = load_manifest()
    existing = manifest.get("versions", {}).get(package["versionName"])
    if (
        existing
        and int(existing.get("versionCode", -1)) == int(package["versionCode"])
        and int(existing.get("apkSize", -1)) == int(package["apkSize"])
    ):
        return existing

    if not auto_analyze:
        raise RuntimeError(
            f"Unsupported version {package['versionName']} "
            f"({package['versionCode']}, {package['apkSize']} bytes)"
        )

    apk_path = find_local_apk(int(package["apkSize"]))
    if apk_path is None:
        apk_path = CACHE_DIR / f"base-{package['versionCode']}.apk"
        if not apk_path.exists():
            pull_remote_apk(str(package["remoteApk"]), apk_path)
    return analyze_version(package, apk_path)


def remote_hex(remote_apk: str, offset: int) -> str:
    output = adb_shell(
        f"dd if={remote_apk} bs=1 skip={offset} count=4 2>/dev/null "
        "| od -An -tx1"
    )
    return "".join(output.split())


def apply_patch(entry: dict, *, launch_after: bool) -> dict:
    package = installed_package()
    remote_apk = str(package["remoteApk"])
    if int(package["apkSize"]) != int(entry["apkSize"]):
        raise RuntimeError("The installed APK changed after the patch was prepared")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path = STATE_DIR / f"{entry['versionName']}.json"
    state = {
        "versionName": entry["versionName"],
        "versionCode": entry["versionCode"],
        "apkSize": entry["apkSize"],
        "remoteApk": remote_apk,
        "patches": [],
    }

    adb("shell", "am", "force-stop", PACKAGE)
    for patch in entry["patches"]:
        absolute_offset = int(patch["absoluteOffset"])
        current = remote_hex(remote_apk, absolute_offset)
        expected = str(patch["expected"])
        replace = str(patch["replace"])
        if current == replace:
            original = expected
        elif current == expected:
            original = current
            with tempfile.NamedTemporaryFile(
                prefix="pocket-world-patch-",
                suffix=".bin",
                delete=False,
            ) as stream:
                stream.write(bytes.fromhex(replace))
                local_patch = Path(stream.name)
            remote_patch = f"/data/local/tmp/{patch['name']}.bin"
            try:
                adb("push", str(local_patch), remote_patch)
                adb(
                    "shell",
                    f"dd if={remote_patch} of={remote_apk} "
                    f"bs=1 seek={absolute_offset} count=4 conv=notrunc "
                    "2>/dev/null",
                )
            finally:
                local_patch.unlink(missing_ok=True)
        else:
            raise RuntimeError(
                f"Unexpected bytes at {patch['name']}: {current}"
            )

        verified = remote_hex(remote_apk, absolute_offset)
        if verified != replace:
            raise RuntimeError(f"Patch verification failed: {patch['name']}")
        state["patches"].append(
            {
                "name": patch["name"],
                "absoluteOffset": absolute_offset,
                "original": original,
                "patched": replace,
            }
        )

    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if launch_after:
        adb("shell", "am", "start", "-n", ACTIVITY)
    return state


def restore_patch(version_name: str) -> dict:
    state_path = STATE_DIR / f"{version_name}.json"
    if not state_path.exists():
        raise FileNotFoundError(f"No saved patch state: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    package = installed_package()
    remote_apk = str(package["remoteApk"])
    if int(package["apkSize"]) != int(state["apkSize"]):
        raise RuntimeError("The installed APK changed; restore is not safe")

    adb("shell", "am", "force-stop", PACKAGE)
    for patch in state["patches"]:
        with tempfile.NamedTemporaryFile(
            prefix="pocket-world-restore-",
            suffix=".bin",
            delete=False,
        ) as stream:
            stream.write(bytes.fromhex(patch["original"]))
            local_patch = Path(stream.name)
        remote_patch = f"/data/local/tmp/restore-{patch['name']}.bin"
        try:
            adb("push", str(local_patch), remote_patch)
            adb(
                "shell",
                f"dd if={remote_patch} of={remote_apk} "
                f"bs=1 seek={patch['absoluteOffset']} count=4 conv=notrunc "
                "2>/dev/null",
            )
        finally:
            local_patch.unlink(missing_ok=True)
    return state


def self_test() -> int:
    manifest = load_manifest()
    checked = 0
    for version_name, entry in manifest.get("versions", {}).items():
        apk_path = find_local_apk(int(entry["apkSize"]))
        if apk_path is None:
            print(f"{version_name}: local APK not found; skipped")
            continue
        data_offset = zip_library_data_offset(apk_path)
        if data_offset != int(entry["dataOffset"]):
            raise RuntimeError(f"{version_name}: ZIP data offset changed")
        with apk_path.open("rb") as stream:
            for patch in entry["patches"]:
                stream.seek(int(patch["absoluteOffset"]))
                actual = stream.read(4).hex()
                if actual != patch["expected"]:
                    raise RuntimeError(
                        f"{version_name} {patch['name']}: "
                        f"expected {patch['expected']}, got {actual}"
                    )
                branch = branch_bytes(
                    int(patch["fileOffset"]),
                    int(entry["targetFileOffset"]),
                ).hex()
                if branch != patch["replace"]:
                    raise RuntimeError(
                        f"{version_name} {patch['name']}: branch mismatch"
                    )
        print(f"{version_name}: OK")
        checked += 1
    if checked == 0:
        raise RuntimeError("No local APK matched the patch manifest")
    return checked


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Patch the game's existing auto-finish callback."
    )
    parser.add_argument(
        "action",
        choices=["auto", "detect", "apply", "restore", "analyze", "selftest"],
        nargs="?",
        default="auto",
    )
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--no-auto-analyze", action="store_true")
    args = parser.parse_args()

    if args.action == "selftest":
        count = self_test()
        print(f"selftest passed for {count} version(s)")
        return

    connect_device(
        require_root=args.action in {"auto", "apply", "restore", "analyze"}
    )
    package = installed_package()
    print(
        f"installed version={package['versionName']} "
        f"code={package['versionCode']} size={package['apkSize']}"
    )

    if args.action == "detect":
        manifest = load_manifest()
        supported = package["versionName"] in manifest.get("versions", {})
        print(f"supported={str(supported).lower()}")
        return

    if args.action == "restore":
        state = restore_patch(str(package["versionName"]))
        print(f"restored {len(state['patches'])} patches")
        return

    entry = get_version_entry(
        package,
        auto_analyze=not args.no_auto_analyze,
    )
    print(
        f"patch prepared for version={entry['versionName']} "
        f"target=0x{entry['targetFileOffset']:X}"
    )
    if args.action in {"auto", "apply"}:
        state = apply_patch(entry, launch_after=args.launch)
        print(f"applied {len(state['patches'])} patches")
    elif args.action == "analyze":
        print("patch manifest updated")


if __name__ == "__main__":
    main()
