"""Demo artifacts must stay reproducible from their tracked SVG source."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "render_svg.py"
DEMOS = SKILL_DIR / "demos"
CASES = {
    "bitter-lesson": 30,
    "survivorship-bias": 30,
    "survivorship-bias-chalkboard": 10,
}
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


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


def video_ssim(fresh, tracked):
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
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["ok"] is True

    assert sha256(tmp_path / f"{demo_name}.png") == sha256(demo / f"{demo_name}.png")
    assert video_ssim(
        tmp_path / f"{demo_name}.mp4",
        demo / f"{demo_name}.mp4",
    ) >= 0.999
