#!/usr/bin/env python3
"""Check the surface-separation rule in references/svg-authoring.md.

`render_svg.py` validates structure, text collisions, margins, and motion. It never
inspects color, so the one color rule that is mechanically decidable is checked here:

    every nested surface separates from the surface it sits on, by a lightness step
    of dL* >= 4 or by a visible stroke.

A surface with neither reads as absent. Compare against the *nearest enclosing*
surface, not the page ground: a pale pill on a tinted card is judged against the card.

Usage (from the skill directory):
    python3 scripts/validate_visual_contract.py                 # all shipped diagrams
    python3 scripts/validate_visual_contract.py path/to.svg ... # specific files

Exit 0 when every checked file complies, 1 otherwise.
"""

from __future__ import annotations

import glob
import sys
import xml.etree.ElementTree as ET

MIN_LIGHTNESS_STEP = 4.0


def lightness(hex_color: str) -> float:
    """CIE L* of an sRGB hex color."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    linear = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    y = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)
    return 116 * (y ** (1 / 3) if y > 0.008856 else 7.787 * y + 16 / 116) - 16


def box(rect) -> tuple[float, float, float, float]:
    return tuple(float(rect.get(k, 0) or 0) for k in ("x", "y", "width", "height"))


def contains(outer, inner) -> bool:
    ox, oy, ow, oh = box(outer)
    ix, iy, iw, ih = box(inner)
    return ox <= ix and oy <= iy and ox + ow >= ix + iw and oy + oh >= iy + ih


def violations(svg_path: str) -> list[str]:
    root = ET.parse(svg_path).getroot()
    parent_of = {child: group for group in root.iter() for child in group}
    rects = [
        e for e in root.iter()
        if e.tag.endswith("}rect") and (e.get("fill") or "").startswith("#")
    ]
    if not rects:
        return []

    ground = rects[0]
    # Ascending area, so the first containing rect found is the nearest one.
    by_area = sorted(rects, key=lambda e: box(e)[2] * box(e)[3])

    found = []
    for rect in rects[1:]:
        area = box(rect)[2] * box(rect)[3]
        host = next(
            (s for s in by_area
             if s is not rect and box(s)[2] * box(s)[3] > area and contains(s, rect)),
            ground,
        )
        stroke = rect.get("stroke")
        if stroke is None:
            group = parent_of.get(rect)
            stroke = group.get("stroke") if group is not None else None
        if stroke and stroke != "none":
            continue
        step = abs(lightness(rect.get("fill")) - lightness(host.get("fill")))
        if step < MIN_LIGHTNESS_STEP:
            found.append(
                f"{rect.get('fill')} on {host.get('fill')}: dL*={step:.2f} "
                f"(need {MIN_LIGHTNESS_STEP:.0f}) and no stroke"
            )
    return found


def main(argv: list[str]) -> int:
    targets = argv[1:] or sorted(glob.glob("examples/**/diagram.svg", recursive=True))
    if not targets:
        print("no SVG files to check", file=sys.stderr)
        return 1

    failed = 0
    for path in targets:
        found = violations(path)
        print(f"{'FAIL' if found else 'OK  '} {path}")
        for message in found:
            print(f"       {message}")
        failed += bool(found)

    print(f"\n{len(targets) - failed}/{len(targets)} files comply")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
