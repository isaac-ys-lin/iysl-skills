---
name: iysl-anidiagram
description: Use when the user asks for animated explanatory diagrams, one-page multi-diagram infographics, architecture/process/loop/funnel/timeline/flowchart visuals, animated SVG / MP4 / PNG output, or visuals from articles, screenshots, systems, or product stories.
---

# ani-diagram

Create animated explanatory diagrams as hand-authored SMIL animated SVGs. The model writes the SVG directly; `scripts/render_svg.py` validates the authoring contract, renders it deterministically in a browser, runs quality gates, and encodes MP4/PNG.

Two references are binding contracts, not suggestions:

- `references/svg-authoring.md` — structural rules the validator enforces (SMIL only, self-contained, text stays text, font stacks, loop discipline, size hierarchy).
- `references/animation-semantics.md` — the relation-to-motion table. A motion pattern that mismatches the content relation is a defect, exactly like a wrong label.

## Decision Ladder

Every diagram walks the same ladder, in order:

1. **Claim** — what should a reader understand within 3 seconds? Extract it from the source; never invent it.
2. **Relation** — sequence, loop, narrowing, ranking, tradeoff, layers, contrast, branching, system map, or multi-part story.
3. **Composition** — the visual structure that makes that relation easiest to read. Style and animation are chosen last, in service of the explanation; they are never a classifier that picks the layout.

If the source yields no claim (reference lists, plain lookup tables, material that asserts nothing), refuse to draw and ask what the reader should take away — do not invent a claim. See `examples/gallery/09-no-claim-refusal/`.

## Pipeline: Direction → Creative → Review

Production runs as three roles. Direction happens in the main conversation; Creative and Review are dispatched as subagents via the Agent tool.

### Role 1 — Direction (main conversation, must align with the user)

1. Decompose the source into a numbered fact list `F1..Fn`. Tag each fact `must-keep` or `droppable`. This list is the coverage contract for everything downstream.
2. Extract the claim (the 3-second takeaway), name the relation, and identify the audience.
3. Propose a direction: a composition approach plus an **animation story** — what the motion will explain and why, grounded in the relation-to-motion table in `references/animation-semantics.md`.
4. **Fixed step: present the claim, the fact list, and the proposed composition and animation intent to the user. Only proceed after the user confirms or corrects them.**

If step 2 produces no claim, stop here and ask (the 09 case documents this refusal).

### Role 2 — Creative (two parallel subagents)

Dispatch two Creative agents in parallel. Each agent receives:

- the source material,
- the user-confirmed direction (claim, relation, audience, animation story),
- the fact list `F1..Fn` with must-keep/droppable tags,
- both reference contracts (`svg-authoring.md`, `animation-semantics.md`).

**Divergence is mandatory**: the two agents must take different visual languages and composition strategies — not the same layout with a different palette. Assign each agent a distinct direction explicitly in its prompt (for example, one spatial/geometric composition versus one editorial/panel composition).

Each agent must produce:

- `diagram.svg` conforming to `references/svg-authoring.md`,
- a coverage table mapping every `Fi` to where it lands in the diagram, or an explicit drop with a reason — `must-keep` facts may never be dropped,
- a passing run of `render_svg.py --check` (exit 0) on its own SVG before handing it back.

### Role 3 — Review (one adversarial subagent)

Dispatch one Review agent with both candidates. The reviewer reads the raw SVG source of each candidate, views the poster PNG, and extracts six equidistant frames from each MP4 with ffmpeg, inspecting every frame:

```bash
ffmpeg -i candidate.mp4 -vf "select='not(mod(n,ceil(N/6)))'" -vsync vfr frame_%d.png
```

Rubric, in order:

- **(a) Coverage diff** — walk `F1..Fn` against each coverage table: is every fact where the table says it is, and is every drop justified? A dropped `must-keep` is an automatic fail.
- **(b) Animation semantics** — check each animated element against the relation-to-motion table in `references/animation-semantics.md`. A mismatched motion pattern is a fail, not a taste note.
- **(c) Three reading depths** — the claim lands in 3 seconds (title), the structure lands in 10 seconds (section titles and layout), and a close read rewards with details (labels and annotations).
- **(d) Visual quality** — hierarchy, density, whitespace, and collisions that the scripted checks cannot see (icon-over-label overlap, cramped groups, dead zones). This is the eyes-on pass beyond `render_svg.py`.

A fail returns a concrete fix list to the responsible Creative agent — at most two revision rounds. The main conversation picks the winner and delivers it.

## Render

```bash
python3 /path/to/skill/scripts/render_svg.py \
  --svg diagram.svg \
  --outdir /path/to/output-dir \
  --basename descriptive-name \
  --check
```

Exit codes: `0` = all checks passed and outputs written; `2` = structural validation failed (the JSON output lists every problem); `1` = a quality gate or output contract check failed. Exit 0 is required before any delivery.

The renderer's quality gates measure text collisions and canvas margins at two timeline points, verify the animation actually moves, and probe the encoded outputs. These gates are floors, not goals — the Review role still looks at frames by eye.

## Deliverables

- `diagram.svg` — the primary deliverable. It loops in any browser as-is and its text remains directly editable.
- `descriptive-name.mp4` — for embedding where SVG is not accepted.
- `descriptive-name.png` — the poster frame (`data-poster-t`), which must read as a complete diagram on its own.
- `--gif` only when the target platform cannot play video.

The static poster must be understandable before animation adds anything: motion contributes sequence, causality, or focus on top of a diagram that already works — it never carries information the poster lacks.

## Judgment Assets

- `examples/gallery/` holds worked judgment examples — claim extraction, relation choice, coverage tables, and the SVGs that resulted. They are quality anchors to reason against, not templates to copy.
- Match the source language and tone; preserve Chinese labels when the source is Chinese.
- One animation story at a time. Motion that explains nothing gets removed.
- When two compositions both fit the relation, prefer the one whose poster frame reads faster.
