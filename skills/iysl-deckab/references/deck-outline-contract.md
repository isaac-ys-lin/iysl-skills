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

## Optional Style Exploration

Use `references/style-exploration.md` only when the user asks to compare
directions, when brand or audience preference is materially unresolved, or when
the first direction has a demonstrated quality gap. A useful comparison may
include the topic's natural direction, a reasoned inversion, and a
content-specific wildcard, but a normal outline does not require three options
or a user selection ceremony. A specified style, anchor, or direct-production
request is authoritative. When exploration is used, alternatives must differ in
visual and spatial logic, and the chosen direction must be expanded faithfully
in `STYLE_INSTRUCTIONS` (see `core-role.md`).

## Outline Shape

Work as an Architect persona (see `core-role.md`): identify the decision, audience turning points, causal structure, and priority of ideas; assign each slide one primary logic relation (causal, contrast, hierarchy, flow, loop, composition, or timeline), then create a deck of at most 20 slides. If the user did not state the audience or the decision the deck must drive, infer them from the source and reflect the assumption in the cover and narrative goals instead of blocking.

STYLE_INSTRUCTIONS definition, slide four-section format, guardrails, and language rules: follow `core-role.md` exactly. Do not add a fifth section. Do not include speaker notes, full script, API settings, or image-generation suffixes in the outline unless explicitly requested.
