# Output Risk Profile

## Boundary

This skill owns animated explanatory diagrams authored as hand-written SMIL animated SVGs. `scripts/render_svg.py` validates the authoring contract, renders the SVG deterministically in a browser, runs quality gates, and encodes MP4/PNG (GIF on request). The primary deliverable is the editable `.svg`; `.mp4` and `.png` are derived.

## Main Risks

- Wrong relation: content forced into a composition that hides the real story (a loop drawn as a linear sequence, a ranking drawn as a funnel).
- Missed details: a source fact that should survive is silently dropped, so the diagram reads as a bare skeleton instead of a complete explanation.
- Mismatched motion: the animation pattern does not encode the content relation (a loop that scans linearly, a contrast animated as one-sided flow) — a defect, not a taste note.
- Template drift: outputs start looking identical even when the content calls for different structures.
- Text overload: long labels fit technically but become hard to read.
- Decorative animation: motion that does not explain sequence, causality, or focus; or more than one animation story competing at once.
- Editability regression: the SVG stops being self-contained (embeds external resources), converts text to paths, or otherwise loses its editable text semantics.
- Over-constraint: rigid rules or classifier logic start replacing the model's semantic judgment about relation and composition.

## Current Controls

- `references/svg-authoring.md` defines the structural contract the validator enforces: SMIL-only animation, self-contained resources, text stays `<text>`, CJK font stacks, seamless loop discipline, and size hierarchy.
- `references/animation-semantics.md` defines the relation-to-motion table and per-relation anti-patterns; the Review role checks each animated element against it.
- `SKILL.md` runs production as a three-role pipeline (Direction → Creative → Review) with a numbered `F1..Fn` fact list as the coverage contract, so dropped `must-keep` facts fail review.
- `scripts/render_svg.py` structural validation rejects non-SMIL animation, `<script>`, external resources, missing `data-loop-seconds`, and missing CJK font fallback before rendering (CLI exit `2` with a per-problem `messages` list); nothing silently degrades.
- `render_svg.py --check` renders each frame in a real browser and measures text collisions and canvas margins from in-page `getBoundingClientRect` (more accurate than estimated widths) at two timeline points, verifies the animation actually moves (`motion_nonzero`), and probes the encoded MP4/PNG/GIF output contracts.
- Tests cover structural-validation rejection cases, the full browser render pipeline on a sample SVG, collision detection, and a gallery pass that renders every `examples/gallery/**/diagram.svg` to exit 0 (browser tests skip when no browser is available).

## Known Limits

- The validator checks structure and measurable quality; visual taste — hierarchy, density, whether the poster reads on its own — still needs the Review role's eyes on the frames.
- Deterministic rendering depends on the browser's SMIL `setCurrentTime` seek; the fallback if that regresses is WAAPI-based seeking, which would change only the renderer, not the authoring contract.
- Motion must encode the relation; the machine checks that motion exists, not that it means the right thing — that stays a Review-role judgment against `animation-semantics.md`.
- Examples are quality anchors, not templates to copy blindly.
