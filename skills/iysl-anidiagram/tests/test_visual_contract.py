"""Surface-separation contract tests.

`references/svg-authoring.md` states one colour rule that is mechanically
decidable: every nested surface separates from the surface it sits on, by a
lightness step of dL* >= 4 or by a visible stroke. `render_svg.py` never
inspects colour, so without these tests the rule would decay into prose the
way the font-size table did.

The negative case matters as much as the positive one: a suite that only
asserts "everything passes" would keep passing if the checker became a no-op.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
CHECKER = SKILL_DIR / "scripts" / "validate_visual_contract.py"
EXAMPLES = SKILL_DIR / "examples"

# A panel with no stroke, 2.13 L* from its ground: the defect this rule was
# written for. Structure is deliberately minimal; the checker reads geometry
# and fills, not motion.
VIOLATING_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
  <rect x="0" y="0" width="200" height="100" fill="#f6f8fb"/>
  <rect x="20" y="20" width="160" height="60" rx="8" fill="#eef2f9"/>
</svg>
"""

# The same panel, deepened until it clears the step.
COMPLIANT_SVG = VIOLATING_SVG.replace("#eef2f9", "#e4eaf5")

# The same thin panel, separated by a stroke instead of a lightness step.
STROKED_SVG = VIOLATING_SVG.replace(
    'rx="8" fill="#eef2f9"', 'rx="8" fill="#eef2f9" stroke="#c9d6ef"'
)


def shipped_svgs():
    return sorted(EXAMPLES.glob("**/diagram.svg"))


def example_id(svg_path):
    return str(svg_path.relative_to(EXAMPLES).parent)


def run_checker(*paths):
    return subprocess.run(
        [sys.executable, str(CHECKER), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
        cwd=SKILL_DIR,
    )


def test_checker_exists_and_examples_were_found():
    assert CHECKER.exists(), "validate_visual_contract.py is missing"
    assert shipped_svgs(), "no shipped diagrams found to check"


@pytest.mark.parametrize("svg_path", shipped_svgs(), ids=example_id)
def test_shipped_diagram_meets_surface_separation(svg_path):
    result = run_checker(svg_path)
    assert result.returncode == 0, (
        f"{example_id(svg_path)} violates the surface-separation rule:\n"
        f"{result.stdout}{result.stderr}"
    )


def test_checker_rejects_an_invisible_surface(tmp_path):
    """Without this, a checker that always returned 0 would look healthy."""
    svg = tmp_path / "violating.svg"
    svg.write_text(VIOLATING_SVG, encoding="utf-8")
    result = run_checker(svg)
    assert result.returncode == 1, (
        "checker accepted a panel 2.13 L* from its ground with no stroke:\n"
        f"{result.stdout}{result.stderr}"
    )
    assert "dL*" in result.stdout


def test_checker_accepts_a_sufficient_lightness_step(tmp_path):
    svg = tmp_path / "compliant.svg"
    svg.write_text(COMPLIANT_SVG, encoding="utf-8")
    assert run_checker(svg).returncode == 0


def test_checker_accepts_a_stroke_instead_of_a_lightness_step(tmp_path):
    """Both routes are legitimate; the rule is separation, not depth."""
    svg = tmp_path / "stroked.svg"
    svg.write_text(STROKED_SVG, encoding="utf-8")
    assert run_checker(svg).returncode == 0


def test_checker_measures_against_the_nearest_enclosing_surface(tmp_path):
    """A pale pill on a tinted card is judged against the card, not the ground.

    Against the page ground the pill would look fine; against the card it does
    not. Comparing to the wrong parent was a real bug during authoring.
    """
    svg = tmp_path / "nested.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#ffffff"/>
  <rect x="20" y="20" width="360" height="160" fill="#f8faff" stroke="#cfd9eb"/>
  <rect x="60" y="60" width="120" height="40" fill="#edf2ff"/>
</svg>
""",
        encoding="utf-8",
    )
    result = run_checker(svg)
    assert result.returncode == 1, (
        "pill was compared against the page ground instead of the card it sits on:\n"
        f"{result.stdout}"
    )
    assert "#f8faff" in result.stdout, (
        f"expected the card named as the host surface, got:\n{result.stdout}"
    )
