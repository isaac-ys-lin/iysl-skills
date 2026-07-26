#!/usr/bin/env python3
"""Validate the deterministic structure of an iysl-deckab outline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SLIDE_RE = re.compile(r"^Slide\s+(\d+)\s*$", re.IGNORECASE | re.MULTILINE)
STYLE_RE = re.compile(r"```[^\n]*\n\s*<STYLE_INSTRUCTIONS>[\s\S]*?</STYLE_INSTRUCTIONS>\s*\n```", re.IGNORECASE)
REQUIRED_SECTIONS = ("// NARRATIVE GOAL", "// KEY CONTENT", "// VISUAL", "// LAYOUT")
PLACEHOLDER_RE = re.compile(r"\[[^\]]*(?:author|date|title|name)[^\]]*\]|\b(?:TODO|TBD|PLACEHOLDER)\b", re.IGNORECASE)


def validate_outline(text: str, *, allow_over_20: bool = False, allow_missing_style: bool = False) -> list[str]:
    errors: list[str] = []
    style_blocks = STYLE_RE.findall(text)
    if not allow_missing_style and len(style_blocks) != 1:
        errors.append(f"expected exactly one STYLE_INSTRUCTIONS block, found {len(style_blocks)}")

    slide_matches = list(SLIDE_RE.finditer(text))
    if not slide_matches:
        errors.append("no Slide N headings found")
        return errors
    numbers = [int(match.group(1)) for match in slide_matches]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        errors.append(f"slide numbers must be continuous from 1: found {numbers}")
    if len(numbers) > 20 and not allow_over_20:
        errors.append(f"slide count {len(numbers)} exceeds N <= 20; pass --allow-over-20 for an explicit override")

    for index, match in enumerate(slide_matches):
        end = slide_matches[index + 1].start() if index + 1 < len(slide_matches) else len(text)
        block = text[match.start() : end]
        slide_number = match.group(1)
        for section in REQUIRED_SECTIONS:
            count = block.count(section)
            if count != 1:
                errors.append(f"Slide {slide_number}: expected one {section}, found {count}")
        if "mode b" in block.lower() and not re.search(r"visible[- ]label whitelist|visible_label_whitelist", block, re.IGNORECASE):
            errors.append(f"Slide {slide_number}: Mode B requires a visible-label whitelist")

    placeholder = PLACEHOLDER_RE.search(text)
    if placeholder:
        errors.append(f"placeholder is not allowed: {placeholder.group(0)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outline", type=Path, help="Markdown outline to validate")
    parser.add_argument("--allow-over-20", action="store_true")
    parser.add_argument("--allow-missing-style", action="store_true")
    args = parser.parse_args()
    try:
        text = args.outline.read_text(encoding="utf-8")
    except OSError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 2
    errors = validate_outline(text, allow_over_20=args.allow_over_20, allow_missing_style=args.allow_missing_style)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
