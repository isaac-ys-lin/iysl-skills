import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "render_animated_diagram.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_animated_diagram", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FontFallbackTest(unittest.TestCase):
    def setUp(self):
        self.renderer = load_renderer()

    def test_load_font_returns_default_when_no_candidates(self):
        self.renderer.font_candidates = lambda hand=False, cjk=False, bold=False: []
        self.renderer._FONT_PATH_CACHE.clear()
        font = self.renderer.load_font(16)
        self.assertIsNotNone(font)

    def test_load_font_skips_missing_paths(self):
        original = self.renderer.font_candidates
        self.renderer.font_candidates = lambda hand=False, cjk=False, bold=False: (
            ["/nonexistent/never-here.ttf"] + original(hand=hand, cjk=cjk, bold=bold)
        )
        self.renderer._FONT_PATH_CACHE.clear()
        font = self.renderer.load_font(16)
        self.assertIsNotNone(font)

    def test_font_path_probe_is_cached(self):
        calls = []
        original = self.renderer.font_candidates

        def counting(hand=False, cjk=False, bold=False):
            calls.append(1)
            return original(hand=hand, cjk=cjk, bold=bold)

        self.renderer.font_candidates = counting
        self.renderer._FONT_PATH_CACHE.clear()
        self.renderer.load_font(16)
        self.renderer.load_font(24)
        self.renderer.load_font(31)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
