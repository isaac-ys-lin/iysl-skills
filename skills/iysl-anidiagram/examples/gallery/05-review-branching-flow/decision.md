# Decision

## Source Type

Review workflow brief with approval, retry, escalation, and merge behavior.

## Primary Claim

The process matters because it branches on review outcomes, allows retries, and rejoins at merge.

## Relation

Branching process with loop-back and merge.

## Layout

`flow`

## Why This Fits

The reader must see where judgment changes the path. A flow layout can show the main route, alternate branches, and a clean return from revision without pretending the process is linear.

## Rejected Alternatives

A `timeline` would hide the decisions that determine the next step. A `before_after` view would erase the operational logic. An `architecture` layout would add unnecessary density for a process whose main value is branch clarity.

## Style And Animation

Keep the diagram compact and operational. Motion should follow the main path first, then reveal retry and escalation branches so the reader learns the default route before the exceptions.

## Validation

Confirm the source brief genuinely needs branching, not just sequence. The spec must pass `--verify --check`, keep node and branch density low enough that labels remain readable at a glance, and still read clearly in PNG form with branch labels visible.
