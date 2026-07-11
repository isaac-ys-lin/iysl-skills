# Decision

## Source Type

Support handoff brief with one shared process and two different emphasis goals.

## Primary Claim

The same timeline can communicate either active focus moving across work or ownership being handed forward, depending on the animation and emphasis choice.

## Relation

Sequence in both versions, with emphasis changing between focus-tracking and handoff causality.

## Composition

A shared four-card timeline keeps stage order, owners, labels, spacing, and connectors identical in both variants. This controls the semantic layout so only the motion story changes.

## Why This Fits

The semantic structure stays linear in both readings, so the layout does not need to change. What changes is the explanatory job of motion: a moving dot supports "where attention is now," while an arrowed advance better signals "this stage hands the work to the next owner."

## Rejected Alternatives

A branching flow would invent decisions that are not present. A multi-panel comparison would add weight without adding meaning. Switching primitives or coordinates between variants would hide the gallery lesson by conflating layout change with motion change.

## Motion Semantics

- `dot/diagram.svg`: only one node pulses at a time. The pulse encodes active focus — “attention is here now” — and advances in stage order.
- `arrow/diagram.svg`: only one transfer arrow is active at a time. It travels forward across a connector and encodes explicit ownership handoff from one role to the next.

Both use an eight-second loop with two-second reading states. Their static diagrams remain complete without motion.

## Coverage

| Fact | Dot variant | Arrow variant |
| --- | --- | --- |
| F1 four ordered stages | Four numbered cards, left to right | Same four numbered cards, left to right |
| F2–F5 stage owners | Owner badge inside every card | Same owner badge inside every card |
| F6 active attention reading | Single sequential focus ring | Preserved in title contrast, not encoded by arrow motion |
| F7 ownership handoff reading | Preserved in title contrast, not encoded by pulse motion | Single forward-moving arrow across each connector |
| F8 identical semantic layout | Shared coordinates, labels, colors, and connectors | Shared coordinates, labels, colors, and connectors |

## Validation

Each SVG must pass `scripts/render_svg.py --check` with exit 0. Review the poster PNG and timeline frames to confirm that both remain recognizably the same process while the dot reads as current focus and the arrow reads as forward ownership transfer.
