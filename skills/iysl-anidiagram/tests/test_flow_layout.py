import importlib.util
import json
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


def flow_spec():
    return {
        "layout": "flow",
        "title": {"main": "Refund Flow", "subtitle": "Gate and retry"},
        "canvas": {"width": 1210, "height": 1000, "frames": 12, "fps": 20},
        "nodes": [
            {"id": "submit", "label": "Submit", "kind": "start"},
            {"id": "gate", "label": "Passes?", "kind": "decision"},
            {"id": "fix", "label": "Request evidence", "lane": "right"},
            {"id": "ship", "label": "Refund issued", "kind": "end"},
        ],
        "edges": [
            {"from": "submit", "to": "gate"},
            {"from": "gate", "to": "ship", "label": "yes"},
            {"from": "gate", "to": "fix", "label": "no"},
            {"from": "fix", "to": "submit", "kind": "retry"},
        ],
    }


class FlowLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()

    def test_flow_renders_contract_checks(self):
        spec = flow_spec()
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "flow")
            checks = self.renderer.check_outputs(result, spec)
            excalidraw = json.loads(Path(result["excalidraw"]).read_text(encoding="utf-8"))
        self.assertTrue(checks["ok"], checks)
        texts = {element.get("text") for element in excalidraw["elements"] if element.get("type") == "text"}
        self.assertIn("Submit", texts)
        self.assertIn("yes", texts)
        self.assertIn("no", texts)

    def test_flow_decision_and_retry_shapes_in_excalidraw(self):
        spec = flow_spec()
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "flow")
            excalidraw = json.loads(Path(result["excalidraw"]).read_text(encoding="utf-8"))
        types = [element["type"] for element in excalidraw["elements"]]
        self.assertIn("diamond", types)
        dashed = [
            element
            for element in excalidraw["elements"]
            if element["type"] in ("line", "arrow") and element.get("strokeStyle") == "dashed"
        ]
        self.assertTrue(dashed)

    def test_flow_gif_has_motion(self):
        spec = flow_spec()
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "flow")
            report = self.renderer.frame_diff_report(result["gif"])
        self.assertTrue(all(item["changed_pixels"] > 0 for item in report["diffs"]), report)

    def test_flow_ir_compiles_nodes_and_edges(self):
        raw = {
            "diagram_ir": {
                "claim": "Review gate",
                "relation": "branch",
                "nodes": [
                    {"id": "a", "label": "Start", "kind": "start"},
                    {"id": "b", "label": "Check?", "kind": "decision"},
                    {"id": "c", "label": "Done", "kind": "end"},
                ],
                "edges": [
                    {"from": "a", "to": "b"},
                    {"from": "b", "to": "c", "label": "yes"},
                ],
            }
        }
        spec = self.renderer.normalize_render_input(raw)
        self.assertEqual(spec["layout"], "flow")
        self.assertEqual([node["id"] for node in spec["nodes"]], ["a", "b", "c"])
        self.assertEqual(spec["edges"][1]["label"], "yes")

    def test_flow_ir_without_edges_builds_chain(self):
        raw = {
            "diagram_ir": {
                "claim": "Steps",
                "relation": "flow",
                "nodes": [
                    {"id": "a", "label": "One"},
                    {"id": "b", "label": "Two"},
                ],
            }
        }
        spec = self.renderer.normalize_render_input(raw)
        self.assertEqual(spec["layout"], "flow")
        self.assertNotIn("edges", spec)
        geom = self.renderer.flow_geometry(spec, 1210, 1000)
        self.assertEqual([edge["from"] for edge in geom["edges"]], ["a"])

    def test_flow_edge_to_unknown_node_raises(self):
        spec = flow_spec()
        spec["edges"].append({"from": "gate", "to": "ghost"})
        with self.assertRaises(self.renderer.SpecValidationError) as ctx:
            self.renderer.validate_spec(spec)
        self.assertIn("ghost", " ".join(ctx.exception.messages))

    def test_flow_asset_spec_renders(self):
        spec = json.loads((ROOT / "assets" / "flow-spec.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "flow-asset")
            checks = self.renderer.check_outputs(result, spec)
        self.assertTrue(checks["ok"], checks)


if __name__ == "__main__":
    unittest.main()
