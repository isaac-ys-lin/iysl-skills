# iysl-anidiagram Gallery And Freedom Contract Design

## Goal

Improve `iysl-anidiagram` so examples teach diagram judgment instead of becoming rigid templates. The skill should keep deterministic rendering and validation, while giving the model more freedom to choose relation, density, tone, emphasis, and animation based on the source material.

## Problem

The current skill already says the content should choose the structure, and that `assets/*-spec.json` are quality anchors rather than templates. In practice, the repository has one main JSON sample per primitive, so a model can easily treat those samples as the expected visual output. That creates three risks:

- Outputs converge into similar-looking diagrams even when the source story differs.
- The model copies layout samples before deciding the underlying relation.
- "More freedom" becomes vague, because the skill describes latitude but does not demonstrate it.

## Source-Backed Judgment Logic

The gallery will use outside sources only to strengthen decision logic, not to copy templates, artwork, or proprietary visual systems.

- The Financial Times Visual Vocabulary starts from the relationship most important to the story, then considers suitable visual forms. This supports anidiagram's relation-first decision ladder: claim -> relation -> layout -> style atoms -> validation. Source: <https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md> and <https://journalismcourses.org/wp-content/uploads/2020/07/Visual-vocabulary.pdf>.
- NN/g's chart-selection guidance emphasizes choosing the chart that fits the goal and presentation context, not picking a visual form in isolation. This maps to gallery cases that include claim, rejected alternatives, and why a layout serves the message. Source: <https://www.nngroup.com/articles/choosing-chart-types/>.
- NN/g's context, clutter, and contrast framing supports a quality rule for every gallery item: preserve enough context, remove non-explanatory clutter, and use contrast only to clarify the takeaway. Source: <https://www.nngroup.com/videos/better-charts-analytics-quantitative-ux-data/>.
- NN/g's proximity principle supports grouping rules for composite, flow, stack, and architecture diagrams: related elements should be visually closer, and unrelated groups need whitespace or region separation. Source: <https://www.nngroup.com/articles/gestalt-proximity/>.

These sources become design heuristics, not new schema requirements.

## Proposed Architecture

Keep the existing separation:

- `assets/`: renderer contract specs. These should remain compact examples that prove each layout's supported fields and output checks.
- `references/spec-format.md`: schema and renderer behavior.
- `SKILL.md`: agent workflow, design latitude rules, and validation requirements.

Add a new layer:

- `examples/gallery/`: curated decision examples. Each example shows how a source brief becomes a diagram through explicit judgment.

Recommended gallery item shape:

```text
examples/gallery/01-launch-three-readings/
  brief.md
  timeline/spec.json
  funnel/spec.json
  composite/spec.json
  decision.md
```

Recommended fields in `decision.md`:

- Source type
- Primary claim
- Relation chosen
- Layout chosen
- Why this layout fits
- Rejected alternatives
- Style and animation choices
- Validation command

## First Gallery Scope

Start with 8-12 high-quality cases rather than a large template library.

- Same source, different claims: one product launch brief rendered as timeline, funnel, and composite.
- Chinese explanatory content: loop, stack, and before/after examples using Traditional Chinese labels and realistic training-note density.
- System workflow: flow and architecture examples that show when branching/process logic needs `flow`, and when a dense system map needs `architecture`.
- Style freedom: at least two cases showing the same semantic layout with different tone or animation choices, such as arrow motion for handoff and dot motion for active focus.
- Anti-template cases: examples that explicitly reject a tempting layout and explain why.

The first gallery should be original, repo-owned content. Web sources inform the decision rubric; gallery briefs should be synthesized from common use cases or local project-neutral scenarios, not copied from articles.

## Design Latitude Contract

Add a concise contract to `SKILL.md`:

1. Extract the claim before choosing the layout.
2. Choose relation first: sequence, loop, narrowing, tradeoff, layers, contrast, branching, system map, or multi-part story.
3. Use gallery examples for judgment patterns, not visual copying.
4. Use `assets/*-spec.json` only to confirm valid fields and renderer contracts.
5. Vary label density, grouping, emphasis, tone, and animation when it clarifies the source.
6. Do not use style atoms as a classifier; choose style after relation and layout.
7. If no primitive fits, extend the renderer with tests instead of distorting an unrelated layout.
8. Always render with `--verify --check` and human-review the PNG for hierarchy, overlap, clipping, and readability.

## Validation

Add a gallery validation path that renders every `examples/gallery/**/spec.json`.

Expected command shape:

```bash
python3 skills/iysl-anidiagram/scripts/render_animated_diagram.py \
  --spec examples/gallery/.../spec.json \
  --outdir /tmp/iysl-anidiagram-gallery-check \
  --basename gallery-item \
  --verify \
  --check
```

Preferred implementation is a small repo-owned script or pytest case so future gallery additions cannot silently rot.

## Non-Goals

- Do not import external visual templates.
- Do not weaken renderer validation to allow freer but unverifiable output.
- Do not turn every gallery case into a new schema variant.
- Do not generate final PNG/GIF assets into the repository unless there is a separate packaging decision.
- Do not add a new primitive in this pass unless a gallery case proves current primitives are insufficient.

## Implementation Plan Preview

After this design is approved:

1. Add `.superpowers/` to `.gitignore` so visual companion artifacts stay out of commits.
2. Create `examples/gallery/README.md` with the gallery index and selection rubric.
3. Add the first 8-12 gallery cases with `brief.md`, `decision.md`, and checked `spec.json`.
4. Update `SKILL.md` with the Design Latitude Contract and gallery usage order.
5. Update `references/spec-format.md` to clarify assets vs gallery.
6. Add automated gallery validation.
7. Run tests and render/check the gallery.

## Open Decision

The main remaining choice is gallery size for the first implementation. Recommendation: 9 cases. This is enough to cover relation variety, Chinese examples, style latitude, and anti-template reasoning without making the first pass heavy or repetitive.
