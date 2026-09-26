---
name: iysl-equity-council
description: Challenge a PEI preliminary underwrite with three isolated equity-method agents when initial coverage or a material reassessment needs it.
metadata:
  compatibility: Requires agent collaboration; Python 3 is needed only to validate Council receipts.
---

# Equity Council

## Activate

Use for formal initial coverage or a formal reassessment that could materially
change assumptions, valuation, or investment direction. Use the owner-only path
for incremental refreshes; do not use Council for collection, daily monitoring,
trade overlays, or implementation work.

Before dispatch, the PEI owner must have a preliminary underwrite with valid
security identity, current price and timestamp, decision horizon, candidate
assumptions, evidence anchors, proposed Base values or ranges, and flip
conditions. Council is supporting analysis, not a separate package authority.

If collaboration is unavailable for a Council-required run, disclose the
limitation and leave the affected material assumption unresolved. Do not emulate
three seats in one response.

## Ownership

- Equity Data owns admissibility, identity, provenance, freshness, and accepted
  evidence. Council may discover sources but cannot self-admit them.
- The PEI owner owns the preliminary underwrite, adjudication, authoritative
  model, and final paper.
- Council challenges starting assumptions; it does not issue the investment
  stance, own delivery, size a position, or authorize execution.

## Protocol

After activation and before preparing any packet, read
[references/council-protocol.md](references/council-protocol.md). It is the
single contract for the three seat IDs and lenses, six assumption families,
packet and memo schemas, source discovery and admission, owner adjudication,
and stop rule.

Follow the formal-research source policy. Council performs one isolated round;
Data verifies decision-material discoveries through the existing PEI receipt;
the owner adjudicates them once. Do one targeted refill only when a remaining
gap can materially change the judgment or break essential computation. Do not
restart Council or add a review round.

## Complete

Complete Council support when all three first-round memos are sealed, their
decision-material candidates have dispositions through the existing receipt,
the owner has adjudicated the preliminary assumptions, and changed
decision-critical calculations are checked. Save the memos and adjudication as
supporting artifacts; the PEI-owned research paper is the deliverable.

Keep internal receipts out of the investor-facing paper. Historical schema v3
runs remain evidence-closed and read-only.
