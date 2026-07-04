# iysl-anidiagram Decision Gallery

This gallery teaches diagram judgment. Use it before copying any JSON shape.

## How To Use

1. Read the source brief.
2. State the claim the diagram must prove.
3. Choose the relation: sequence, loop, narrowing, ranking, tradeoff, layers, contrast, branching, system map, or multi-part story.
4. Pick the layout that makes that relation easiest to understand.
5. Borrow field syntax from `assets/*-spec.json` only after the relation is chosen.
6. Render with `--verify --check` and review the PNG by eye.

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

This table is an index, not a classifier. Do not route from Source Type or Layout columns straight to a spec; open the case's `brief.md` and `decision.md` first, state your own claim and relation, and only then compare against the case.

| Case | Source Type | Claim | Relation | Layout | Why Not |
| --- | --- | --- | --- | --- | --- |
| [01 timeline](01-launch-three-readings/) | Product launch | Launch risk falls when work is sequenced through gates | sequence | `timeline` | A funnel would hide chronology |
| [01 funnel](01-launch-three-readings/) | Product launch | Launch adoption narrows at each handoff | narrowing | `funnel` | A timeline would hide drop-off |
| [01 composite](01-launch-three-readings/) | Product launch | Launch readiness needs plan, adoption, and feedback loop together | multi-part story | `composite` | A single primitive would flatten the story |
| [02](02-chinese-training-loop/) | Chinese training note | Escalation grows through a repeating communication loop | loop | `circular_loop` | A timeline would imply it happens only once |
| [03](03-chinese-capability-stack/) | Chinese capability note | Agent work depends on layered capabilities | layers | `stack` | A flow would imply runtime order |
| [04](04-workflow-before-after/) | Workflow migration | The important story is before vs after operating mode | contrast | `before_after` | A stack would hide transformation |
| [05](05-review-branching-flow/) | Review workflow | The process branches, retries, and merges | branching | `flow` | A timeline would hide decisions |
| [06](06-technical-architecture-map/) | Technical system | Multiple sources feed a core process and output package | system map | `architecture` | A flow would underrepresent system density |
| [07 dot](07-style-motion-contrast/) | Support handoff | Active focus moves across the same process | sequence | `timeline` | Arrow motion would imply handoff more than attention |
| [07 arrow](07-style-motion-contrast/) | Support handoff | Ownership is handed forward across the same process | sequence | `timeline` | Dot motion would understate causality in the handoff story |
| [08](08-priority-matrix-anti-template/) | Prioritization | Initiatives should be compared by impact and effort | tradeoff | `matrix` | A timeline would invent fake chronology |
| [09](09-no-claim-refusal/) | Tooling reference page | None — the source asserts nothing | none | none (refused) | Any layout would invent a claim the source does not make |
| [10](10-cloud-spend-ranking/) | Cost review | Spend concentrates in compute; start cutting there | ranking | `ranking` | A funnel would invent a narrowing pipeline between independent line items |

## Adding A Case

- Every case needs a repo-owned `brief.md` (original source material, starts with an H1) and a `decision.md` with `## Primary Claim`, `## Rejected Alternatives`, and `## Validation` sections; tests enforce all of this.
- Every `spec.json` must render and pass `--verify --check`; `tests/test_gallery_examples.py` and `tools/verify-skill.sh` both enforce it.
- Render the PNG and review it by eye before committing. `--check` measures painted text collisions and canvas margins, but icon-over-label overlap, hierarchy, and overall readability still need eyes.
- A case earns its place by teaching a judgment the existing cases do not already cover, not by adding another topic for the same relation.
