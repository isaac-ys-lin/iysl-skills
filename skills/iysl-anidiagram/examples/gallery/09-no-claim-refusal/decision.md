# Decision

## Source Type

Internal reference page listing squads, tools, owners, and renewal months.

## Primary Claim

None. The page asserts nothing; it exists for lookup. Every candidate claim ("tooling overlaps across squads", "renewals cluster in Q3") would be invented by the diagram author, not extracted from the source.

## Relation

None chosen. Without a claim there is no relation to encode, and the decision ladder stops at step 1.

## Layout

None. The correct deliverable is a question back to the requester: "What should a reader learn from this page — overlap, cost timing, ownership gaps?" A real answer restarts the ladder with an actual claim.

## Why This Fits

The gallery's core rule is that layout follows claim. This case shows the rule's boundary condition: when no claim exists, refusing is the judgment, and any diagram produced anyway would decorate data rather than explain it. A matrix of squads-versus-tools would look organized while asserting a comparison nobody made.

## Rejected Alternatives

A `stack` would invent dependency between squads. A `matrix` would invent a tradeoff axis. A `composite` "overview page" is the most tempting failure: it looks neutral but silently promotes lookup data into claims. Rendering the table as-is in diagram form adds animation cost and subtracts searchability.

## Style And Animation

Not applicable. If the requester later names a claim (for example, "renewal months cluster and we should stagger them"), style and motion choices start from that claim, not from this page.

## Validation

There is no spec to render. Validation for this case is behavioral: given a claim-free source, the skill should respond with the refusal-and-question above rather than a spec. Tests assert this case documents the refusal without a `spec.json`.
