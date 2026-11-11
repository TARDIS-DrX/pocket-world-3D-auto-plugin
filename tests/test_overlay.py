from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("quick_assembly_overlay", ROOT / "overlay.py")
OVERLAY = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(OVERLAY)


class HintDetectionTests(unittest.TestCase):
    def test_template_is_found(self) -> None:
        template_path = ROOT / "assets" / "hint_windmill.png"
        with Image.open(template_path).convert("RGB") as template:
            canvas = Image.new("RGB", (900, 1600), (247, 242, 235))
            canvas.paste(template, (804, 190))
            match = OVERLAY.detect_hint_button(canvas)
        self.assertIsNotNone(match)
        score, position = match
        self.assertGreater(score, OVERLAY.MATCH_THRESHOLD)
        self.assertEqual(position, (804 + template.width // 2, 190 + template.height // 2))

    def test_blank_page_is_rejected(self) -> None:
        canvas = Image.new("RGB", (900, 1600), (247, 242, 235))
        self.assertIsNone(OVERLAY.detect_hint_button(canvas))


if __name__ == "__main__":
    unittest.main()
