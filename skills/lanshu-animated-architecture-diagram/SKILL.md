---
name: lanshu-animated-architecture-diagram
description: Use when the user asks for animated explanatory diagrams, architecture/process/loop/funnel/timeline visuals, editable Excalidraw diagrams, PNG/GIF output, or visual explanations from articles, screenshots, systems, or product stories.
---

# Principled Animated Diagram

Create animated explanatory diagrams from content, screenshots, articles, or systems. Let the idea choose the shape; render deterministic `.png`, `.gif`, and editable `.excalidraw`.

## Core Approach

1. Extract the message: actors, stages, loops, metrics, decisions, and takeaway.
2. Decide the relation before visuals: sequence, cycle, narrowing, tradeoff, layers, contrast, or system map.
3. Write compact JSON, or Diagram IR first when the source is not already a spec.
4. Render with the bundled Python/Pillow renderer.
5. Verify motion, dimensions, editable Excalidraw JSON, and basic readability before delivery.

## Layout Primitives

- `circular_loop`: repeated traps, flywheels, metric loops, cycles.
- `timeline`: chronological plans, release steps, incidents, maturity paths.
- `funnel`: conversion, filtering, leakage, drop-off.
- `matrix`: prioritization, positioning, tradeoffs.
- `stack`: layers, capability stacks, dependencies.
- `before_after`: transformation, contrast, migration.
- `architecture`: black-canvas system map with inputs, pipeline, gate, outputs.
- Use `flow` only if branching decisions, retry, escalation, or merge paths are needed and a linear timeline would distort the idea.
- For unsupported shapes, extend the script instead of distorting an existing layout.

Read `references/spec-format.md` for schemas, Diagram IR, and extension rules. Use `assets/*-spec.json` as quality anchors, not templates. Reports hold maintenance evidence.

## Visual Principles

- Let the content choose the structure.
- Model owns semantic choices; renderer owns stable output and checks.
- Use optional style, block color, and animation atoms to adjust emphasis without changing the chosen layout.
- Use short labels, clear hierarchy, one main claim, and one animation story.
- Static PNG must read before GIF motion adds sequence, causality, or focus.
- Match the reference language and tone. Preserve Chinese labels when the source is Chinese.
- Avoid text overlap, cramped badges, tiny type, and decorative motion that does not explain anything.
- Keep `.excalidraw` editable and text-based. Do not embed external files unless explicitly requested.

## Render

```bash
python /path/to/skill/scripts/render_animated_diagram.py \
  --spec /path/to/spec.json \
  --outdir /path/to/output-dir \
  --basename descriptive-name \
  --verify \
  --check
```

## Validate And Deliver

`--check` must return `"ok": true`; motion diffs must be nonzero. Review PNG for overlap, clipping, contrast, and hierarchy. Deliver `.gif`, `.png`, and `.excalidraw`.
