# Decision

## Source Type

Support handoff brief with one shared process and two different emphasis goals.

## Primary Claim

The same timeline can communicate either active focus moving across work or ownership being handed forward, depending on the animation and emphasis choice.

## Relation

Sequence in both versions, with emphasis changing between focus-tracking and handoff causality.

## Layout

`timeline`

## Why This Fits

The semantic structure stays linear in both readings, so the layout does not need to change. What changes is the explanatory job of motion: a moving dot supports "where attention is now," while an arrowed advance better signals "this stage hands the work to the next owner."

## Rejected Alternatives

A `flow` would suggest branching decisions that are not present. A `composite` would add weight without adding meaning. Switching to different primitives for the two readings would hide the gallery lesson that style and animation can vary inside one chosen relation.

## Style And Animation

Keep two spec variants: dot motion for active focus and arrow motion for forward handoff. Keep labels and stage order identical so the contrast is attributable to motion intent rather than content drift.

## Validation

Confirm one brief can support two motion readings on the same semantic path. Both `dot/spec.json` and `arrow/spec.json` must pass `--verify --check`, and the PNGs should still look like the same process with different emphasis.
