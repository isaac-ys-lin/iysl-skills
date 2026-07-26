from pathlib import Path

from scripts.validate_outline import validate_outline


STYLE = """```xml
<STYLE_INSTRUCTIONS>
background: #ffffff
accent: #111111
</STYLE_INSTRUCTIONS>
```"""


def slide(number=1, body="A source-backed slide."):
    return f"""Slide {number}
// NARRATIVE GOAL
Show the supported point.

// KEY CONTENT
{body}

// VISUAL
Three elements arranged left to right with arrows showing the stated relation.

// LAYOUT
16:9 split-stage with a clear reading path.
"""


def test_valid_outline_passes():
    assert validate_outline(STYLE + "\n" + slide()) == []


def test_missing_section_fails():
    outline = (STYLE + "\n" + slide()).replace("// LAYOUT\n16:9 split-stage with a clear reading path.", "")
    assert any("// LAYOUT" in error for error in validate_outline(outline))


def test_duplicate_style_block_fails():
    assert any("exactly one" in error for error in validate_outline(STYLE + "\n" + STYLE + "\n" + slide()))


def test_mode_b_requires_visible_label_whitelist():
    outline = STYLE + "\n" + slide(body="Mode B prompt")
    assert any("visible-label whitelist" in error for error in validate_outline(outline))


def test_placeholder_fails_but_source_needed_is_allowed():
    bad = STYLE + "\n" + slide(body="[Author Name]")
    good = STYLE + "\n" + slide(body="Revenue: SOURCE NEEDED")
    assert any("placeholder" in error for error in validate_outline(bad))
    assert not any("placeholder" in error for error in validate_outline(good))


def test_explicit_over_20_override():
    outline = STYLE + "\n" + "\n".join(slide(number) for number in range(1, 22))
    assert any("exceeds" in error for error in validate_outline(outline))
    assert not any("exceeds" in error for error in validate_outline(outline, allow_over_20=True))
