"""Verify tracked demo integrity and cross-platform render contracts."""

import hashlib
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest
from PIL import Image


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "render_svg.py"
DEMOS = SKILL_DIR / "demos"
MANIFEST = json.loads((DEMOS / "artifact-manifest.json").read_text(encoding="utf-8"))
CASES = {
    "bitter-lesson": 30,
    "how-complex-systems-fail": 30,
    "survivorship-bias": 30,
    "survivorship-bias-chalkboard": 10,
}
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
DEMO_RENDER_TIMEOUT = 360  # 180s global-lock budget plus rendering/encoding time.


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


def normalized_text_sha256(path):
    text = path.read_text(encoding="utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


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


def test_normalized_text_sha256_ignores_platform_line_endings(tmp_path):
    lf_path = tmp_path / "lf.svg"
    crlf_path = tmp_path / "crlf.svg"
    lf_path.write_bytes(b"<svg>\n<text>demo</text>\n</svg>\n")
    crlf_path.write_bytes(b"<svg>\r\n<text>demo</text>\r\n</svg>\r\n")
    assert normalized_text_sha256(lf_path) == normalized_text_sha256(crlf_path)


@pytest.mark.parametrize("demo_name", CASES)
def test_demo_manifest_matches_tracked_artifacts(demo_name):
    demo = DEMOS / demo_name
    entry = MANIFEST["demos"][demo_name]
    assert entry["fps"] == CASES[demo_name]
    tracked_files = {
        "svg": demo / "diagram.svg",
        "png": demo / f"{demo_name}.png",
        "mp4": demo / f"{demo_name}.mp4",
    }
    assert set(entry["sha256"]) == set(tracked_files)
    for artifact_type, path in tracked_files.items():
        digest = normalized_text_sha256(path) if artifact_type == "svg" else sha256(path)
        assert digest == entry["sha256"][artifact_type]


@pytest.mark.parametrize("demo_name", CASES)
def test_demo_artifacts_render_on_platform(browser_available, demo_name, tmp_path):
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

    with Image.open(tmp_path / f"{demo_name}.png") as fresh_png:
        with Image.open(demo / f"{demo_name}.png") as tracked_png:
            assert fresh_png.size == tracked_png.size
    assert_same_video_contract(
        tmp_path / f"{demo_name}.mp4",
        demo / f"{demo_name}.mp4",
    )
