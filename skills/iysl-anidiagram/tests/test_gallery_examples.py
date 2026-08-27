"""Gallery admission and render-contract tests.

Admission tests never need a browser and always run.
The render test skips when playwright + a launchable Chrome/Chromium are
unavailable (same probe as tests/test_render_svg.py).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "render_svg.py"
GALLERY_VALIDATOR = SKILL_DIR / "scripts" / "validate_gallery.py"
GALLERY = SKILL_DIR / "examples" / "gallery"

MIN_DIAGRAM_COUNT = 5  # five cases; 07 contributes two variants


def gallery_svgs():
    return sorted(GALLERY.glob("**/diagram.svg"))


def case_id(svg_path):
    return str(svg_path.relative_to(GALLERY).parent)


def run_gallery_validator(gallery=GALLERY):
    result = subprocess.run(
        [sys.executable, str(GALLERY_VALIDATOR), str(gallery)],
        capture_output=True,
        text=True,
    )
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


def test_gallery_has_enough_diagrams():
    svgs = gallery_svgs()
    found = [case_id(p) for p in svgs]
    assert len(svgs) >= MIN_DIAGRAM_COUNT, (
        f"expected at least {MIN_DIAGRAM_COUNT} diagram.svg files in the gallery, "
        f"found {len(svgs)}: {found}"
    )


def test_gallery_cases_pass_admission_contract():
    result, report = run_gallery_validator()

    assert result.returncode == 0, result.stdout + result.stderr
    assert report["valid"] is True
    assert report["errors"] == []


@pytest.mark.parametrize(
    ("relative_path", "old", "new", "expected"),
    [
        (
            "05-review-branching-flow/decision.md",
            "## Primary Claim",
            "## Claim Summary",
            "decision.md missing required section: Primary Claim",
        ),
        (
            "05-review-branching-flow/direction.md",
            "## Audience",
            "## Intended Readers",
            "direction.md missing required section: Audience",
        ),
        (
            "05-review-branching-flow/decision.md",
            "## Validation",
            "## Final Check",
            "decision.md missing required section: Validation",
        ),
        (
            "05-review-branching-flow/decision.md",
            "The process matters because it branches on review outcomes, allows "
            "retries, and rejoins at merge.",
            "",
            "decision.md has empty required section: Primary Claim",
        ),
        (
            "05-review-branching-flow/brief.md",
            "# Review Workflow Brief",
            "## Review Workflow Brief",
            "brief.md must start with an H1",
        ),
        (
            "05-review-branching-flow/direction.md",
            "| F4 |",
            "| F9 |",
            "direction.md Fact List IDs must be contiguous from F1",
        ),
        (
            "09-no-claim-refusal/decision.md",
            "None. The page asserts nothing; it exists for lookup.",
            "The page proves that tooling overlaps across squads.",
            "claim-bearing case requires at least one diagram.svg",
        ),
        (
            "05-review-branching-flow/direction.md",
            "Review is not a straight line: one decision point routes every change "
            "to pass, revise, or escalate — and all paths rejoin at merge.",
            "",
            "direction.md has empty required section: Claim",
        ),
        (
            "05-review-branching-flow/direction.md",
            "## Animation Story",
            "## Motion",
            "direction.md missing required section: Animation Story",
        ),
    ],
)
def test_gallery_admission_rejects_invalid_case_docs(
    tmp_path, relative_path, old, new, expected
):
    gallery = tmp_path / "gallery"
    shutil.copytree(GALLERY, gallery)
    target = gallery / relative_path
    original = target.read_text(encoding="utf-8")
    assert old in original
    target.write_text(original.replace(old, new, 1), encoding="utf-8")

    result, report = run_gallery_validator(gallery)

    assert result.returncode == 1
    assert any(expected in error for error in report["errors"])


def test_gallery_admission_rejects_missing_direction(tmp_path):
    gallery = tmp_path / "gallery"
    shutil.copytree(GALLERY, gallery)
    (gallery / "05-review-branching-flow" / "direction.md").unlink()

    result, report = run_gallery_validator(gallery)

    assert result.returncode == 1
    assert any("missing direction.md" in error for error in report["errors"])


def test_gallery_admission_rejects_diagram_for_no_claim(tmp_path):
    gallery = tmp_path / "gallery"
    shutil.copytree(GALLERY, gallery)
    (gallery / "09-no-claim-refusal" / "diagram.svg").write_text(
        "<svg/>", encoding="utf-8"
    )

    result, report = run_gallery_validator(gallery)

    assert result.returncode == 1
    assert any(
        "claim-free refusal must not contain diagram.svg" in error
        for error in report["errors"]
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
