---
name: iysl-anidiagram
description: Use when the user asks for animated explanatory diagrams, one-page multi-diagram infographics, architecture/process/loop/funnel/timeline/flowchart visuals, editable Excalidraw diagrams, PNG/GIF output, or visuals from articles, screenshots, systems, or product stories.
---

# ani-diagram

Create animated explanatory diagrams from content, screenshots, articles, or systems. Let the idea choose the shape; render deterministic `.png`, `.gif`, and `.excalidraw`.

## Core Approach

1. Extract actors, stages, loops, metrics, decisions, and takeaway.
2. Decide the relation before visuals: sequence, loop, narrowing, ranking, tradeoff, layers, contrast, branching, system map, or multi-part story.
3. Write compact JSON, or Diagram IR first when the source is not already a spec.
4. Render with the bundled Python/Pillow renderer.
5. Verify motion, dimensions, editable Excalidraw, and readability.

## Design Latitude Contract

1. Extract the claim before choosing the layout.
2. Choose the relation first: sequence, loop, narrowing, ranking, tradeoff, layers, contrast, branching, system map, or multi-part story.
3. Use `examples/gallery/` for judgment patterns, not visual copying.
4. Use `assets/*-spec.json` only to confirm valid fields and renderer contracts.
5. Vary label density, grouping, emphasis, tone, and animation when it clarifies the source.
6. Do not use style atoms as a classifier; choose style after relation and layout.
7. If no primitive fits, extend the renderer with tests instead of distorting an unrelated layout.
8. Always render with `--verify --check`; it measures painted text collisions and canvas margins. Still human-review the PNG for hierarchy, icon-over-label overlap, and readability.
9. If the source yields no claim (reference lists, plain tables, material with nothing to prove), say a diagram is not warranted and ask what the reader should take away — do not invent a claim. See `examples/gallery/09-no-claim-refusal/`.

## Layout Primitives

- `circular_loop`: repeated traps, flywheels, metric loops, feedback loops.
- `timeline`: chronological plans, release steps, incidents, maturity paths.
- `funnel`: conversion, filtering, leakage, drop-off.
- `ranking`: magnitude comparison of independent parallel quantities; use `funnel` only when one population narrows through stages.
- `matrix`: prioritization, positioning, tradeoffs.
- `stack`: layers, capability stacks, dependencies.
- `before_after`: transformation, contrast, migration.
- `flow`: branching decisions, retry/loop-back, merge paths; use `timeline` when the path is linear.
- `composite`: one infographic page combining several primitives as stacked full/half-width sections. One claim -> one primitive; multiple related claims on one page -> `composite`. Never nest composites.
- `architecture`: black-canvas system map with inputs, pipeline, gate, outputs.
- For unsupported shapes, extend the script instead of distorting an existing layout.

Schemas live in `references/spec-format.md`. Renderer contract samples live in `assets/*-spec.json`. Judgment examples live in `examples/gallery/`; read their `decision.md` files when a source could reasonably become more than one layout.

## Visual Principles

- Let the content choose the structure.
- Model owns semantic choices; renderer owns stable output, validation, and checks.
- Use optional style, block color, and animation atoms to adjust emphasis without changing the chosen layout.
- Use short labels, clear hierarchy, one main claim, and one animation story.
- On composite pages each section keeps one claim; the page title carries the umbrella story.
- Static PNG must read before GIF motion adds sequence, causality, or focus.
- Match the reference language and tone. Preserve Chinese labels when the source is Chinese.
- Avoid text overlap, cramped badges, tiny type, and decorative motion that does not explain anything.
- Keep `.excalidraw` editable and text-based. Do not embed external files unless explicitly requested.

## Render

```bash
python3 /path/to/skill/scripts/render_animated_diagram.py \
  --spec /path/to/spec.json \
  --outdir /path/to/output-dir \
  --basename descriptive-name \
  --verify \
  --check
```

## Validate And Deliver

Run with `--check`: exit 0 is required; exit 2 means the spec is invalid (the JSON output lists every problem); exit 1 means an output contract check failed. Then human-review the PNG for overlap, clipping, contrast, and hierarchy. Deliver `.gif`, `.png`, and `.excalidraw`.
