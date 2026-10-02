"""Dependency-free checks for every bundled SVG renderer and CLI contract."""
import json
from decimal import Decimal
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parents[1]

def test_node_chart_suites():
    for script in ["basic-charts.test.js", "composition-charts.test.js", "statistical-charts.test.js", "render-chart.test.js"]:
        result = subprocess.run(["node", str(ROOT / "tests" / script)], text=True, capture_output=True)
        assert result.returncode == 0, result.stderr

def test_build_deck_suite():
    # PPTX assembly needs the pinned npm packages; install them with `npm ci --prefix scripts`.
    assert (ROOT / "scripts" / "node_modules" / "pptxgenjs").is_dir(), "run: npm ci --prefix skills/iysl-transglobe/scripts"
    result = subprocess.run(["node", str(ROOT / "tests" / "build-deck.test.js")], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr

def test_cli_preserves_input_metadata_and_writes_xml_svg():
    examples = json.loads((ROOT / "assets" / "chart-examples.json").read_text(encoding="utf-8"))["charts"]
    with tempfile.TemporaryDirectory() as directory:
        input_path, output_path = Path(directory) / "input.json", Path(directory) / "output.svg"
        for spec in examples.values():
            input_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(["node", str(ROOT / "scripts" / "render-chart.js"), str(input_path), str(output_path)], text=True, capture_output=True)
            assert result.returncode == 0, result.stderr
            root = ET.fromstring(output_path.read_text(encoding="utf-8"))
            metadata = next(node for node in root if node.tag.endswith("metadata"))
            assert json.loads(metadata.text) == spec
            assert spec["subtitle"] in "".join(root.itertext())

def test_cli_bare_prints_caption_lines():
    spec = json.loads((ROOT / "assets" / "chart-examples.json").read_text(encoding="utf-8"))["charts"]["waterfall"]
    with tempfile.TemporaryDirectory() as directory:
        input_path, output_path = Path(directory) / "input.json", Path(directory) / "output.svg"
        input_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(["node", str(ROOT / "scripts" / "render-chart.js"), str(input_path), str(output_path), "--bare"], text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
        assert spec["source"] in result.stdout and spec["unit"] in result.stdout
        root = ET.fromstring(output_path.read_text(encoding="utf-8"))
        visible = "".join(node.text or "" for node in root.iter() if node.tag.endswith("}text"))
        assert "資料來源" not in visible and spec["title"] not in visible, "bare SVG leaves title and footer to the page"

def test_gallery_uses_the_same_composition_data_for_three_questions():
    source = json.loads((ROOT / "assets" / "chart-examples.json").read_text(encoding="utf-8"))["charts"]["stacked"]
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run(["node", str(ROOT / "tests" / "make-gallery.js"), directory], check=True, capture_output=True)
        specs = {name: json.loads((Path(directory) / f"same-data-{name}.json").read_text(encoding="utf-8"))
                 for name in ["total-size", "within-channel", "size-and-composition"]}
        assert specs["total-size"]["data"] == [{"label": row["label"], "value": float(sum(Decimal(str(v)) for v in row["values"]))} for row in source["data"]]
        for name in ["within-channel", "size-and-composition"]:
            assert specs[name]["data"] == source["data"]
            assert specs[name]["categories"] == source["categories"]
        for spec in specs.values():
            assert spec["unit"] == source["unit"] and spec["period"] == source["period"]
            assert spec["sourceReference"]
