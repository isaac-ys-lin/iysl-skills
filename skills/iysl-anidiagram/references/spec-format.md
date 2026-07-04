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

- `layout`: choose the visual primitive. Supported: `circular_loop`, `timeline`, `funnel`, `matrix`, `stack`, `before_after`, `flow`, `composite`, `architecture`.
- `canvas`: output dimensions and GIF timing.
- `palette`: optional override for both tones. Keys: `background`, `primary`, `muted`, `border`, `chip`, `text`. Under `dark_technical` the defaults come from the dark theme; `chip` also feeds `primary_soft` unless `primary_soft` is set explicitly.
- Block-level `style`: optional override for a specific step, card, point, stage, or contrast block.
- `animation.marker`: optional for light layouts; use `arrow` when motion should imply forward handoff instead of moving dots.
- `style.tone`: optional; use `light_editorial` by default, or `dark_technical` when the source calls for Lanshu/DailyDoseOfDS-style black technical sketches.
- `finish`: optional visual finish atoms. Supported keys: `grain`, `vignette`, `soft_glow`.
- Keep labels short. Text fitting is a safety net, not a substitute for editing.

### Validation

The renderer validates every spec before drawing. An unknown `layout` is an error (CLI exits `2` with a `messages` list); it never silently falls back. A spec with no `layout` is accepted only when it is architecture-shaped, meaning it has at least one of: `signature`, `inputs`, `input_title`, `core`, `decision`, `output`, `left_panel`, `center_panel`, `right_panel`, `loop_label`, `retry_label`. Each layout also requires its content field (for example `funnel` requires `stages` or `steps`); missing fields are reported per layout, and composite errors name the section, like `sections[1] (funnel): ...`.

## Assets Versus Gallery

- `assets/*-spec.json` are compact renderer contract samples. Use them to confirm field names, supported layout structures, and output checks.
- `examples/gallery/` contains decision examples. Use these to understand how a source brief, claim, relation, rejected alternatives, and style choices lead to a spec.
- Do not copy a gallery spec as a template before stating the claim and relation. The gallery demonstrates judgment; the renderer validates contracts.

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
2. Pick the layout per the Layout Selection section below.
3. Create a concise spec or Diagram IR.
4. Render and verify.

Decision ladder:

1. Claim: what should the reader understand first? If the source yields no claim, stop and say a diagram is not warranted instead of inventing one (see `examples/gallery/09-no-claim-refusal/`).
2. Relation: sequence, loop, narrowing, ranking, tradeoff, layers, contrast, branching, system map, or multi-part story.
3. Layout: choose the primitive that makes that relation easiest to scan.
4. Emphasis: choose density, grouping, tone, motion marker, and block styles.
5. Validation: render, run `--check`, and review the PNG by eye.

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
- `ranking`, `magnitude` -> `ranking`
- `matrix`, `tradeoff` -> `matrix`
- `stack`, `layers` -> `stack`
- `before_after`, `contrast` -> `before_after`
- `flow`, `branch`, `decision` -> `flow`
- `composite`, `story` -> `composite`
- `architecture` -> `architecture`

For `flow`, the IR accepts an optional `edges` array (same shape as the spec's) next to `nodes`; without it the nodes compile to a sequential chain. For `composite`, the IR carries a `sections` array of sub-IRs, each with its own `relation` and `nodes` plus optional `span`/`height`; nested composite sections are rejected.

## Layout Selection

- Use `circular_loop` for repeated traps, flywheels, incentive loops, metric loops, and cyclic experiences.
- Use `timeline` for chronological plans, release paths, incident sequences, and maturity stages.
- Use `funnel` for conversion, filtering, narrowing, leakage, and drop-off.
- Use `ranking` for magnitude comparison of independent parallel quantities (spend, volume, frequency); a funnel's shrinking bars assert one narrowing population, a ranking's do not.
- Use `matrix` for prioritization, positioning, tradeoff maps, and impact-effort comparisons.
- Use `stack` for layers, capability stacks, dependencies, and mental models.
- Use `before_after` for transformation, contrast, migration, and manual-to-automated shifts.
- Use `flow` for branching decisions, retry/loop-back, escalation, and merge paths; prefer `timeline` when the path is linear.
- Use `composite` when the source tells a multi-part story that needs several primitives on one page (for example timeline + funnel + loop).
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

## `ranking`

```json
{
  "layout": "ranking",
  "title": {"main": "Spend by Service", "subtitle": "Monthly, sorted"},
  "items": [
    {"label": "Compute", "value": 42, "display": "42k"},
    {"label": "Storage", "value": 18, "display": "18k"},
    {"label": "Network", "value": 9, "display": "9k"}
  ]
}
```

Numeric `value` (non-negative) sets bar length; optional `display` overrides the printed value. Items render sorted descending by default; set `"sort": "none"` to keep spec order. Recommended: 3 to 8 items with short labels.

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

## `flow`

```json
{
  "layout": "flow",
  "title": {"main": "Refund Review Flow", "subtitle": "Gate on policy, retry with evidence"},
  "nodes": [
    {"id": "submit", "label": "Submit request", "kind": "start"},
    {"id": "triage", "label": "Auto triage", "body": "Dedupe, attach history"},
    {"id": "gate", "label": "Passes policy?", "kind": "decision"},
    {"id": "fix", "label": "Request evidence", "lane": "right"},
    {"id": "ship", "label": "Refund issued", "kind": "end"}
  ],
  "edges": [
    {"from": "submit", "to": "triage"},
    {"from": "triage", "to": "gate"},
    {"from": "gate", "to": "ship", "label": "yes"},
    {"from": "gate", "to": "fix", "label": "no"},
    {"from": "fix", "to": "triage", "kind": "retry", "label": "resubmit"}
  ]
}
```

- `nodes[].id`: required and unique; edges reference it.
- `nodes[].kind`: `step` (default card), `decision` (diamond), `start`/`end` (accent pill).
- `nodes[].lane`: `main` (default), `left`, or `right` for branch targets.
- `edges` are optional; omitting them chains the nodes in order (prefer `timeline` then). `kind: "retry"` renders dashed through the outer gutter; `label` becomes a badge on the edge. Forward edges must be acyclic; mark loop-backs as `kind: "retry"`.
- Rows come from the longest forward path (retry edges excluded, so loop-backs are safe). Two nodes on the same lane and row offset by half a row — keep it to 8 nodes or fewer and prefer full-width regions.

Animation: the marker travels the main spine, retry edges get dimmer offset dots, and the active node pulses — faster when it is a decision.

## `composite`

One infographic page that stacks several primitives as sections. Use it for multi-part stories; every section keeps one claim and the page title carries the umbrella story.

```json
{
  "layout": "composite",
  "title": {"main": "Atlas 2.0 Launch, One Page", "subtitle": "Plan, adoption, retention"},
  "canvas": {"width": 1210},
  "sections": [
    {"span": "full", "height": 400, "layout": "timeline", "title": "Rollout path",
     "steps": [{"label": "Beta"}, {"label": "GA"}]},
    {"span": "half", "height": 560, "layout": "funnel", "title": "Launch funnel",
     "stages": [{"label": "Visits", "value": "48k"}]},
    {"span": "half", "height": 560, "layout": "circular_loop", "title": "Retention loop",
     "steps": [{"label": "Build"}, {"label": "Share"}]}
  ]
}
```

- A section is any composable layout's spec fields inlined, plus `span`, `height`, and string `title`/`subtitle` (which become the sub-diagram's own title — there is no separate heading element).
- Composable layouts: `circular_loop`, `timeline`, `funnel`, `ranking`, `matrix`, `stack`, `before_after`, `flow`. Nested `composite` and `architecture` sections are rejected.
- Arrangement: sections stack in order; a `half` pairs with the immediately following `half`, an orphan `half` is promoted to full width, and a row is as tall as its tallest cell. Margins/gutters are fixed (36/28) with a 118px page title block.
- Page height is computed from the rows — setting `canvas.height` on a composite is a validation error. Width defaults to 1210.
- `style`, `palette`, and `animation` inherit page -> section; a section key wins wholesale. `finish` applies once at page level only.
- Each section must meet its layout's minimum region (generally 360x260; `circular_loop` needs 420x420) or validation fails. Keep pages to about 5 sections; half columns are ~560px wide.
- Animation defaults for composite are `frames: 36, fps: 10` (sections activate sequentially, each playing its own animation during its slice, with a pulsing outline on the active section). Keep `1000/fps` a multiple of 10 or the GIF fps check fails; drop `frames` to 24 first if file size matters.

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

Everything mechanical (files exist, dimensions/fps/frames match, motion is nonzero, Excalidraw ids unique, fonts, text bounds, composite regions) is enforced by `--check` — read its JSON output for the full list. Exit codes: `0` ok, `1` a check failed, `2` invalid spec.

`--check` also measures the actually painted text boxes (not the estimated Excalidraw widths):

- `readability_text_collision` fails when two painted text boxes overlap by more than `quality.collision_tolerance` px on both axes (default 2).
- `readability_canvas_margin` fails when any painted text or shape sits closer than `quality.margin` px to the canvas edge (default 8).
- Both knobs live under a top-level `"quality"` object; raise or lower them per spec only with a reason, not to silence a real collision.

What `--check` still cannot verify, review by eye on the PNG:

- The static PNG is understandable before relying on GIF motion.
- Icons or decorations covering a label (shape-over-text is legitimate for cards, so it is not machine-checked).
- Cramped badges or misleading hierarchy.
