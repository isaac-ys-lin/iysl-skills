import importlib.util
import json
import subprocess
import sys
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


class SpecValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def test_unknown_layout_raises_with_supported_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(self.renderer.SpecValidationError) as ctx:
                self.renderer.write_outputs({"layout": "flowchart", "steps": [{"label": "a"}]}, Path(tmp), "bad")
        joined = " ".join(ctx.exception.messages)
        self.assertIn("flowchart", joined)
        self.assertIn("flow", joined)
        self.assertIn("timeline", joined)

    def test_missing_layout_architecture_shaped_resolves(self):
        spec = json.loads((ROOT / "assets" / "default-spec.json").read_text(encoding="utf-8"))
        self.assertNotIn("layout", spec)
        self.assertEqual(self.renderer.resolve_layout(spec), "architecture")

    def test_missing_layout_unshaped_spec_raises(self):
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.resolve_layout({"title": {"main": "x"}, "steps": [{"label": "a"}]})
        self.assertIn("architecture-shaped", " ".join(ctx.exception.messages))

    def test_missing_required_fields_names_layout_and_fields(self):
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec({"layout": "funnel", "title": {"main": "x"}})
        joined = " ".join(ctx.exception.messages)
        self.assertIn("funnel", joined)
        self.assertIn("stages", joined)

    def test_registry_dispatch_covers_all_documented_layouts(self):
        expected = {
            "circular_loop",
            "timeline",
            "funnel",
            "ranking",
            "matrix",
            "stack",
            "before_after",
            "flow",
            "composite",
            "architecture",
        }
        self.assertEqual(set(self.renderer.LAYOUTS), expected)
        for name, entry in self.renderer.LAYOUTS.items():
            self.assertTrue(callable(entry.render), name)
            if entry.kind == "light" and name != "composite":
                self.assertTrue(entry.animate is not None or entry.pulse_targets is not None, name)

    def test_ir_relation_map_generated_from_registry(self):
        self.assertEqual(self.renderer.IR_RELATION_LAYOUTS["loop"], "circular_loop")
        self.assertEqual(self.renderer.IR_RELATION_LAYOUTS["branch"], "flow")
        self.assertEqual(self.renderer.IR_RELATION_LAYOUTS["story"], "composite")
        self.assertEqual(self.renderer.IR_RELATION_LAYOUTS["ranking"], "ranking")
        self.assertEqual(self.renderer.IR_RELATION_LAYOUTS["magnitude"], "ranking")

    def test_ranking_requires_labels_and_nonnegative_numeric_values(self):
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec(
                {
                    "layout": "ranking",
                    "items": [
                        {"label": "", "value": 10},
                        {"label": "ok", "value": -3},
                        {"label": "also ok", "value": "many"},
                    ],
                }
            )
        joined = " ".join(ctx.exception.messages)
        self.assertIn("items[0] needs a non-empty 'label'", joined)
        self.assertIn("items[1].value must be a non-negative number", joined)
        self.assertIn("items[2].value must be a non-negative number", joined)

    def test_ranking_requires_one_positive_value(self):
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec(
                {"layout": "ranking", "items": [{"label": "a", "value": 0}, {"label": "b", "value": 0}]}
            )
        self.assertIn("at least one item with value > 0", " ".join(ctx.exception.messages))

    def test_quality_must_be_an_object_with_nonnegative_numeric_knobs(self):
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec({"layout": "funnel", "stages": [{"label": "a"}], "quality": "loose"})
        self.assertIn("quality must be an object", " ".join(ctx.exception.messages))
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec(
                {"layout": "funnel", "stages": [{"label": "a"}], "quality": {"margin": -4}}
            )
        self.assertIn("quality.margin must be a non-negative number", " ".join(ctx.exception.messages))

    def test_ranking_sorts_descending_by_default_and_respects_sort_none(self):
        spec = {"items": [{"label": "small", "value": 1}, {"label": "big", "value": 9}]}
        self.assertEqual([item["label"] for item in self.renderer.ranking_items(spec)], ["big", "small"])
        spec["sort"] = "none"
        self.assertEqual([item["label"] for item in self.renderer.ranking_items(spec)], ["small", "big"])

    def test_cli_exits_2_on_invalid_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps({"layout": "nope"}), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--spec", str(bad), "--outdir", tmp],
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "spec_validation_failed")
        self.assertTrue(payload["messages"])

    def test_flow_node_items_must_be_objects(self):
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec({"layout": "flow", "nodes": ["bad-node"]})
        self.assertIn("nodes[0] must be an object", " ".join(ctx.exception.messages))

    def test_cli_exits_2_for_invalid_flow_node_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad-flow.json"
            bad.write_text(json.dumps({"layout": "flow", "nodes": ["bad-node"]}), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(MODULE_PATH), "--spec", str(bad), "--outdir", tmp],
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["error"], "spec_validation_failed")
        self.assertIn("nodes[0] must be an object", " ".join(payload["messages"]))


if __name__ == "__main__":
    unittest.main()
