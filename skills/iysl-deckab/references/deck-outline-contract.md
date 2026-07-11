# Deck Outline Contract

## Contract

Use this contract when converting any content, notes, talk script, meeting record, producer notes, or deck brief into a source-faithful deck outline. This contract supplements `core-role.md`, which is the authoritative reference for STYLE_INSTRUCTIONS definition, slide structure, constraints, and language rules.

## Input Handling

- Raw content or data: extract producer notes/source first, then create the deck outline.
- Talk scripts or transcripts: preserve original claims, numbers, quotes, and context while shaping the slide narrative.
- Creative or presentation brief: expand to slide-by-slide outline; mark missing evidence as `SOURCE NEEDED`.
- Existing slide/page brief: do not rewrite the core content; move to A/B prompt workflow.
- Existing image prompt set: preserve intent; add style instructions, A/B modes, anchor workflow, and checks.
- Generated-result critique: make minimal prompt patches; do not rewrite the whole deck unless requested.

## Source Fidelity Supplement

Core source fidelity rules are in `core-role.md`. Additional rules for outline work:

1. If the user asks for stronger persuasion, improve narrative strategy and visual communication without inventing proof.
2. Preserve quote meaning; if it is not exact, use summary language and no quotation marks.

## Style Divergence

Before outline production is dispatched, the orchestrating agent presents at least three style directions whose differences are visible at a glance — if any two cover thumbnails would read as the same deck, regenerate. Structure them as thesis / antithesis / wildcard: **thesis** is the direction the topic most obviously calls for, executed at its best; **antithesis** deliberately inverts the thesis on core dimensions (dark↔light, dense↔airy, cool↔warm, technical↔humanist, restrained↔expressive) — bold, yet argued rigorously from the content's logic and emotion, never bold for its own sake, and disqualified if it reads as a mere variation of the thesis; **wildcard** is derived from a content-specific metaphor, outside common family lists. Each direction includes a name, design aesthetic, background + palette hexes, font mood, visual-element language, and a fit rationale. The user picks, blends, or adjusts. Skip only when the user already specified a style, provided a style anchor (the orchestrating agent then extracts an anchor-derived style contract as the direction), or asked to proceed directly. In non-interactive runs (batch/automation), the orchestrating agent selects one direction itself and records the rationale in the handoff message or run manifest — never inside the outline artifact. The chosen direction is passed into the dispatch prompt and must be expanded faithfully in `STYLE_INSTRUCTIONS` (see `core-role.md`).

## Outline Shape

Work as an Architect persona (see `core-role.md`): identify the decision, audience turning points, causal structure, and priority of ideas; assign each slide one primary logic relation (causal, contrast, hierarchy, flow, loop, composition, or timeline), then create a deck of at most 20 slides. If the user did not state the audience or the decision the deck must drive, infer them from the source and reflect the assumption in the cover and narrative goals instead of blocking.

STYLE_INSTRUCTIONS definition, slide four-section format, guardrails, and language rules: follow `core-role.md` exactly. Do not add a fifth section. Do not include speaker notes, full script, API settings, or image-generation suffixes in the outline unless explicitly requested.
