# Decision

## Source Type

Product launch brief for a cross-functional rollout review.

## Primary Claim

The same source can support three valid claims: risk falls when gates are sequenced, adoption narrows at each handoff, or launch readiness requires several connected readings on one page.

## Relation

This case intentionally spans three relations. `timeline` serves sequence, `funnel` serves narrowing, and `composite` serves a multi-part story with more than one supporting relation.

## Layout

Use `timeline` when the review question is "what must happen in order." Use `funnel` when the question is "where does the audience shrink." Use `composite` when the page must carry launch plan, adoption shape, and feedback path together without pretending they are one single primitive.

## Why This Fits

This case teaches that layout choice follows the claim, not the topic label. All three diagrams can be about the same launch, but they answer different review questions. That makes it a clean gallery anchor for relation-first judgment.

## Rejected Alternatives

A single default diagram would collapse distinct meanings into one shape. A matrix would invent a tradeoff that is not the core story. A loop on its own would overstate repetition and underplay launch gating. Using only a timeline would hide drop-off; using only a funnel would hide chronology.

## Style And Animation

Keep the visual language calm and operational. Timeline motion should emphasize forward movement through gates. Funnel motion should emphasize narrowing and leakage. Composite motion should stay restrained so each section remains readable as a static page before animation adds emphasis.

## Validation

Confirm this shared decision explains all three spec variants: `timeline/spec.json`, `funnel/spec.json`, and `composite/spec.json`. Each spec must render with `--verify --check` and still read clearly in the PNG without motion.
