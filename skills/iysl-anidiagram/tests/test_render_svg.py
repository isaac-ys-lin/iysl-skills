"""Tests for scripts/render_svg.py (animated SVG -> MP4/PNG toolchain).

Structural validation tests never need a browser and always run.
Browser-dependent tests skip when playwright + a launchable Chrome/Chromium
are unavailable.
"""

import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "render_svg.py"
SAMPLE_SVG = SKILL_DIR / "assets" / "svg-sample.svg"
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"

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
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180)


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
        assert any("active_content_forbidden" in m for m in report["messages"])

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

    @pytest.mark.parametrize(
        "animation, expected",
        [
            (
                '<animate attributeName="cx" values="120;280;120" keyTimes="0;0.5;1" '
                'keySplines="0.23 1 0.32 1;0.23 1 0.32 1" dur="3s"/>',
                "spline_calc_mode_missing",
            ),
            (
                '<animate attributeName="cx" values="120;280;120" keyTimes="0;0.5;1" '
                'calcMode="spline" dur="3s"/>',
                "spline_key_splines_missing",
            ),
            (
                '<animate attributeName="cx" values="120;280;120" keyTimes="0;0.5;1" '
                'calcMode="spline" keySplines="0.23 1 0.32 1" dur="3s"/>',
                "spline_count_invalid",
            ),
            (
                '<animate attributeName="cx" values="120;280;120" keyTimes="0;0.5;1" '
                'calcMode="spline" keySplines="0.23 1 1.2 1;0.23 1 0.32 1" dur="3s"/>',
                "spline_control_point_invalid",
            ),
            (
                '<animate attributeName="cx" values="120;280;120" keyTimes="0;0.5;1" '
                'calcMode="spline" keySplines="NaN 0 1 1;0.23 1 0.32 1" dur="3s"/>',
                "spline_control_point_invalid",
            ),
            (
                '<animate attributeName="cx" values="120;280;120" keyTimes="0;banana;1" '
                'calcMode="spline" keySplines="0.23 1 0.32 1;0.23 1 0.32 1" dur="3s"/>',
                "spline_key_times_invalid",
            ),
            (
                '<animate attributeName="cx" values="120;280;120" keyTimes="0;1.2;1" '
                'calcMode="spline" keySplines="0.23 1 0.32 1;0.23 1 0.32 1" dur="3s"/>',
                "spline_key_times_invalid",
            ),
            (
                '<animate attributeName="cx" values="120;;280" keyTimes="0;;1" '
                'calcMode="spline" keySplines="0.23 1 0.32 1;0.23 1 0.32 1" dur="3s"/>',
                "spline_empty_stop_invalid",
            ),
        ],
    )
    def test_rejects_incomplete_or_invalid_spline(self, animation, expected):
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import render_svg

            bad = VALID_MINIMAL_SVG.replace(
                '<animate attributeName="cx" values="120;280;120" dur="3s" repeatCount="indefinite"/>',
                animation,
            )
            messages, _ = render_svg.validate_structure(bad)
        finally:
            sys.path.remove(str(SCRIPT.parent))
        assert any(expected in message for message in messages)

    @pytest.mark.parametrize(
        "payload",
        [
            '<g onload="document.body.dataset.pwned=1"><text x="10" y="20">x</text></g>',
            '<foreignObject x="0" y="0" width="10" height="10"><div xmlns="http://www.w3.org/1999/xhtml">x</div></foreignObject>',
            '<iframe href="data:text/html,x"/>',
            '<img src="https://example.invalid/probe.png"/>',
            '<image href="data:image/png;base64,AA=="><set attributeName="href" to="https://example.invalid/set.png" begin="0s"/></image>',
            '<rect x="0" y="0" width="10" height="10" fill="url(https://example.invalid/fill.svg#p)"/>',
            '<rect x="0" y="0" width="10" height="10" filter="url(https://example.invalid/filter.svg#f)"/>',
            '<image href="data:image/png;base64,AA=="><set attributeName="xlink:href" to="https://example.invalid/xlink.png" begin="0s"/></image>',
            r'<rect x="0" y="0" width="10" height="10" fill="u\72l(https://example.invalid/escaped.svg#p)"/>',
            r'<style>@\69mport "https://example.invalid/escaped-import.css";</style>',
            '<g style="background-image:image-set(\'https://example.invalid/imageset-attr.png\' 1x)"><text x="10" y="20">x</text></g>',
            '<style>svg { background-image:image-set("https://example.invalid/imageset-block.png" 1x); }</style>',
        ],
    )
    def test_rejects_active_svg_content(self, payload):
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import render_svg

            bad = VALID_MINIMAL_SVG.replace("</svg>", payload + "</svg>")
            messages, _ = render_svg.validate_structure(bad)
        finally:
            sys.path.remove(str(SCRIPT.parent))
        assert any("active_content_forbidden" in message for message in messages)

    def test_motion_warning_does_not_count_invalid_splines_as_eased(self):
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import render_svg

            invalid = "".join(
                '<animate attributeName="opacity" values="0;1" '
                'keySplines="0.23 1 0.32 1" dur="3s"/>'
                for _ in range(6)
            )
            svg = VALID_MINIMAL_SVG.replace("</svg>", invalid + "</svg>")
            warnings = render_svg.scan_motion_warnings(svg)
        finally:
            sys.path.remove(str(SCRIPT.parent))
        assert any("motion_mostly_linear" in warning for warning in warnings)

    def test_accepts_valid_spline_and_explicit_linear_motion(self):
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import render_svg

            valid = VALID_MINIMAL_SVG.replace(
                '<animate attributeName="cx" values="120;280;120" dur="3s" repeatCount="indefinite"/>',
                '<animate attributeName="cx" values="120;280;120" keyTimes="0;0.5;1" '
                'calcMode="spline" keySplines="0.77 0 0.175 1;0.77 0 0.175 1" '
                'dur="3s" repeatCount="indefinite"/>',
            )
            messages, _ = render_svg.validate_structure(valid)
        finally:
            sys.path.remove(str(SCRIPT.parent))
        assert messages == []

    def test_render_lock_serializes_processes(self, tmp_path):
        lock_path = tmp_path / "renderer.lock"
        ready = tmp_path / "ready"
        entered = tmp_path / "entered"
        code = f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(SCRIPT.parent)!r})
import render_svg
Path({str(ready)!r}).write_text('ready')
with render_svg.exclusive_render_lock(Path({str(lock_path)!r})):
    Path({str(entered)!r}).write_text('entered')
"""
        import fcntl

        process = None
        try:
            with lock_path.open("a+") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                process = subprocess.Popen([sys.executable, "-c", code])
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                assert ready.exists(), "child did not reach the render lock"
                assert not entered.exists(), "child entered while the render lock was held"
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            assert process.wait(timeout=5) == 0
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
        assert entered.exists()

    def test_render_lock_times_out(self, tmp_path):
        import fcntl

        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import render_svg

            lock_path = tmp_path / "renderer-timeout.lock"
            with lock_path.open("a+") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                with pytest.raises(TimeoutError):
                    with render_svg.exclusive_render_lock(lock_path, timeout=0.05):
                        pass
        finally:
            sys.path.remove(str(SCRIPT.parent))

    def test_sample_hides_open_path_motion_at_loop_seam(self):
        root = ET.parse(SAMPLE_SVG).getroot()
        motion_parent = next(
            element
            for element in root.iter()
            if any(child.tag.rsplit("}", 1)[-1] == "animateMotion" for child in element)
        )
        opacity = next(
            child
            for child in motion_parent
            if child.tag.rsplit("}", 1)[-1] == "animate"
            and child.get("attributeName") == "opacity"
        )
        values = [value.strip() for value in opacity.get("values", "").split(";")]
        key_times = [value.strip() for value in opacity.get("keyTimes", "").split(";")]
        assert key_times[-1] == "1"
        assert values[-2:] == ["0", "0"]


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
                "motion_nonzero", "loop_position_seam", "external_resource_runtime",
                "output_mp4", "output_png"} <= check_names

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

    def test_visible_open_motion_path_fails_loop_seam(self, browser_available, tmp_path):
        bad = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200"
     data-loop-seconds="2" font-family="{CJK_FONT_STACK}">
  <rect width="400" height="200" fill="#ffffff"/>
  <text x="200" y="50" text-anchor="middle" font-size="24">可見跳點</text>
  <path id="open" d="M 40 120 L 360 120" fill="none"/>
  <circle r="8" fill="#2459c7">
    <animateMotion dur="2s" repeatCount="indefinite"><mpath href="#open"/></animateMotion>
  </circle>
</svg>"""
        svg_path = tmp_path / "open-path.svg"
        svg_path.write_text(bad, encoding="utf-8")
        result = run_cli(
            svg_path,
            tmp_path / "open-path-out",
            basename="open-path",
            extra_args=["--fps", "10"],
        )
        assert result.returncode == 1, result.stdout + result.stderr
        report = json.loads(result.stdout)
        seam = next(check for check in report["checks"] if check["name"] == "loop_position_seam")
        assert seam["ok"] is False

    def test_visible_finite_motion_fails_loop_seam(self, browser_available, tmp_path):
        bad = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200"
     data-loop-seconds="2" font-family="{CJK_FONT_STACK}">
  <rect width="400" height="200" fill="#ffffff"/>
  <text x="200" y="50" text-anchor="middle" font-size="24">有限動畫跳點</text>
  <circle cx="40" cy="120" r="8" fill="#2459c7">
    <animate attributeName="cx" values="40;360" dur="2s" fill="freeze"/>
  </circle>
</svg>"""
        svg_path = tmp_path / "finite-motion.svg"
        svg_path.write_text(bad, encoding="utf-8")
        result = run_cli(
            svg_path,
            tmp_path / "finite-motion-out",
            basename="finite-motion",
            extra_args=["--fps", "10"],
        )
        assert result.returncode == 1, result.stdout + result.stderr
        report = json.loads(result.stdout)
        seam = next(check for check in report["checks"] if check["name"] == "loop_position_seam")
        assert seam["ok"] is False

    def test_hidden_motion_does_not_fail_loop_seam(self, browser_available, tmp_path):
        hidden = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200"
     data-loop-seconds="2" font-family="{CJK_FONT_STACK}">
  <rect width="400" height="200" fill="#ffffff"/>
  <text x="200" y="50" text-anchor="middle" font-size="24">隱藏動畫</text>
  <path id="hidden-open" d="M 40 120 L 360 120" fill="none"/>
  <circle r="8" fill="#2459c7" visibility="hidden">
    <animateMotion dur="2s" repeatCount="indefinite"><mpath href="#hidden-open"/></animateMotion>
  </circle>
  <circle cx="40" cy="160" r="5" fill="#2459c7">
    <animate attributeName="cx" values="40;60;40" dur="2s" repeatCount="indefinite"/>
  </circle>
</svg>"""
        svg_path = tmp_path / "hidden-motion.svg"
        svg_path.write_text(hidden, encoding="utf-8")
        result = run_cli(
            svg_path,
            tmp_path / "hidden-motion-out",
            basename="hidden-motion",
            extra_args=["--fps", "10"],
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def test_parallel_renders_are_pixel_deterministic(self, browser_available, tmp_path):
        from concurrent.futures import ThreadPoolExecutor

        def render(name):
            return run_cli(
                SAMPLE_SVG,
                tmp_path / name,
                basename=name,
                extra_args=["--fps", "5"],
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(render, ("parallel-a", "parallel-b")))
        for result in results:
            assert result.returncode == 0, result.stdout + result.stderr

        def frame_md5(path):
            result = subprocess.run(
                [
                FFMPEG,
                    "-v", "error",
                    "-i", str(path),
                    "-f", "framemd5",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, result.stderr
            return "\n".join(
                line for line in result.stdout.splitlines() if not line.startswith("#")
            )

        assert frame_md5(tmp_path / "parallel-a" / "parallel-a.mp4") == frame_md5(
            tmp_path / "parallel-b" / "parallel-b.mp4"
        )
