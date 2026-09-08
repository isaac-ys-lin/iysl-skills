---
name: iysl-equity-council
description: Challenge a PEI preliminary underwrite with three isolated equity-method agents when initial coverage or a material reassessment needs it.
metadata:
  compatibility: Requires agent collaboration and Python 3 for the current Council receipt validator.
---

# Equity Council

## Outcome

Challenge the assumptions in a PEI preliminary underwrite before the owner model
is finalized when this skill is activated. Run three isolated public-method
agents in parallel:

- `Aswath Damodaran — Fundamental Committee Member`
- `George Soros — Reflexivity Committee Member`
- `Michael Mauboussin — Expectations Committee Member`

They are analytical lenses, not the actual people, endorsements, private-process
claims, current positions, or evidence authorities. They propose corrections;
the same PEI／primary-model owner accepts, conditionally accepts, or rejects each
material challenge. Council does not issue the final investment stance and does
not own the paper.

This skill is advisory only. It does not size a position, place an order, or
authorize execution.

## Activation boundary

Use this skill for formal initial coverage, or a formal reassessment that could
materially change assumptions, valuation, or investment direction, after Equity Data has produced a sufficient context
and the PEI owner has written a structured preliminary underwrite. Routine
incremental refreshes remain owner-only. Do not use it for data collection,
daily monitoring, trade overlays, or implementation work.

Require before dispatch:

1. valid security identity;
2. current price with as-of timestamp;
3. explicit decision horizon;
4. a preliminary underwrite owned by PEI; and
5. a preliminary underwrite with candidate assumptions, evidence anchors,
   proposed Base values or ranges, and flip conditions.

The preliminary underwrite covers each materially load-bearing family or gives
an explicit non-material disposition: revenue and order conversion; product mix
and operating margin; reinvestment and FCFF conversion; capital structure and
WACC; explicit growth duration, competitive-advantage fade, and terminal
economics; and the 12-month earnings path and market-implied expectations. This
is aggregate investment judgment, not a second registry for every formula cell.

Before dispatch, confirm the preliminary underwrite identifies the security,
cutoff, candidate assumptions and evidence anchors. Council output is supporting
analysis, not a separate package authority.

If agent collaboration is unavailable for a Council-required run, disclose the
limitation and leave the affected material assumption unresolved; do
not emulate three seats in one response. Routine owner-only work is unaffected.

## Ownership

- Equity Data owns admissibility, identity, provenance, freshness, and accepted
  evidence. Council can independently discover sources; it cannot self-admit them.
- The PEI owner owns the preliminary underwrite, adjudication, authoritative
  model, and final paper.
- Council agents challenge the starting assumptions and may discover supporting or opposing original sources under the project source policy.
- Council does not create a second investment conclusion or delivery authority.

## Workflow

1. Build one packet per seat from the accepted evidence and the same candidate
   assumptions. Material Ask SA, Analysis, or Transcript challenge signals enter
   only after the PEI owner records each one under the affected
   `candidate_assumptions[].challenge_signal_dispositions` with provenance,
   finding, `adopt`／`reject`／`not_material`, accepted supporting evidence IDs,
   reason, and flip condition. Ask SA remains `provider_synthesis` and cannot
   use itself as supporting evidence. Do not add raw Ask SA or a root-level
   parallel signal schema. Each packet includes only identity, cutoff, horizon,
   relevant evidence IDs, and instructions. Do not include a final model, fair
   value, action, position, or another seat's output.
2. Read [references/council-protocol.md](references/council-protocol.md). Spawn
   three parallel leaf agents. They receive the same starting evidence and may
   independently browse or use Exa under the formal workflow source policy.
   They may not read other seats' outputs or delegate. Search and challenge
   happen in this one round, with no separate scout phase.
3. Seal each memo with its exact packet hash. A memo challenges assumptions and
   states evidence, reasoning, decision impact, falsifier, and limitations. It
   may propose a Base value or range, but it does not calculate the final model
   or choose `Long`／`Short`／`Avoid`／`Pass`. Every seat tests what may be too
   conservative, too aggressive, or uncertain and states its strongest
   evidence-consistent market-right countercase; no seat is assigned a fixed
   Bull or Bear conclusion. Check material omissions under the protocol as well
   as the assumptions already listed.
4. Return all three sealed memos to the same PEI owner. Equity Data checks
   decision-material source candidates and admits supported originals through
   the existing PEI receipt; the owner records accepted/rejected/not-material
   source dispositions. Preserve the starting receipt and sealed packets.
   For every preliminary
   assumption, record `accept`／`conditional`／`reject`, the final Base/range,
   cited evidence, reason, and model input IDs.
   Apply the formal workflow's assumption-formation rule through the packet
   instructions in the Council protocol; do not add another review round.

5. If an unresolved gap could materially change the judgment, do one targeted
   upstream refill. Then deliver a defensible estimate or conditional scenarios;
   unsupported central values stay unresolved rather than becoming conservative
   placeholders. Do not restart Council.
6. Calculate one authoritative owner model and let the PEI owner update the
   final research paper. Recheck only changed decision-critical calculations;
   Prioritize the requested-horizon probability-weighted target and total return.
   Explain operating outcomes, how the market may price them, and subjective
   probability reasoning. Base and current intrinsic value remain distinct
   references; inspect unsupported low upside weights as well as model haircuts.
7. Save the three memos and owner adjudication as supporting artifacts. Do not
   create a receipt DAG, closure/seal gate, or second content authority.

## Invariants

- Exactly three isolated agents run whenever this Council is activated.
- First-round memos stay sealed until all three complete.
- New runs use schema v4: truthful `browsed`, candidate sources separate from
  accepted evidence. Schema v3 remains evidence-closed for historical runs.
- Names and public methods shape questions, never source weight.
- Missing scenario probabilities do not imply `Avoid`.
- Council disagreement is not averaged. The owner explains each adjudication.
- No mandatory second round, cross-examination, probability matrix, mechanism
  taxonomy, persona-convergence score, or post-model Chair exists in current
  formal research.
- A PM-style horizon review may be requested separately after research, but it
  cannot alter the frozen model or serve as formal closure authority.
- Keep internal receipts out of the investor-facing paper.

## Output

The final deliverable is the PEI-owned full research paper, not a Council
verdict block. Council remains visible through the paper's assumption changes,
strongest countercase, unresolved limitations, and model-linked reasoning.

### Model linkage

Map each adjudicated assumption to the actual owner model fields of the same economic meaning and the applicable Base period. Multiple period decisions may share one model path; structural inputs need model provenance but need not be forced into an unrelated Council decision. The owner checks changed decision-critical calculations before publication. Council support stays outside the reader package.
