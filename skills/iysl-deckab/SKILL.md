---
name: iysl-deckab
description: Turn source material, talks, producer notes, slide briefs, or image prompt sets into a source-faithful deck outline, slide brief, Mode A/B prompt set, or style-anchor workflow. Exclude direct PPTX/Keynote export, one-off image generation, writing polish, asset search, and design critique only.
compatibility: Requires Python for the deterministic outline validator; source and prompt work can remain inline and does not require network access.
---

# Source-faithful Deck Design

## Intent

Convert the requested source or existing brief into the smallest useful deck
artifact while keeping story truth in the outline and visual execution in the
prompt layer.

## Use and boundaries

- Use for deck outlines, slide briefs, Mode A/B image prompts, or a
  reference-image style anchor workflow.
- Classify the requested output first. For a deck outline or slide brief, read
  both `references/core-role.md` and
  `references/deck-outline-contract.md`. For Mode A/B prompts or an anchor
  workflow, read `references/image-prompt-workflow.md`. Read
  `references/artifact-storage.md` before writing when the user requests saved
  artifacts, the deck exceeds three slides, subagents are used, both A/B modes
  are produced, or the work includes API production, anchors, image generation,
  or a second correction round.
- Do not use for PPTX/Keynote export, one-off image generation, writing polish,
  asset search, or design critique only.

## Invariants

- Preserve source facts, numbers, claims, quotes, and proper nouns. Mark missing
  support as `SOURCE NEEDED`; never fill gaps with plausible content.
- Treat the outline as story truth. Prompts may specify visual execution but do
  not rewrite the source or copy a style anchor's content.
- Use Taiwan Traditional Chinese for visible Chinese labels. Mode B must include
  a visible-label whitelist and no extra in-image text.
- When the structured outline contract is requested, keep one style block, slide
  numbering, four required sections, and `N <= 20` unless explicitly overridden.

## Adaptive execution

Build an internal logic map, choose one source-appropriate style direction, and
produce the requested artifact inline by default. A user-specified style or
anchor is authoritative; do not reopen the choice. A work or analysis deck may
omit a back cover when page count or purpose calls for it; an external sharing
deck should close the narrative deliberately.

Run `scripts/validate_outline.py` when producing the structured outline and fix
every reported structural failure. Then compare every claim, number, quote, and
proper noun with the source, confirm unsupported material is marked
`SOURCE NEEDED`, and apply the completion checks in `references/core-role.md`.
Stop only after the structural and source-fidelity checks both pass. Offer
multiple style directions, variants, or subagents only when requested, when
preference is materially ambiguous, or when the first direction has a
demonstrated quality gap.

## Validation and resources

Use `references/deck-outline-contract.md` for the exact outline format and
`references/image-prompt-workflow.md` for Mode A/B and anchors. Use
`references/style-exploration.md` only when exploration is justified; use
`references/artifact-storage.md` only when artifacts or a run folder are needed.
