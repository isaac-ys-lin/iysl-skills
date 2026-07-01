# Deck Outline Contract

## Contract

Use this contract when converting any content, notes, talk script, meeting record, producer notes, or deck brief into a source-faithful deck outline.

## Input Handling

- Raw content or data: extract producer notes/source first, then create the deck outline.
- Talk scripts or transcripts: preserve original claims, numbers, quotes, and context while shaping the slide narrative.
- Creative or presentation brief: expand to slide-by-slide outline; mark missing evidence as `SOURCE NEEDED`.
- Existing slide/page brief: do not rewrite the core content; move to A/B prompt workflow.
- Existing image prompt set: preserve intent; add style instructions, A/B modes, anchor workflow, and checks.
- Generated-result critique: make minimal prompt patches; do not rewrite the whole deck unless requested.

## Source Fidelity

1. Every number, claim, quote, data point, named entity, example, and comparison must trace to producer notes/source.
2. If support is unclear, write `SOURCE NEEDED: <needed evidence>` instead of guessing.
3. You may order, group, name, summarize, and design narrative flow, but not alter source meaning, degree, causality, or timing.
4. If sources conflict, preserve the conflict and mark what needs confirmation.
5. If the user asks for stronger persuasion, improve narrative strategy and visual communication without inventing proof.
6. Preserve quote meaning; if it is not exact, use summary language and no quotation marks.

## Outline Shape

Work as an Architect persona: identify the decision, audience turning points, causal structure, and priority of ideas, then create a deck of at most 20 slides.

Output must start with exactly one fenced code block containing only `<STYLE_INSTRUCTIONS>` XML tags and style guide. Do not place summaries, conversational filler, or another style block before it.

`<STYLE_INSTRUCTIONS>` must define:

1. Design aesthetic.
2. Background color with hex and material/texture note.
3. Primary font personality for headlines.
4. Secondary font for readable body copy.
5. Color palette with primary text hex and primary accent hex.
6. Visual elements: line work, imagery policy, layout logic.
7. Optional only when useful: icon, chart, spacing, or annotation style.

After the code block, output `Slide 1` through `Slide N`, where `N <= 20`.

Each slide has exactly four sections:

```text
Slide 1
// NARRATIVE GOAL
Single idea this slide must make the audience understand or believe.

// KEY CONTENT
Source-backed content; missing evidence is SOURCE NEEDED.

// VISUAL
Main visual, chart, infographics, or scene concept with required visible labels.

// LAYOUT
16:9 composition, hierarchy, reading path, and editable text zones.
```

Do not add a fifth section. Do not include speaker notes, full script, API settings, or image-generation suffixes in the outline unless explicitly requested.

## Guardrails

- Slide 1 must be a designed cover.
- Final slide must be a designed back cover or closing anchor statement.
- Do not use `Thank You`, `Any Questions?`, `[Author Name]`, `[Date]`, or similar placeholders.
- Do not use AI cliche patterns such as `It wasn't just [X], it was [Y]`.
- Do not ask to generate photorealistic images of prominent individuals.
- Do not add slide numbers, footers, logos, or running headers unless producer notes require them.

## Language And Labels

If the source or audience is Chinese, default to Taiwan Traditional Chinese. Visible labels in diagrams and images keep the source language; do not translate Chinese labels into English. Existing acronyms such as PM, PD, PSC, PRC, PAC, and PMC may remain unchanged.
