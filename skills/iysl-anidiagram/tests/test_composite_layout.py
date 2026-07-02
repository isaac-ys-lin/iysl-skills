import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "render_animated_diagram.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_animated_diagram", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def composite_spec():
    return {
        "layout": "composite",
        "title": {"main": "Launch Story", "subtitle": "One page"},
        "canvas": {"width": 1210, "frames": 12, "fps": 10},
        "sections": [
            {
                "span": "full",
                "height": 400,
                "layout": "timeline",
                "title": "Rollout",
                "steps": [{"label": "Beta"}, {"label": "GA"}, {"label": "Scale"}],
            },
            {
                "span": "half",
                "height": 560,
                "layout": "funnel",
                "title": "Funnel",
                "stages": [{"label": "Visits", "value": "10k"}, {"label": "Paying", "value": "300"}],
            },
            {
                "span": "half",
                "height": 560,
                "layout": "stack",
                "title": "Stack",
                "layers": [{"label": "UI"}, {"label": "API"}, {"label": "Data"}],
            },
        ],
    }


class CompositeLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def render(self, spec):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        result = self.renderer.write_outputs(spec, Path(tmp.name), "page")
        return result

    def test_composite_contract_checks_pass(self):
        spec = composite_spec()
        result = self.render(spec)
        checks = self.renderer.check_outputs(result, spec)
        self.assertTrue(checks["ok"], checks)
        geom = self.renderer.composite_geometry(spec)
        with Image.open(result["png"]) as png:
            self.assertEqual(png.height, geom["height"])
            self.assertEqual(png.width, geom["width"])

    def test_composite_translates_section_elements_by_region_origin(self):
        spec = composite_spec()
        geom = self.renderer.composite_geometry(spec)
        rx, ry, rw, rh = [int(round(v)) for v in self.renderer.section_region(geom, 0)]
        sub = self.renderer.section_sub_spec(spec["sections"][0], spec, rw, rh)
        sub_ex, _ = self.renderer.LAYOUTS["timeline"].render(sub)
        standalone = [(e["type"], e["x"], e["y"]) for e in sub_ex.elements]

        page_ex, _ = self.renderer.render_composite(spec)
        s1 = [(e["type"], e["x"], e["y"]) for e in page_ex.elements if e["id"].startswith("s1-")]
        self.assertEqual(len(s1), len(standalone))
        for (kind_a, x_a, y_a), (kind_b, x_b, y_b) in zip(standalone, s1):
            self.assertEqual(kind_a, kind_b)
            self.assertAlmostEqual(x_a + rx, x_b, places=1)
            self.assertAlmostEqual(y_a + ry, y_b, places=1)

    def test_composite_ids_unique_and_indexes_monotonic_across_sections(self):
        spec = composite_spec()
        page_ex, _ = self.renderer.render_composite(spec)
        ids = [element["id"] for element in page_ex.elements]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any(element_id.startswith("s1-") for element_id in ids))
        self.assertTrue(any(element_id.startswith("s3-") for element_id in ids))
        indexes = [element["index"] for element in page_ex.elements]
        self.assertEqual(indexes, sorted(indexes))
        self.assertEqual(len(indexes), len(set(indexes)))

    def test_composite_validation_names_section_index(self):
        spec = composite_spec()
        del spec["sections"][1]["stages"]
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec(spec)
        joined = " ".join(ctx.exception.messages)
        self.assertIn("sections[1]", joined)
        self.assertIn("funnel", joined)

    def test_nested_composite_rejected(self):
        spec = composite_spec()
        spec["sections"].append({"layout": "composite", "sections": []})
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec(spec)
        self.assertIn("nested composite", " ".join(ctx.exception.messages))

    def test_composite_explicit_height_rejected(self):
        spec = composite_spec()
        spec["canvas"]["height"] = 2000
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec(spec)
        self.assertIn("canvas.height", " ".join(ctx.exception.messages))

    def test_composite_half_pairing_and_orphan_promotion(self):
        spec = composite_spec()
        for section in spec["sections"]:
            section["span"] = "half"
        geom = self.renderer.composite_geometry(spec)
        self.assertEqual(len(geom["rows"]), 2)
        self.assertEqual(len(geom["rows"][0]["cells"]), 2)
        self.assertEqual(len(geom["rows"][1]["cells"]), 1)
        full_w = geom["width"] - 2 * self.renderer.COMPOSITE_MARGIN
        self.assertEqual(geom["rows"][1]["cells"][0]["w"], full_w)

    def test_composite_motion_nonzero_across_slices(self):
        spec = composite_spec()
        result = self.render(spec)
        report = self.renderer.frame_diff_report(result["gif"])
        self.assertTrue(all(item["changed_pixels"] > 0 for item in report["diffs"]), report)
        with Image.open(result["png"]) as png:
            static = png.convert("RGB")
            slices = self.renderer.composite_time_slices(len(spec["sections"]), 12)
            with Image.open(result["gif"]) as gif:
                for start, _ in slices:
                    gif.seek(start)
                    frame = gif.convert("RGB")
                    self.assertIsNotNone(ImageChops.difference(static, frame).getbbox())

    def test_composite_ir_compiles_sections(self):
        raw = {
            "diagram_ir": {
                "claim": "Launch story",
                "relation": "composite",
                "sections": [
                    {
                        "relation": "sequence",
                        "claim": "Rollout",
                        "span": "full",
                        "nodes": [{"id": "a", "label": "Beta"}, {"id": "b", "label": "GA"}],
                    },
                    {
                        "relation": "funnel",
                        "claim": "Funnel",
                        "span": "half",
                        "nodes": [{"id": "v", "label": "Visits", "value": "10k"}],
                    },
                ],
            }
        }
        spec = self.renderer.normalize_render_input(raw)
        self.assertEqual(spec["layout"], "composite")
        self.assertEqual([section["layout"] for section in spec["sections"]], ["timeline", "funnel"])
        self.assertEqual(spec["sections"][1]["span"], "half")

    def test_composite_asset_spec_renders(self):
        spec = json.loads((ROOT / "assets" / "composite-spec.json").read_text(encoding="utf-8"))
        # write_outputs resolves the computed page height into spec["canvas"];
        # check_outputs must see that same resolved spec (as the CLI does)
        result = self.render(spec)
        checks = self.renderer.check_outputs(result, spec)
        self.assertTrue(checks["ok"], checks)

    def test_composite_min_region_guard(self):
        spec = composite_spec()
        # a full-width row keeps its own height, so 200px really is the region
        # height (half rows take the max of the pair and could mask the guard)
        spec["sections"][2] = {
            "span": "full",
            "height": 200,
            "layout": "circular_loop",
            "title": "Loop",
            "steps": [{"label": "a"}, {"label": "b"}],
        }
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec(spec)
        joined = " ".join(ctx.exception.messages)
        self.assertIn("sections[2]", joined)
        self.assertIn("below minimum", joined)


if __name__ == "__main__":
    unittest.main()
