# Animation Semantics Contract

Motion in an animated diagram must encode the content relation. Animation is part of
the argument, not decoration: a mismatched motion pattern is a review failure, exactly
like a wrong label. Before animating anything, name the relation the diagram claims,
then pick the matching motion pattern below.

## Relation-to-Motion Table

| Relation | Required motion | Anti-patterns |
| --- | --- | --- |
| **Sequence / process** | Staged reveal in step order, or an arrow/particle advancing along the main line. Direction stays consistent from first to last step. | Steps appearing out of order; motion running against the reading direction. |
| **Loop / cycle** | Continuous circulation with no visible start/end seam: an element travels a closed path, or nodes are emphasized in ring order, wrapping around forever. | A linear sweep; any one-directional motion that visibly "finishes" — a cycle never finishes. |
| **Branching / decision** | Branch paths light up in turn; the decision node gets the emphasis pulse. Retry/fallback edges animate as a backflow toward the earlier node. | Animating all branches simultaneously (hides the either/or); ignoring the decision point. |
| **Contrast / before-after** | Alternating emphasis between the two sides, or a transition wipe/slide from one state to the other. | A single flowing dot on one side only — that reads as process, not contrast. |
| **Narrowing / funnel** | Stage-by-stage convergence that visualizes volume shrinking: each stage reveals smaller/denser than the last, or particles drop out at each gate. | Uniform reveal that hides the attrition; motion that grows instead of narrows. |
| **Ranking** | Bars/values growing to their magnitude, or items called out one by one in rank order. Ranking encodes magnitude and order, not causation. | Flow arrows between ranks — ranking is not a process; do not imply steps. |
| **Layers / stack** | Layer-by-layer reveal from bottom to top (or along the dependency direction), each layer settling before the next appears. | Random-order reveal; animating layers as if data flows through them when the claim is composition. |
| **System map** | Data-flow particles traveling along edges, with a clear source -> processing -> output direction. Edge motion direction must match the real data direction. | Particles moving both ways on a one-way edge; edges pulsing with no direction. |
| **Focus / emphasis** | A single pulse (scale/glow/opacity) on one element, meaning "this is the current point". | Pulsing multiple elements at once; using pulse as generic decoration. |

## Universal Anti-Patterns

These fail review regardless of relation:

- **Decorative motion**: any animation that explains nothing. If removing the motion
  loses no meaning, remove the motion.
- **Multiple simultaneous animation stories**: at any moment the viewer should be
  able to say what the animation is currently explaining. Two unrelated motions at
  once means neither is read.
- **Pacing faster than reading**: every reveal segment must hold for at least 1.2
  seconds so its label can actually be read. If the loop cannot fit all steps at a
  readable pace, cut steps or lengthen `data-loop-seconds` — never speed past the
  labels.

## Review Question

For each animated element, answer: *which relation does this motion encode, and would
a viewer infer that relation from the motion alone?* If the answer names no relation
from the table, or names a different one than the diagram claims, the animation is
wrong even if it looks polished.
