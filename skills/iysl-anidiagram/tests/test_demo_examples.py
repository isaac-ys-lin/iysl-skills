"""Demo artifacts must stay reproducible from their tracked SVG source."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "render_svg.py"
DEMOS = SKILL_DIR / "demos"
CASES = {
    "bitter-lesson": 30,
    "how-complex-systems-fail": 30,
    "survivorship-bias": 30,
    "survivorship-bias-chalkboard": 10,
}
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
DEMO_RENDER_TIMEOUT = 360  # 180s global-lock budget plus rendering/encoding time.
MIN_ARTIFACT_SSIM = 0.99
CANONICAL_RENDER = os.environ.get(
    "IYSL_CANONICAL_RENDER",
    "1" if sys.platform == "darwin" else "0",
) == "1"


@pytest.fixture(scope="session")
def browser_available():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.fail("playwright is required to verify tracked demo artifacts")
    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(channel="chrome")
            except Exception:
                browser = playwright.chromium.launch()
            browser.close()
    except Exception as error:
        pytest.fail(f"no launchable Chrome/Chromium: {error}")
    return True


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def media_ssim(fresh, tracked):
    result = subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel", "info",
            "-i", str(fresh),
            "-i", str(tracked),
            "-lavfi", "ssim",
            "-f", "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    match = re.search(r"All:([0-9.]+)", result.stderr)
    assert match, f"ffmpeg did not report SSIM: {result.stderr[-500:]}"
    return float(match.group(1))


def video_metadata(path):
    result = subprocess.run(
        [
            FFPROBE,
            "-v", "error",
            "-count_frames",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,nb_read_frames:format=duration",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": Fraction(stream["r_frame_rate"]),
        "frames": int(stream["nb_read_frames"]),
        "duration": float(payload["format"]["duration"]),
    }


def assert_same_video_contract(fresh, tracked):
    fresh_metadata = video_metadata(fresh)
    tracked_metadata = video_metadata(tracked)
    for field in ("width", "height", "fps", "frames"):
        assert fresh_metadata[field] == tracked_metadata[field], (
            f"{field} differs: fresh={fresh_metadata[field]}, "
            f"tracked={tracked_metadata[field]}"
        )
    frame_duration = 1 / float(tracked_metadata["fps"])
    assert abs(fresh_metadata["duration"] - tracked_metadata["duration"]) <= frame_duration


@pytest.mark.parametrize("demo_name", CASES)
def test_demo_artifacts_are_fresh(browser_available, demo_name, tmp_path):
    demo = DEMOS / demo_name
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--svg", str(demo / "diagram.svg"),
            "--outdir", str(tmp_path),
            "--basename", demo_name,
            "--fps", str(CASES[demo_name]),
            "--check",
        ],
        capture_output=True,
        text=True,
        timeout=DEMO_RENDER_TIMEOUT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["ok"] is True

    fresh_png = tmp_path / f"{demo_name}.png"
    tracked_png = demo / f"{demo_name}.png"
    if CANONICAL_RENDER:
        assert sha256(fresh_png) == sha256(tracked_png)
        minimum_ssim = 0.999
    else:
        minimum_ssim = MIN_ARTIFACT_SSIM

    assert_same_video_contract(
        tmp_path / f"{demo_name}.mp4",
        demo / f"{demo_name}.mp4",
    )
    for extension in ("png", "mp4"):
        score = media_ssim(
            tmp_path / f"{demo_name}.{extension}",
            demo / f"{demo_name}.{extension}",
        )
        assert score >= minimum_ssim, (
            f"{demo_name}.{extension} SSIM {score:.6f} "
            f"is below {minimum_ssim:.3f}"
        )
