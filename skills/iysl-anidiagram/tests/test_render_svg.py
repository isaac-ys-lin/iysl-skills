"""Tests for scripts/render_svg.py (animated SVG -> MP4/PNG toolchain).

Structural validation tests never need a browser and always run.
Browser-dependent tests skip when playwright + a launchable Chrome/Chromium
are unavailable.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "render_svg.py"
SAMPLE_SVG = SKILL_DIR / "assets" / "svg-sample.svg"

CJK_FONT_STACK = "'PingFang TC', 'Noto Sans TC', 'Helvetica Neue', Arial, sans-serif"

VALID_MINIMAL_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300"
     data-loop-seconds="3" font-family="{CJK_FONT_STACK}">
  <rect width="400" height="300" fill="#ffffff"/>
  <text x="200" y="60" text-anchor="middle" font-size="24" fill="#182032">標題</text>
  <circle cx="200" cy="180" r="20" fill="#2459c7">
    <animate attributeName="cx" values="120;280;120" dur="3s" repeatCount="indefinite"/>
  </circle>
</svg>
"""


def run_cli(svg_path, outdir, basename="out", extra_args=()):
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--svg", str(svg_path),
        "--outdir", str(outdir),
        "--basename", basename,
        "--check",
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def run_structure(tmp_path, svg_text):
    svg_path = tmp_path / "input.svg"
    svg_path.write_text(svg_text, encoding="utf-8")
    result = run_cli(svg_path, tmp_path / "out")
    return result, json.loads(result.stdout)


@pytest.fixture(scope="session")
def browser_available():
    """Probe playwright plus a launchable Chrome/Chromium once per session."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright is not installed")
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome")
            except Exception:
                browser = p.chromium.launch()
            browser.close()
    except Exception as err:
        pytest.skip(f"no launchable Chrome/Chromium: {err}")
    return True


class TestStructureValidation:
    """Stage (a): exit 2 plus a messages list. No browser required."""

    def test_valid_minimal_svg_passes_structure(self):
        # Assert the validator accepts a well-formed document via the module API;
        # the full passing path through the CLI is covered by TestFullPipeline.
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import render_svg
            messages, meta = render_svg.validate_structure(VALID_MINIMAL_SVG)
        finally:
            sys.path.remove(str(SCRIPT.parent))
        assert messages == []
        assert meta["loop_seconds"] == 3.0
        assert meta["width"] == 400.0
        assert meta["height"] == 300.0

    def test_rejects_script_element(self, tmp_path):
        bad = VALID_MINIMAL_SVG.replace(
            "</svg>", "<script>alert(1)</script></svg>"
        )
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert report["ok"] is False
        assert any("script" in m for m in report["messages"])

    def test_rejects_css_keyframes(self, tmp_path):
        bad = VALID_MINIMAL_SVG.replace(
            "<rect",
            "<style>@keyframes spin { to { transform: rotate(360deg); } }</style><rect",
        )
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert any("css_animation" in m for m in report["messages"])

    def test_rejects_css_animation_in_style_attribute(self, tmp_path):
        bad = VALID_MINIMAL_SVG.replace(
            '<circle cx="200"',
            '<circle style="animation: spin 2s linear infinite" cx="200"',
        )
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert any("css_animation" in m for m in report["messages"])

    def test_rejects_missing_loop_seconds(self, tmp_path):
        bad = VALID_MINIMAL_SVG.replace(' data-loop-seconds="3"', "")
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert any("data-loop-seconds" in m for m in report["messages"])

    def test_rejects_loop_seconds_out_of_range(self, tmp_path):
        bad = VALID_MINIMAL_SVG.replace('data-loop-seconds="3"', 'data-loop-seconds="60"')
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert any("data-loop-seconds_out_of_range" in m for m in report["messages"])

    def test_rejects_external_image_href(self, tmp_path):
        bad = VALID_MINIMAL_SVG.replace(
            "</svg>",
            '<image href="https://example.com/x.png" width="10" height="10"/></svg>',
        )
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert any("image_external_href_forbidden" in m for m in report["messages"])

    def test_rejects_missing_viewbox(self, tmp_path):
        bad = VALID_MINIMAL_SVG.replace(' viewBox="0 0 400 300"', "")
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert any("viewbox" in m for m in report["messages"])

    def test_rejects_missing_text_and_cjk_stack(self, tmp_path):
        bad = VALID_MINIMAL_SVG.replace(
            '<text x="200" y="60" text-anchor="middle" font-size="24" fill="#182032">標題</text>',
            "",
        ).replace(CJK_FONT_STACK, "Arial, sans-serif")
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert any("text_missing" in m for m in report["messages"])
        assert any("cjk_font_fallback_missing" in m for m in report["messages"])

    def test_reports_all_problems_at_once(self, tmp_path):
        bad = (
            VALID_MINIMAL_SVG
            .replace(' data-loop-seconds="3"', "")
            .replace("</svg>", "<script>x()</script></svg>")
        )
        result, report = run_structure(tmp_path, bad)
        assert result.returncode == 2
        assert len(report["messages"]) >= 2


class TestFullPipeline:
    """Stages (b)+(c) against the repo sample. Requires a browser."""

    def test_sample_svg_renders_end_to_end(self, browser_available, tmp_path):
        outdir = tmp_path / "out"
        result = run_cli(SAMPLE_SVG, outdir, basename="sample", extra_args=["--fps", "10"])
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        assert report["ok"] is True

        mp4 = outdir / "sample.mp4"
        png = outdir / "sample.png"
        assert mp4.exists() and mp4.stat().st_size > 0
        assert png.exists() and png.stat().st_size > 0

        probe = subprocess.run(
            [
                "/opt/homebrew/bin/ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-show_entries", "format=duration",
                "-of", "json", str(mp4),
            ],
            capture_output=True, text=True,
        )
        info = json.loads(probe.stdout)
        width = int(info["streams"][0]["width"])
        height = int(info["streams"][0]["height"])
        duration = float(info["format"]["duration"])
        assert width % 2 == 0 and height % 2 == 0
        # sample declares data-loop-seconds="4"; 40 frames at 10 fps = 4.0s
        assert abs(duration - 4.0) < 0.2

        check_names = {check["name"] for check in report["checks"]}
        assert {"readability_text_collision", "readability_canvas_margin",
                "motion_nonzero", "output_mp4", "output_png"} <= check_names

    def test_text_collision_fails_quality_gate(self, browser_available, tmp_path):
        bad = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200"
     data-loop-seconds="2" font-family="{CJK_FONT_STACK}">
  <rect width="400" height="200" fill="#ffffff"/>
  <text x="200" y="100" text-anchor="middle" font-size="24" fill="#111111">重疊文字甲</text>
  <text x="205" y="104" text-anchor="middle" font-size="24" fill="#333333">重疊文字乙</text>
  <circle cx="60" cy="160" r="10" fill="#2459c7">
    <animate attributeName="cx" values="60;340;60" dur="2s" repeatCount="indefinite"/>
  </circle>
</svg>
"""
        svg_path = tmp_path / "collision.svg"
        svg_path.write_text(bad, encoding="utf-8")
        result = run_cli(svg_path, tmp_path / "out", basename="collision",
                         extra_args=["--fps", "10"])
        assert result.returncode == 1, result.stdout + result.stderr
        report = json.loads(result.stdout)
        assert report["ok"] is False
        collision = next(
            check for check in report["checks"]
            if check["name"] == "readability_text_collision"
        )
        assert collision["ok"] is False
        assert "重疊文字甲" in collision["detail"] or "重疊文字乙" in collision["detail"]
