"""Gallery contract tests: every diagram.svg must pass render_svg.py --check.

Discovery and documentation tests never need a browser and always run.
The render test skips when playwright + a launchable Chrome/Chromium are
unavailable (same probe as tests/test_render_svg.py).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "render_svg.py"
GALLERY = SKILL_DIR / "examples" / "gallery"

MIN_DIAGRAM_COUNT = 5  # five cases; 07 contributes two variants


def gallery_svgs():
    return sorted(GALLERY.glob("**/diagram.svg"))


def case_id(svg_path):
    return str(svg_path.relative_to(GALLERY).parent)


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


def test_gallery_has_enough_diagrams():
    svgs = gallery_svgs()
    found = [case_id(p) for p in svgs]
    assert len(svgs) >= MIN_DIAGRAM_COUNT, (
        f"expected at least {MIN_DIAGRAM_COUNT} diagram.svg files in the gallery, "
        f"found {len(svgs)}: {found}"
    )


def test_each_diagram_has_direction_and_decision():
    """Every diagram.svg case documents its direction and decision.

    Variant subdirectories (e.g. 07 arrow/dot) may share the docs of their
    parent case directory.
    """
    for svg_path in gallery_svgs():
        for doc in ("direction.md", "decision.md"):
            nearby = [svg_path.parent / doc, svg_path.parent.parent / doc]
            assert any(p.exists() for p in nearby), (
                f"{case_id(svg_path)} has no nearby {doc} "
                f"(checked {', '.join(str(p) for p in nearby)})"
            )


def test_refusal_case_has_no_diagram():
    """09 documents refusing a claim-free source; refusing is the lesson."""
    case = GALLERY / "09-no-claim-refusal"
    assert (case / "brief.md").exists(), "refusal case needs a brief.md"
    assert (case / "decision.md").exists(), "refusal case needs a decision.md"
    assert not list(case.glob("**/diagram.svg")), (
        "the refusal case must not contain a diagram.svg; refusing is the lesson"
    )


@pytest.mark.parametrize("svg_path", gallery_svgs(), ids=case_id)
def test_gallery_diagram_passes_check(browser_available, svg_path, tmp_path):
    basename = "-".join(svg_path.relative_to(GALLERY).parent.parts)
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--svg", str(svg_path),
            "--outdir", str(tmp_path),
            "--basename", basename,
            "--fps", "10",
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{case_id(svg_path)} failed render_svg.py --check "
        f"(exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
    )
    report = json.loads(result.stdout)
    assert report["ok"] is True


def test_arrow_never_moves_backward_while_visible(browser_available):
    from playwright.sync_api import sync_playwright

    svg_path = GALLERY / "07-style-motion-contrast" / "arrow" / "diagram.svg"
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="chrome")
        except Exception:
            browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1200, "height": 680})
            page.set_content(svg_path.read_text(encoding="utf-8"))
            samples = page.evaluate(
                """
                async () => {
                  const svg = document.querySelector('svg');
                  const arrow = document.querySelector('animateTransform').parentElement;
                  svg.pauseAnimations();
                  const rows = [];
                  for (let i = 0; i < 20; i++) {
                    const t = 7.2 + i * (0.79 / 19);
                    svg.setCurrentTime(t);
                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                    let node = arrow;
                    let opacity = 1;
                    while (node && node !== svg) {
                      opacity *= Number.parseFloat(getComputedStyle(node).opacity || '1');
                      node = node.parentElement;
                    }
                    const rect = arrow.getBoundingClientRect();
                    rows.push({t, x: rect.x + rect.width / 2, opacity});
                  }
                  return rows;
                }
                """
            )
        finally:
            browser.close()

    for previous, current in zip(samples, samples[1:]):
        if previous["opacity"] >= 0.05 and current["opacity"] >= 0.05:
            assert current["x"] >= previous["x"] - 1, (
                "arrow moved backward while visible: "
                f"t={previous['t']:.3f}->{current['t']:.3f}, "
                f"x={previous['x']:.1f}->{current['x']:.1f}"
            )
