---
name: iysl-anidiagram
description: Create a source-faithful animated explanatory diagram as editable SMIL SVG with MP4 and PNG outputs. Use when the user wants a claim, relation, process, comparison, system map, or neutral structure made visual; do not invent unsupported claims.
compatibility: Requires Python, Playwright with a launchable browser, and ffmpeg for rendering; structural checks remain available without browser rendering.
---

# Animated Diagram

## Intent

Turn a supported claim or neutral structure into one readable animated diagram
whose composition and motion make the relation easier to understand.

## Use and boundaries

- Read the source and identify the takeaway, relation, audience, and must-keep
  information before choosing layout or style.
- If a reference list or lookup table has no claim, a descriptive structure is
  allowed when the user asks for one; otherwise ask for the intended takeaway.
- Do not invent causality, ranking, emphasis, or facts merely to make a visual.

## Invariants

- Preserve source meaning and keep text editable; follow the SVG safety and
  self-contained contract in `references/svg-authoring.md`.
- Motion must encode the claimed relation, not act as decoration; use
  `references/animation-semantics.md` for relation-to-motion choices.
- The poster frame must be complete and readable before animation adds focus or
  sequence. A requested variant must differ in actual visual or spatial logic.
- `render_svg.py --check` must pass before any SVG, MP4, or PNG is delivered.

## Adaptive execution

1. Build an internal content map: takeaway, relation, required facts, audience,
   and what can be omitted.
2. Choose one composition, motion story, and visual treatment that best serves
   that relation. Produce one candidate by default.
3. Run the renderer's structural and output checks. Fix the reported failure,
   then inspect the poster and a complexity-appropriate sample of frames.
4. Deliver the editable `diagram.svg`, MP4, and poster PNG as the default
   verified bundle; add GIF only when requested. If browser rendering or ffmpeg
   is unavailable, report the missing dependency instead of delivering a
   partially verified bundle. Stop once acceptance is met.

Escalate to additional candidates, subagents, blind review, or deeper frame
sampling only for an explicit variants request, materially ambiguous visual
directions, a high-value external delivery, or a quality gap after the first
candidate. The number of agents and revisions is not fixed.

## Validation and resources

Use `scripts/render_svg.py --check` as the hard gate. Read `style-directions.md`
when the content's visual language is uncertain or a multi-candidate comparison
is needed; read `quality-escalation.md` only when escalation is justified. When
adding or changing a decision-gallery case, follow `examples/gallery/README.md`
and run `scripts/validate_gallery.py` before rendering.
