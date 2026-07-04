import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "render_animated_diagram.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_animated_diagram", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_by_name(checks, name):
    return next(check for check in checks["checks"] if check["name"] == name)


class PaintQualityChecksUnitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def run_checks(self, painted, spec=None, width=1000, height=800):
        return self.renderer.paint_quality_checks(painted, [], spec or {}, width, height)

    def test_empty_painted_texts_fail_presence(self):
        checks = self.run_checks([])
        presence = next(c for c in checks if c["name"] == "readability_painted_text_present")
        self.assertFalse(presence["ok"])

    def test_overlapping_texts_reported_as_collision(self):
        painted = [
            {"text": "alpha", "x": 100, "y": 100, "w": 80, "h": 20},
            {"text": "beta", "x": 150, "y": 105, "w": 80, "h": 20},
        ]
        collision = next(c for c in self.run_checks(painted) if c["name"] == "readability_text_collision")
        self.assertFalse(collision["ok"])
        self.assertEqual(collision["collisions"][0]["a"], "alpha")

    def test_adjacent_texts_within_tolerance_pass(self):
        painted = [
            {"text": "alpha", "x": 100, "y": 100, "w": 80, "h": 20},
            {"text": "beta", "x": 181, "y": 100, "w": 80, "h": 20},
        ]
        collision = next(c for c in self.run_checks(painted) if c["name"] == "readability_text_collision")
        self.assertTrue(collision["ok"])

    def test_text_outside_margin_reported(self):
        painted = [{"text": "edge", "x": 2, "y": 100, "w": 80, "h": 20}]
        margin = next(c for c in self.run_checks(painted) if c["name"] == "readability_canvas_margin")
        self.assertFalse(margin["ok"])
        self.assertIn("edge", margin["text_outside"])

    def test_shape_outside_margin_reported(self):
        painted = [{"text": "ok", "x": 100, "y": 100, "w": 80, "h": 20}]
        elements = [{"id": "rect-0001", "type": "rectangle", "x": 0, "y": 0, "width": 40, "height": 40}]
        checks = self.renderer.paint_quality_checks(painted, elements, {}, 1000, 800)
        margin = next(c for c in checks if c["name"] == "readability_canvas_margin")
        self.assertFalse(margin["ok"])
        self.assertIn("rect-0001", margin["shape_outside"])

    def test_quality_overrides_respected(self):
        painted = [{"text": "edge", "x": 2, "y": 100, "w": 80, "h": 20}]
        spec = {"quality": {"margin": 1}}
        margin = next(c for c in self.run_checks(painted, spec=spec) if c["name"] == "readability_canvas_margin")
        self.assertTrue(margin["ok"])


class PaintQualityChecksRenderTest(unittest.TestCase):
    """Negative fixtures proving the gate fires through the real render path."""

    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def render_and_check(self, spec):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "fixture")
            return self.renderer.check_outputs(result, spec)

    def test_colliding_matrix_labels_fail_check(self):
        spec = {
            "layout": "matrix",
            "canvas": {"width": 900, "height": 700, "frames": 4, "fps": 4},
            "title": {"main": "Collision Fixture"},
            "x_axis": "Effort",
            "y_axis": "Impact",
            "items": [
                {"label": "Deliberately overlapping label", "x": 0.5, "y": 0.5},
                {"label": "Deliberately overlapping label", "x": 0.5, "y": 0.5},
            ],
        }
        checks = self.render_and_check(spec)
        self.assertFalse(checks["ok"])
        self.assertFalse(check_by_name(checks, "readability_text_collision")["ok"])

    def test_absurd_margin_requirement_fails_check(self):
        spec = {
            "layout": "funnel",
            "canvas": {"width": 900, "height": 700, "frames": 4, "fps": 4},
            "quality": {"margin": 400},
            "title": {"main": "Margin Fixture"},
            "stages": [
                {"label": "Reached", "value": "10k"},
                {"label": "Kept", "value": "2k"},
            ],
        }
        checks = self.render_and_check(spec)
        self.assertFalse(checks["ok"])
        self.assertFalse(check_by_name(checks, "readability_canvas_margin")["ok"])

    def test_clean_spec_passes_new_checks(self):
        spec = {
            "layout": "funnel",
            "canvas": {"width": 900, "height": 700, "frames": 4, "fps": 4},
            "title": {"main": "Clean Fixture"},
            "stages": [
                {"label": "Reached", "value": "10k"},
                {"label": "Kept", "value": "2k"},
            ],
        }
        checks = self.render_and_check(spec)
        self.assertTrue(checks["ok"], checks)
        self.assertTrue(check_by_name(checks, "readability_painted_text_present")["ok"])


if __name__ == "__main__":
    unittest.main()
