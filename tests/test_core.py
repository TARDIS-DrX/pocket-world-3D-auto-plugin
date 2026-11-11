from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("quick_assembly_plugin", ROOT / "plugin.py")
PLUGIN = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(PLUGIN)


class BranchTests(unittest.TestCase):
    def test_forward_branch(self) -> None:
        encoded = PLUGIN.branch_bytes(0x1000, 0x1024)
        instruction = struct.unpack("<I", encoded)[0]
        self.assertEqual(instruction >> 26, 0b000101)
        self.assertEqual((instruction & 0x03FFFFFF) << 2, 0x24)

    def test_backward_branch(self) -> None:
        encoded = PLUGIN.branch_bytes(0x2000, 0x1FF0)
        instruction = struct.unpack("<I", encoded)[0]
        displacement = (instruction & 0x03FFFFFF) << 2
        self.assertEqual(displacement, 0xFFFFFF0)

    def test_unaligned_target_fails(self) -> None:
        with self.assertRaises(RuntimeError):
            PLUGIN.branch_bytes(0x1000, 0x1002)


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(
            (ROOT / "patch_manifest.json").read_text(encoding="utf-8")
        )

    def test_manifest_package(self) -> None:
        self.assertEqual(self.manifest["package"], "com.puzzle.miniworld.cn")
        self.assertTrue(self.manifest["versions"])

    def test_patch_entries_are_complete(self) -> None:
        required = {
            "name",
            "fileOffset",
            "absoluteOffset",
            "expected",
            "replace",
        }
        for version, entry in self.manifest["versions"].items():
            self.assertEqual(entry["versionName"], version)
            self.assertEqual(len(entry["patches"]), 2)
            for patch in entry["patches"]:
                self.assertTrue(required.issubset(patch))
                self.assertEqual(len(patch["expected"]), 8)
                self.assertEqual(len(patch["replace"]), 8)

    def test_saved_branch_matches_file_offset(self) -> None:
        for entry in self.manifest["versions"].values():
            for patch in entry["patches"]:
                expected = PLUGIN.branch_bytes(
                    int(patch["fileOffset"]),
                    int(entry["targetFileOffset"]),
                ).hex()
                self.assertEqual(expected, patch["replace"])


if __name__ == "__main__":
    unittest.main()
