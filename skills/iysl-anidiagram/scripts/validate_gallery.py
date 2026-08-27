#!/usr/bin/env python3
"""Validate decision-gallery admission and print one JSON report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DEFAULT_GALLERY = Path(__file__).resolve().parent.parent / "examples" / "gallery"
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
H1_RE = re.compile(r"^#(?!#)\s+\S")
NO_CLAIM_RE = re.compile(r"^None(?:[.:\s]|$)", re.IGNORECASE)
DIRECTION_SECTIONS = ("Claim", "Relation", "Audience", "Fact List")
DECISION_SECTIONS = ("Primary Claim", "Rejected Alternatives", "Validation")


def _markdown_sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.end():end].strip()
    return sections


def _validate_gallery(gallery: Path) -> dict[str, object]:
    errors: list[str] = []
    case_dirs = sorted(path for path in gallery.iterdir() if path.is_dir())
    for case in case_dirs:
        has_diagram = any(case.rglob("diagram.svg"))
        brief = case / "brief.md"
        if not brief.is_file():
            errors.append(f"{case.name}: missing brief.md")
        elif not H1_RE.match(brief.read_text(encoding="utf-8").lstrip()):
            errors.append(f"{case.name}: brief.md must start with an H1")
        decision = case / "decision.md"
        if not decision.is_file():
            errors.append(f"{case.name}: missing decision.md")
            continue
        sections = _markdown_sections(decision.read_text(encoding="utf-8"))
        for required in DECISION_SECTIONS:
            if required not in sections:
                errors.append(f"{case.name}: decision.md missing required section: {required}")
            elif not sections[required]:
                errors.append(f"{case.name}: decision.md has empty required section: {required}")
        claim_free = bool(NO_CLAIM_RE.match(sections.get("Primary Claim", "")))
        if claim_free:
            if has_diagram:
                errors.append(f"{case.name}: claim-free refusal must not contain diagram.svg")
            continue
        if not has_diagram:
            errors.append(f"{case.name}: claim-bearing case requires at least one diagram.svg")
            continue
        direction = case / "direction.md"
        if not direction.is_file():
            errors.append(f"{case.name}: missing direction.md")
            continue
        direction_sections = _markdown_sections(direction.read_text(encoding="utf-8"))
        for required in DIRECTION_SECTIONS:
            if required not in direction_sections:
                errors.append(
                    f"{case.name}: direction.md missing required section: {required}"
                )
            elif not direction_sections[required]:
                errors.append(
                    f"{case.name}: direction.md has empty required section: {required}"
                )
        animation_sections = {"Animation Story", "Animation Stories"} & set(
            direction_sections
        )
        if not animation_sections:
            errors.append(
                f"{case.name}: direction.md missing required section: Animation Story"
            )
        elif not any(direction_sections[section] for section in animation_sections):
            errors.append(
                f"{case.name}: direction.md has empty required section: Animation Story"
            )
        fact_ids = [
            int(value)
            for value in re.findall(
                r"\bF(\d+)\b", direction_sections.get("Fact List", "")
            )
        ]
        unique_fact_ids = sorted(set(fact_ids))
        expected_fact_ids = (
            list(range(1, unique_fact_ids[-1] + 1)) if unique_fact_ids else []
        )
        if (
            not fact_ids
            or len(fact_ids) != len(unique_fact_ids)
            or unique_fact_ids != expected_fact_ids
        ):
            found = ", ".join(f"F{value}" for value in unique_fact_ids) or "none"
            errors.append(
                f"{case.name}: direction.md Fact List IDs must be contiguous "
                f"from F1; found {found}"
            )
    return {
        "valid": not errors,
        "cases": [case.name for case in case_dirs],
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gallery", nargs="?", type=Path, default=DEFAULT_GALLERY)
    args = parser.parse_args(argv)
    gallery = args.gallery.resolve()
    if not gallery.is_dir():
        print(
            json.dumps(
                {
                    "valid": False,
                    "cases": [],
                    "errors": [f"gallery not found: {gallery}"],
                },
                indent=2,
            )
        )
        return 2
    report = _validate_gallery(gallery)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
