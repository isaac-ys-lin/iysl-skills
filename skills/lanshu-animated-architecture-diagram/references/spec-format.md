# Animated Diagram Spec Format

Use this reference when creating or editing specs for `scripts/render_animated_diagram.py`.

## Shared Contract

```json
{
  "layout": "timeline",
  "canvas": {"width": 1210, "height": 1138, "frames": 41, "fps": 20},
  "style": {"tone": "light_editorial"},
  "animation": {"marker": "dot"},
  "finish": {"grain": true},
  "palette": {},
  "title": {"main": "Specific claim", "subtitle": "Optional context"}
}
```

- `layout`: choose the visual primitive. Supported: `circular_loop`, `timeline`, `funnel`, `matrix`, `stack`, `before_after`, `architecture`.
- `canvas`: output dimensions and GIF timing.
- `palette`: optional override. Light layouts use `background`, `primary`, `muted`, `border`, `chip`, `text`.
- Block-level `style`: optional override for a specific step, card, point, stage, or contrast block.
- `animation.marker`: optional for light layouts; use `arrow` when motion should imply forward handoff instead of moving dots.
- `style.tone`: optional; use `light_editorial` by default, or `dark_technical` when the source calls for Lanshu/DailyDoseOfDS-style black technical sketches.
- `finish`: optional visual finish atoms. Supported keys: `grain`, `vignette`, `soft_glow`.
- Keep labels short. Text fitting is a safety net, not a substitute for editing.

## Design Atoms

Use design atoms to tune presentation without replacing semantic layout judgment:

- `style.tone: "light_editorial"`: quiet blue editorial look for broad training, product, and business explanations.
- `style.tone: "dark_technical"`: black-canvas technical look inspired by the original Lanshu repo; best for system maps, architecture, and technical workflow explanations.
- `animation.marker: "dot"`: moving glow dots for active state, scanning, orbit, and general focus.
- `animation.marker: "arrow"`: moving arrowheads for forward handoff, process flow, or causal progression.
- `finish.grain`: subtle texture. Defaults to `true`.
- `finish.vignette`: edge shading. Defaults to `true` for `architecture` and `dark_technical`, otherwise `false`.
- `finish.soft_glow`: frame/module glow. Defaults to `true` for `architecture` and `dark_technical`, otherwise `false`.

Do not use these atoms as a classifier. First choose the relation/layout; then choose tone, motion marker, and finish only if they clarify the explanation.

## Block Style Overrides

Use block styles sparingly to mark emphasis, grouping, contrast, or semantic state. They are optional; omit them when the global palette already explains the diagram.

Supported keys on `steps[]`, `stages[]`, `layers[]`, `items[]`, `before`, and `after`:

- `style.accent`: primary local emphasis, such as a numbered badge or matrix point.
- `style.fill`: local block/card fill.
- `style.stroke`: local block/card border.
- `style.text`: local title or label text.
- `style.muted`: local body text.
- `style.value`: local metric/value text.
- `style.index_text`: text color inside numbered badges.

Example:

```json
{
  "layout": "timeline",
  "title": {"main": "Launch Plan"},
  "steps": [
    {
      "label": "Review",
      "body": "Catch risk",
      "style": {
        "accent": "#c026d3",
        "fill": "#fae8ff",
        "stroke": "#e879f9",
        "text": "#581c87",
        "muted": "#7e22ce"
      }
    }
  ]
}
```

## Principle-Led Workflow

1. Understand the source: claim, actors, stages, metrics, decisions, loops, and contrast.
2. Decide the relation:
   - process or sequence -> `timeline`, or `flow` only when branching is needed
   - repeated cycle -> `circular_loop`
   - narrowing/drop-off -> `funnel`
   - tradeoff/positioning -> `matrix`
   - layers/dependencies -> `stack`
   - transformation/contrast -> `before_after`
   - system with sources/pipeline/output -> `architecture`
3. Create a concise spec or Diagram IR.
4. Render and verify.

The LLM may adapt visual emphasis, labels, palette, and animation intent when it improves explanation. The renderer should not hard-code semantic judgment beyond validating structure and output.

## Diagram IR

Use Diagram IR when the source is an article, screenshot, product story, or ambiguous process rather than an already-valid render spec.

```json
{
  "diagram_ir": {
    "claim": "Refund review",
    "relation": "sequence",
    "layout_reason": "The source is a chronological review path.",
    "style": {"tone": "light_editorial"},
    "animation": {"marker": "arrow"},
    "title": {"main": "Refund Review", "subtitle": "Draft to approval"},
    "nodes": [
      {"id": "request", "label": "Request", "body": "User asks", "style": {"accent": "#2563eb"}},
      {"id": "review", "label": "Review", "body": "Team checks"}
    ]
  }
}
```

`layout_reason` records the model's rationale for choosing the layout. Node-level `style` survives compilation for supported light layouts. The renderer may preserve rationale as metadata, but drawing must depend on `layout`/compiled fields, not on prose reasoning.

Relation mapping:

- `sequence`, `process`, `timeline` -> `timeline`
- `loop`, `cycle` -> `circular_loop`
- `funnel` -> `funnel`
- `matrix`, `tradeoff` -> `matrix`
- `stack`, `layers` -> `stack`
- `before_after`, `contrast` -> `before_after`
- `architecture` -> `architecture`

## Layout Selection

- Use `circular_loop` for repeated traps, flywheels, incentive loops, metric loops, and cyclic experiences.
- Use `timeline` for chronological plans, release paths, incident sequences, and maturity stages.
- Use `funnel` for conversion, filtering, narrowing, leakage, and drop-off.
- Use `matrix` for prioritization, positioning, tradeoff maps, and impact-effort comparisons.
- Use `stack` for layers, capability stacks, dependencies, and mental models.
- Use `before_after` for transformation, contrast, migration, and manual-to-automated shifts.
- Use `architecture` for system maps with sources, core processing, decision gates, and packaged outputs.

If none fits, add a new primitive. Do not bend an unrelated primitive just to avoid code.

## `circular_loop`

```json
{
  "layout": "circular_loop",
  "title": {"main": "转移陷阱", "subtitle": "指标 ↑  体验 ↓"},
  "steps": [
    {"label": "用户遇到一个复杂问题", "badge": "入口"},
    {"label": "被推进自动化流程", "badge": "转移率 ↑"}
  ]
}
```

Recommended: 5 to 9 steps. Use `center` overrides (`x`, `y`, `radius`, `node_radius`) or `legend` overrides (`x`, `y`, `row_gap`, `width`) only when auto layout does not fit.

## `timeline`

```json
{
  "layout": "timeline",
  "animation": {"marker": "arrow"},
  "title": {"main": "Launch Plan", "subtitle": "From draft to release"},
  "steps": [
    {"label": "Draft", "body": "Shape core message"},
    {"label": "Review", "body": "Catch risk"},
    {"label": "Ship", "body": "Publish assets"}
  ]
}
```

Recommended: 3 to 7 steps. Put short explanatory detail in `body`.

## `funnel`

```json
{
  "layout": "funnel",
  "title": {"main": "Support Funnel", "subtitle": "Where users drop"},
  "stages": [
    {"label": "Visits", "value": "10k"},
    {"label": "Starts", "value": "3k"},
    {"label": "Resolved", "value": "900"}
  ]
}
```

Recommended: 3 to 6 stages. Use `value` for count, rate, or short status.

## `matrix`

```json
{
  "layout": "matrix",
  "title": {"main": "Priority Map", "subtitle": "Impact × effort"},
  "x_axis": "Effort",
  "y_axis": "Impact",
  "items": [
    {"label": "Quick win", "x": 0.25, "y": 0.78},
    {"label": "Big bet", "x": 0.76, "y": 0.72}
  ]
}
```

`x` and `y` are normalized from `0` to `1`. Keep labels short enough to sit near points.

## `stack`

```json
{
  "layout": "stack",
  "title": {"main": "Agent Layers", "subtitle": "Capability stack"},
  "layers": [
    {"label": "Interface", "body": "User request"},
    {"label": "Planner", "body": "Choose route"},
    {"label": "Renderer", "body": "Create outputs"}
  ]
}
```

Recommended: 3 to 7 layers. Order top-to-bottom in reading order.

## `before_after`

```json
{
  "layout": "before_after",
  "title": {"main": "Workflow Shift", "subtitle": "Manual to agentic"},
  "before": {"title": "Before", "items": ["Manual sorting", "Lost context"]},
  "after": {"title": "After", "items": ["Reusable memory", "Verified outputs"]}
}
```

Use for contrast where the transformation is the main point. Keep each side to 2 to 5 items.

## `architecture`

Legacy dark architecture/process layout. Use when the content is a system map with sources, core processing, a decision gate, and packaged outputs.

Primary fields:

- `signature`
- `title.prefix`, `title.highlight`, `title.subtitle`
- `inputs`
- `core.cards`
- `decision`
- `output`
- `left_panel`
- `center_panel`
- `right_panel`

Supported icon keys: `folder`, `file`, `scan`, `shield`, `db`, `hash`, `package`.

## Extending Layouts

Each new layout should provide:

- A render function returning `(Excal, Image)`.
- An animation function when generic light motion is insufficient.
- A representative test that fails before implementation.
- A sample spec under `assets/` only when it materially helps reuse.

## Verification

Run:

```bash
python scripts/render_animated_diagram.py \
  --spec assets/circular-loop-spec.json \
  --outdir /tmp/diagram-output \
  --basename diagram \
  --verify \
  --check
```

Quality bar:

- `.png`, `.gif`, and `.excalidraw` exist.
- GIF dimensions, fps, and frame count match `canvas`.
- Frame diff shows real motion.
- Excalidraw IDs are unique.
- Text elements use `fontFamily: 5`.
- `files` is empty unless embedded images were explicitly requested.
- Text stays inside the canvas and does not shrink below the minimum readability floor.
- Static PNG should be understandable before relying on GIF motion.
