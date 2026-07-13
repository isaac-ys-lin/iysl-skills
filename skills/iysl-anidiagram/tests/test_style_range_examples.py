"""Style-range contract tests.

The showcase is a judgment asset, not a template library. These tests keep its
documented houses discoverable and ensure every SVG continues to pass the same
render contract as a production deliverable.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "render_svg.py"
STYLE_RANGE = SKILL_DIR / "examples" / "style-range"
EXPECTED_DIRECTIONS = {"editorial", "blueprint", "print"}


def style_range_svgs():
    return sorted(STYLE_RANGE.glob("*/diagram.svg"))


def direction_id(svg_path):
    return svg_path.parent.name


def normalized_image_difference(left_path, right_path):
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")
    assert left.size == right.size
    difference = ImageChops.difference(left, right)
    return sum(ImageStat.Stat(difference).mean) / (3 * 255)


def test_style_range_has_documented_directions_and_posters():
    found = {direction_id(path) for path in style_range_svgs()}
    assert found == EXPECTED_DIRECTIONS
    assert (STYLE_RANGE / "README.md").exists()
    fingerprints = {}
    for direction in EXPECTED_DIRECTIONS:
        poster = STYLE_RANGE / direction / "poster.png"
        fingerprint = STYLE_RANGE / direction / "fingerprint.json"
        assert poster.exists(), f"{direction} has no poster.png"
        assert poster.stat().st_size > 0, f"{direction}/poster.png is empty"
        data = json.loads(fingerprint.read_text(encoding="utf-8"))
        assert data["visual"], f"{direction} has no visual fingerprint"
        assert data["spatial"], f"{direction} has no spatial fingerprint"
        fingerprints[direction] = data

    directions = sorted(EXPECTED_DIRECTIONS)
    for index, left in enumerate(directions):
        for right in directions[index + 1:]:
            assert fingerprints[left]["visual"] != fingerprints[right]["visual"]
            assert fingerprints[left]["spatial"] != fingerprints[right]["spatial"]


def test_style_range_posters_are_visibly_distinct():
    directions = sorted(EXPECTED_DIRECTIONS)
    for index, left in enumerate(directions):
        for right in directions[index + 1:]:
            difference = normalized_image_difference(
                STYLE_RANGE / left / "poster.png",
                STYLE_RANGE / right / "poster.png",
            )
            assert difference > 0.03, (
                f"{left} and {right} posters are too similar "
                f"(normalized difference {difference:.4f})"
            )


@pytest.mark.parametrize("svg_path", style_range_svgs(), ids=direction_id)
def test_style_range_diagram_passes_check(svg_path, tmp_path):
    basename = f"style-range-{direction_id(svg_path)}"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--svg",
            str(svg_path),
            "--outdir",
            str(tmp_path),
            "--basename",
            basename,
            "--fps",
            "10",
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{direction_id(svg_path)} failed render_svg.py --check "
        f"(exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
    )
    report = json.loads(result.stdout)
    assert report["ok"] is True
    fresh_poster = tmp_path / f"{basename}.png"
    assert fresh_poster.stat().st_size > 0
    assert (tmp_path / f"{basename}.mp4").stat().st_size > 0
    tracked_poster = svg_path.parent / "poster.png"
    difference = normalized_image_difference(tracked_poster, fresh_poster)
    assert difference < 0.02, (
        f"{direction_id(svg_path)}/poster.png is stale "
        f"(normalized difference {difference:.4f})"
    )
