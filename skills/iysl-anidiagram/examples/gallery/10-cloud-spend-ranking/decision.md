# Decision

## Source Type

Quarterly cost review with independent spend line items per service.

## Primary Claim

Spend concentrates heavily in compute; cost-cutting conversations should start there, not spread evenly across services.

## Relation

Ranking by magnitude. The items are independent parallel quantities compared against each other; nothing narrows, cycles, or depends on anything else.

## Layout

`ranking`

## Why This Fits

The reader's question is "which is biggest and by how much." Sorted horizontal bars make the concentration visible at a glance, and the shared baseline makes the 42k-versus-4k gap honest. Bar length is the only encoding, which matches a single-dimension comparison.

## Rejected Alternatives

A `funnel` is the tempting mistake: it also draws shrinking bars, but a funnel asserts that one population narrows through stages, and these services are not stages of anything — using it would invent a pipeline. A `matrix` needs a second real dimension, and this source only has one. A `stack` would invent dependency between billing line items.

## Style And Animation

Keep bars in one calm color family so length stays the only signal; per-item accents are reserved for flagging a single item under discussion. Motion should sweep attention down the ranking order rather than animate bar growth theatrically.

## Validation

Confirm the source quantities are independent parallel magnitudes, not stages of one population — that distinction is what separates `ranking` from `funnel`. The spec must pass `--verify --check`, and the static PNG must keep the shared baseline and value column readable.
