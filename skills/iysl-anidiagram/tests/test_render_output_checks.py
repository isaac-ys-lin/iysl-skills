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


class RenderOutputChecksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_renderer()
        cls.spec = json.loads((ROOT / "assets" / "default-spec.json").read_text(encoding="utf-8"))

    def test_generated_outputs_pass_contract_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(self.spec, Path(tmp), "sample")

            checks = self.renderer.check_outputs(result, self.spec)

        self.assertTrue(checks["ok"], checks)

    def test_existing_render_spec_passes_through_normalization(self):
        spec = {
            "layout": "stack",
            "title": {"main": "Agent Layers", "subtitle": "Capability stack"},
            "layers": [
                {"label": "Interface", "body": "User request"},
                {"label": "Planner", "body": "Choose route"},
                {"label": "Renderer", "body": "Create outputs"},
            ],
        }

        self.assertEqual(self.renderer.normalize_render_input(spec), spec)

    def test_diagram_ir_compiles_sequence_to_timeline_spec(self):
        raw = {
            "diagram_ir": {
                "claim": "Launch Plan",
                "relation": "sequence",
                "layout_reason": "The source is a chronological release path.",
                "title": {"main": "Launch Plan", "subtitle": "Draft to release"},
                "nodes": [
                    {"id": "draft", "label": "Draft", "body": "Shape core message"},
                    {"id": "review", "label": "Review", "body": "Catch risk"},
                    {"id": "ship", "label": "Ship", "body": "Publish assets"},
                ],
            }
        }

        spec = self.renderer.normalize_render_input(raw)

        self.assertEqual(spec["layout"], "timeline")
        self.assertEqual([step["label"] for step in spec["steps"]], ["Draft", "Review", "Ship"])
        self.assertEqual(spec["title"]["main"], "Launch Plan")
        self.assertEqual(spec["layout_reason"], "The source is a chronological release path.")

    def test_diagram_ir_compiles_loop_to_circular_loop_spec(self):
        raw = {
            "diagram_ir": {
                "claim": "Metric Trap",
                "relation": "loop",
                "layout_reason": "The source describes a repeated reinforcing cycle.",
                "title": {"main": "Metric Trap", "subtitle": "Numbers improve, experience falls"},
                "nodes": [
                    {"id": "a", "label": "User asks"},
                    {"id": "b", "label": "Automation deflects"},
                    {"id": "c", "label": "Metric improves"},
                    {"id": "d", "label": "Automation expands"},
                ],
            }
        }

        spec = self.renderer.normalize_render_input(raw)

        self.assertEqual(spec["layout"], "circular_loop")
        self.assertEqual(
            [step["label"] for step in spec["steps"]],
            ["User asks", "Automation deflects", "Metric improves", "Automation expands"],
        )

    def test_diagram_ir_preserves_visual_design_atoms(self):
        raw = {
            "diagram_ir": {
                "claim": "Launch Plan",
                "relation": "sequence",
                "style": {"tone": "dark_technical"},
                "animation": {"marker": "arrow", "pulse": True},
                "finish": {"grain": False, "vignette": True, "soft_glow": True},
                "nodes": [
                    {"id": "draft", "label": "Draft"},
                    {"id": "ship", "label": "Ship"},
                ],
            }
        }

        spec = self.renderer.normalize_render_input(raw)

        self.assertEqual(spec["style"]["tone"], "dark_technical")
        self.assertEqual(spec["animation"]["marker"], "arrow")
        self.assertEqual(spec["finish"]["grain"], False)

    def test_diagram_ir_preserves_node_style_overrides(self):
        raw = {
            "diagram_ir": {
                "claim": "Launch Plan",
                "relation": "sequence",
                "nodes": [
                    {
                        "id": "draft",
                        "label": "Draft",
                        "style": {
                            "accent": "#c026d3",
                            "fill": "#fae8ff",
                            "stroke": "#e879f9",
                            "text": "#581c87",
                        },
                    },
                    {"id": "ship", "label": "Ship"},
                ],
            }
        }

        spec = self.renderer.normalize_render_input(raw)

        self.assertEqual(spec["steps"][0]["style"]["accent"], "#c026d3")
        self.assertEqual(spec["steps"][0]["style"]["fill"], "#fae8ff")
        self.assertEqual(spec["steps"][0]["style"]["stroke"], "#e879f9")
        self.assertEqual(spec["steps"][0]["style"]["text"], "#581c87")

    def test_light_layout_block_style_overrides_render_to_excalidraw(self):
        spec = {
            "layout": "timeline",
            "canvas": {"width": 900, "height": 640, "frames": 20, "fps": 20},
            "title": {"main": "Styled Blocks"},
            "steps": [
                {
                    "label": "Draft",
                    "body": "Shape core message",
                    "style": {
                        "accent": "#c026d3",
                        "fill": "#fae8ff",
                        "stroke": "#e879f9",
                        "text": "#581c87",
                        "muted": "#7e22ce",
                    },
                },
                {"label": "Ship", "body": "Publish assets"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "styled-blocks")
            checks = self.renderer.check_outputs(result, spec)
            excalidraw = json.loads(Path(result["excalidraw"]).read_text(encoding="utf-8"))

        self.assertTrue(checks["ok"], checks)
        elements = excalidraw["elements"]
        self.assertTrue(
            any(
                element.get("type") == "rectangle"
                and element.get("backgroundColor") == "#fae8ff"
                and element.get("strokeColor") == "#e879f9"
                for element in elements
            )
        )
        self.assertTrue(
            any(
                element.get("type") == "ellipse"
                and element.get("backgroundColor") == "#c026d3"
                and element.get("strokeColor") == "#c026d3"
                for element in elements
            )
        )
        self.assertTrue(any(element.get("text") == "Draft" and element.get("strokeColor") == "#581c87" for element in elements))
        self.assertTrue(
            any(element.get("text") == "Shape core message" and element.get("strokeColor") == "#7e22ce" for element in elements)
        )

    def test_before_after_block_style_overrides_render_to_excalidraw(self):
        spec = {
            "layout": "before_after",
            "canvas": {"width": 900, "height": 640, "frames": 20, "fps": 20},
            "title": {"main": "Styled Contrast"},
            "before": {
                "title": "Before",
                "items": ["Manual queue"],
                "style": {"accent": "#ef4444", "fill": "#fef2f2", "stroke": "#fca5a5", "text": "#7f1d1d"},
            },
            "after": {
                "title": "After",
                "items": ["Verified output"],
                "style": {"accent": "#16a34a", "fill": "#f0fdf4", "stroke": "#86efac", "text": "#14532d"},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "styled-contrast")
            checks = self.renderer.check_outputs(result, spec)
            excalidraw = json.loads(Path(result["excalidraw"]).read_text(encoding="utf-8"))

        self.assertTrue(checks["ok"], checks)
        elements = excalidraw["elements"]
        self.assertTrue(
            any(
                element.get("type") == "rectangle"
                and element.get("backgroundColor") == "#fef2f2"
                and element.get("strokeColor") == "#fca5a5"
                for element in elements
            )
        )
        self.assertTrue(
            any(
                element.get("type") == "rectangle"
                and element.get("backgroundColor") == "#f0fdf4"
                and element.get("strokeColor") == "#86efac"
                for element in elements
            )
        )
        self.assertTrue(any(element.get("text") == "Before" and element.get("strokeColor") == "#7f1d1d" for element in elements))
        self.assertTrue(any(element.get("text") == "After" and element.get("strokeColor") == "#14532d" for element in elements))

    def test_dark_technical_tone_changes_light_layout_background(self):
        spec = {
            "layout": "timeline",
            "style": {"tone": "dark_technical"},
            "canvas": {"width": 900, "height": 640, "frames": 20, "fps": 20},
            "title": {"main": "Product Path", "subtitle": "Need to governance"},
            "steps": [
                {"label": "Need", "body": "Customer gap"},
                {"label": "Gate", "body": "Risk review"},
                {"label": "Launch", "body": "Managed release"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "dark-timeline")
            checks = self.renderer.check_outputs(result, spec)
            excalidraw = json.loads(Path(result["excalidraw"]).read_text(encoding="utf-8"))

        self.assertTrue(checks["ok"], checks)
        self.assertEqual(excalidraw["appState"]["viewBackgroundColor"], "#000000")

    def test_timeline_cards_stay_inside_canvas_for_many_steps(self):
        spec = {
            "layout": "timeline",
            "canvas": {"width": 900, "height": 640, "frames": 20, "fps": 20},
            "title": {"main": "Many Steps"},
            "steps": [
                {"label": "One"},
                {"label": "Two"},
                {"label": "Three"},
                {"label": "Four"},
                {"label": "Five"},
                {"label": "Six"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "many-steps")
            excalidraw = json.loads(Path(result["excalidraw"]).read_text(encoding="utf-8"))

        rectangles = [element for element in excalidraw["elements"] if element.get("type") == "rectangle"]
        self.assertTrue(rectangles)
        for element in rectangles:
            self.assertGreaterEqual(element.get("x", 0), 0)
            self.assertLessEqual(element.get("x", 0) + element.get("width", 0), 900)

    def test_finish_options_have_defaults_and_overrides(self):
        light_options = self.renderer.finish_options({"layout": "timeline"})
        dark_options = self.renderer.finish_options({"layout": "timeline", "style": {"tone": "dark_technical"}})
        custom_options = self.renderer.finish_options(
            {
                "layout": "timeline",
                "style": {"tone": "dark_technical"},
                "finish": {"grain": False, "vignette": False, "soft_glow": False},
            }
        )

        self.assertEqual(light_options, {"grain": True, "vignette": False, "soft_glow": False})
        self.assertEqual(dark_options, {"grain": True, "vignette": True, "soft_glow": True})
        self.assertEqual(custom_options, {"grain": False, "vignette": False, "soft_glow": False})

    def test_contract_checks_report_invalid_excalidraw_font(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(self.spec, Path(tmp), "sample")
            excalidraw_path = Path(result["excalidraw"])
            excalidraw = json.loads(excalidraw_path.read_text(encoding="utf-8"))
            first_text = next(element for element in excalidraw["elements"] if element["type"] == "text")
            first_text["fontFamily"] = 1
            excalidraw_path.write_text(json.dumps(excalidraw), encoding="utf-8")

            checks = self.renderer.check_outputs(result, self.spec)

        self.assertFalse(checks["ok"])
        font_check = next(check for check in checks["checks"] if check["name"] == "excalidraw_text_font_family")
        self.assertFalse(font_check["ok"])

    def test_readability_reports_text_below_min_font_size(self):
        spec = {"layout": "timeline", "title": {"main": "Readable"}, "steps": [{"label": "One"}, {"label": "Two"}]}
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "sample")
            excalidraw_path = Path(result["excalidraw"])
            excalidraw = json.loads(excalidraw_path.read_text(encoding="utf-8"))
            first_text = next(element for element in excalidraw["elements"] if element["type"] == "text")
            first_text["fontSize"] = 5
            excalidraw_path.write_text(json.dumps(excalidraw), encoding="utf-8")
            checks = self.renderer.check_outputs(result, spec)

        item = next(check for check in checks["checks"] if check["name"] == "readability_min_font_size")
        self.assertFalse(checks["ok"])
        self.assertFalse(item["ok"])

    def test_readability_reports_text_outside_canvas_bounds(self):
        spec = {"layout": "timeline", "title": {"main": "Bounds"}, "steps": [{"label": "One"}, {"label": "Two"}]}
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "sample")
            excalidraw_path = Path(result["excalidraw"])
            excalidraw = json.loads(excalidraw_path.read_text(encoding="utf-8"))
            first_text = next(element for element in excalidraw["elements"] if element["type"] == "text")
            first_text["x"] = -100
            excalidraw_path.write_text(json.dumps(excalidraw), encoding="utf-8")
            checks = self.renderer.check_outputs(result, spec)

        item = next(check for check in checks["checks"] if check["name"] == "readability_text_within_canvas")
        self.assertFalse(checks["ok"])
        self.assertFalse(item["ok"])

    def test_circular_loop_layout_renders_numbered_cycle(self):
        spec = {
            "layout": "circular_loop",
            "canvas": {"width": 900, "height": 900, "frames": 28, "fps": 20},
            "palette": {
                "background": "#f3f7fc",
                "primary": "#2459c7",
                "muted": "#6b7890",
                "border": "#b8c8ee",
                "chip": "#dce8fb",
                "text": "#182032",
            },
            "title": {"main": "转移陷阱", "subtitle": "指标 ↑  体验 ↓"},
            "animation": {"mode": "orbit", "highlight_steps": True},
            "steps": [
                {"label": "用户遇到一个复杂问题", "badge": "入口"},
                {"label": "被推进自动化流程", "badge": "转移率 ↑"},
                {"label": "被迫一遍遍重复信息", "badge": "响应数 ↑"},
                {"label": "用户放弃，不再追问", "badge": "工单关闭 ↑"},
                {"label": "系统记下一次「高效响应」", "badge": "解决率 ↑"},
                {"label": "数字好看，公司加码自动化", "badge": "成本 ↓"},
                {"label": "下一个用户进同样的圈", "badge": "循环"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = self.renderer.write_outputs(spec, Path(tmp), "circular")
            checks = self.renderer.check_outputs(result, spec)
            diff_report = self.renderer.frame_diff_report(result["gif"])
            excalidraw = json.loads(Path(result["excalidraw"]).read_text(encoding="utf-8"))

        text_values = [element["text"] for element in excalidraw["elements"] if element.get("type") == "text"]
        self.assertTrue(checks["ok"], checks)
        self.assertEqual(excalidraw["appState"]["viewBackgroundColor"], "#f3f7fc")
        self.assertIn("转移陷阱", text_values)
        self.assertIn("指标 ↑  体验 ↓", text_values)
        for index in range(1, 8):
            self.assertIn(str(index), text_values)
        self.assertTrue(any(item["changed_pixels"] > 0 for item in diff_report["diffs"]), diff_report)

    def test_common_principled_layouts_render_contracts(self):
        cases = [
            (
                "timeline",
                {
                    "layout": "timeline",
                    "title": {"main": "Launch Plan", "subtitle": "From draft to release"},
                    "steps": [
                        {"label": "Draft", "body": "Shape core message"},
                        {"label": "Review", "body": "Catch risk"},
                        {"label": "Ship", "body": "Publish assets"},
                    ],
                },
                ["Launch Plan", "Draft", "Ship"],
            ),
            (
                "funnel",
                {
                    "layout": "funnel",
                    "title": {"main": "Support Funnel", "subtitle": "Where users drop"},
                    "stages": [
                        {"label": "Visits", "value": "10k"},
                        {"label": "Starts", "value": "3k"},
                        {"label": "Resolved", "value": "900"},
                    ],
                },
                ["Support Funnel", "Visits", "Resolved"],
            ),
            (
                "matrix",
                {
                    "layout": "matrix",
                    "title": {"main": "Priority Map", "subtitle": "Impact × effort"},
                    "x_axis": "Effort",
                    "y_axis": "Impact",
                    "items": [
                        {"label": "Quick win", "x": 0.25, "y": 0.78},
                        {"label": "Big bet", "x": 0.76, "y": 0.72},
                    ],
                },
                ["Priority Map", "Quick win", "Big bet"],
            ),
            (
                "stack",
                {
                    "layout": "stack",
                    "title": {"main": "Agent Layers", "subtitle": "Capability stack"},
                    "layers": [
                        {"label": "Interface", "body": "User request"},
                        {"label": "Planner", "body": "Choose route"},
                        {"label": "Renderer", "body": "Create outputs"},
                    ],
                },
                ["Agent Layers", "Interface", "Renderer"],
            ),
            (
                "before_after",
                {
                    "layout": "before_after",
                    "title": {"main": "Workflow Shift", "subtitle": "Manual to agentic"},
                    "before": {"title": "Before", "items": ["Manual sorting", "Lost context"]},
                    "after": {"title": "After", "items": ["Reusable memory", "Verified outputs"]},
                },
                ["Workflow Shift", "Before", "After", "Verified outputs"],
            ),
        ]

        for name, spec, expected_text in cases:
            with self.subTest(layout=name), tempfile.TemporaryDirectory() as tmp:
                spec["canvas"] = {"width": 900, "height": 700, "frames": 20, "fps": 20}
                result = self.renderer.write_outputs(spec, Path(tmp), name)
                checks = self.renderer.check_outputs(result, spec)
                diff_report = self.renderer.frame_diff_report(result["gif"])
                excalidraw = json.loads(Path(result["excalidraw"]).read_text(encoding="utf-8"))

            text_values = [element["text"] for element in excalidraw["elements"] if element.get("type") == "text"]
            self.assertTrue(checks["ok"], (name, checks))
            self.assertEqual(excalidraw["appState"]["viewBackgroundColor"], "#f3f7fc")
            for text in expected_text:
                self.assertIn(text, text_values)
            self.assertTrue(any(item["changed_pixels"] > 0 for item in diff_report["diffs"]), (name, diff_report))

    def test_architecture_element_census_stable(self):
        # behavior-preservation proxy for the legacy architecture layout:
        # element counts and the decision diamond position must not drift
        ex, _ = self.renderer.render_architecture(self.spec)
        counts = {}
        for element in ex.elements:
            counts[element["type"]] = counts.get(element["type"], 0) + 1
        self.assertEqual(len(ex.elements), 159)
        self.assertEqual(
            counts,
            {"text": 53, "line": 42, "rectangle": 36, "arrow": 14, "ellipse": 13, "diamond": 1},
        )
        diamond = next(element for element in ex.elements if element["type"] == "diamond")
        self.assertEqual((diamond["x"], diamond["y"]), (706, 508))


if __name__ == "__main__":
    unittest.main()
