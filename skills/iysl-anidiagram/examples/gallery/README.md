# iysl-anidiagram Decision Gallery

This gallery teaches diagram judgment. Use it to reason about a source, not as a set of SVGs to copy.

## How To Use

1. Read the source brief.
2. State the claim the diagram must prove.
3. Choose the relation: sequence, loop, narrowing, ranking, tradeoff, layers, contrast, branching, system map, or multi-part story.
4. Choose the composition that makes that relation easiest to understand, following `references/svg-authoring.md`.
5. Choose the animation story last, grounded in `references/animation-semantics.md` — motion must encode the relation.
6. Render with `scripts/render_svg.py --check` and review the poster PNG and MP4 frames by eye.

## Source-Backed Heuristics

- FT Visual Vocabulary: choose the relationship most important to the story before choosing a visual form.
- NN/g chart selection: fit the visual to the goal and context, not to a favorite shape.
- NN/g context, clutter, contrast: preserve needed context, remove non-explanatory clutter, and use contrast only to clarify the takeaway.
- NN/g proximity: related items should be visually close; unrelated groups need whitespace or region separation.

Sources:
- https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md
- https://journalismcourses.org/wp-content/uploads/2020/07/Visual-vocabulary.pdf
- https://www.nngroup.com/articles/choosing-chart-types/
- https://www.nngroup.com/videos/better-charts-analytics-quantitative-ux-data/
- https://www.nngroup.com/articles/gestalt-proximity/

## Cases

This table is an index, not a classifier. Do not route from Source Type or Relation columns straight to a diagram; open the case's `brief.md`, `direction.md`, and `decision.md` first, state your own claim and relation, and only then compare against the case.

| Case | Source Type | Claim | Relation | Motion | Why Not |
| --- | --- | --- | --- | --- | --- |
| [02](02-chinese-training-loop/) | Chinese training note | Escalation grows through a repeating communication loop | loop | closed-path cycle | A linear sequence would imply it happens only once |
| [04](04-workflow-before-after/) | Workflow migration | The important story is before vs after operating mode | contrast | paired-row alternation | A single sequence would hide the transformation |
| [05](05-review-branching-flow/) | Review workflow | The process branches, retries, and merges | branching | branch-and-retry reveal | A straight timeline would hide the decisions |
| [07 dot](07-style-motion-contrast/) | Support handoff | Active focus moves across the same process | sequence | focus dot | Arrow motion would imply handoff more than attention |
| [07 arrow](07-style-motion-contrast/) | Support handoff | Ownership is handed forward across the same process | sequence | forward-handoff arrows | Dot motion would understate the causality in the handoff story |
| [09](09-no-claim-refusal/) | Tooling reference page | None — the source asserts nothing | none | none (refused) | Any diagram would invent a claim the source does not make |

The 07 pair is the anti-template lesson: one brief, one relation, two motion stories that change the emphasis without changing the composition.

## Adding A Case

- Every case needs a repo-owned `brief.md` (original source material, starts with an H1), a `direction.md` (claim, relation, audience, the `F1..Fn` fact list, and the animation story), and a `decision.md` with `## Primary Claim`, `## Rejected Alternatives`, and `## Validation` sections; tests enforce the structure.
- Every `diagram.svg` must pass `scripts/render_svg.py --check` (exit 0); `tests/test_gallery_examples.py` renders each one and enforces it.
- Render the poster PNG and MP4 frames and review by eye before committing. `--check` measures text collisions and canvas margins, but hierarchy, density, and whether the poster reads on its own still need eyes.
- A case earns its place by teaching a judgment the existing cases do not already cover, not by adding another topic for the same relation.
