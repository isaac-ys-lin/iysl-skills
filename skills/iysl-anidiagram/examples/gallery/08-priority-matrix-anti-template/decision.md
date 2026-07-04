# Decision

## Source Type

Prioritization brief for roadmap initiatives compared by impact and effort.

## Primary Claim

The initiatives should be judged by tradeoff position, not by an invented order of execution.

## Relation

Tradeoff comparison across two dimensions.

## Layout

`matrix`

## Why This Fits

The reader needs to compare initiatives against impact and effort at the same time. A matrix makes the decision surface explicit and helps the team discuss tradeoffs, not sequence theater.

## Rejected Alternatives

A `timeline` would invent fake chronology and imply that one item naturally comes before another. A `funnel` would imply progressive filtering of the same population. A `stack` would imply dependency layers instead of planning tradeoffs.

## Style And Animation

Keep the chart honest and compact. Use emphasis to make quadrant reading easy, but avoid decorative motion that suggests momentum or inevitability. Any animation should support scanning by quadrant, not imply a process.

## Validation

Confirm the source has true impact/effort tradeoffs and no meaningful chronology. The matrix spec must pass `--verify --check`, and static review should confirm the layout does not accidentally read like a sequence.
