---
name: iysl-equity-council
description: Challenge a PEI preliminary underwrite with exactly three isolated equity-method agents before the same PEI owner commits the model.
compatibility: Requires agent collaboration and Python 3 for the current Council receipt validator.
---

# Equity Council

## Outcome

Challenge the assumptions in a PEI preliminary underwrite before the owner model
is calculated. Run exactly three isolated public-method agents in parallel:

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

Use this skill for formal initial coverage and formal research refresh after
Equity Data has produced an accepted context and the PEI owner has written a
structured preliminary underwrite. Do not use it for data collection, daily
monitoring, trade overlays, or implementation work.

Require before dispatch:

1. valid security identity;
2. current price with as-of timestamp;
3. explicit decision horizon;
4. accepted `support/pei_input_receipt.json`; and
5. a preliminary underwrite with candidate assumptions, evidence anchors,
   proposed Base values or ranges, and flip conditions.

The preliminary underwrite covers each materially load-bearing family or gives
an explicit non-material disposition: revenue and order conversion; product mix
and operating margin; reinvestment and FCFF conversion; capital structure and
WACC; explicit growth duration, competitive-advantage fade, and terminal
economics; and the 12-month earnings path and market-implied expectations. This
is aggregate investment judgment, not a second registry for every formula cell.

If agent collaboration is unavailable, current formal research is `BLOCKED`.
Do not emulate the three seats in one response. A PEI `BLOCKED` evidence posture
also blocks Council when the missing research input could change direction,
model completeness, or the promotion gate. Otherwise disclose the limitation
and continue.

## Ownership

- Equity Data owns admissibility, identity, provenance, freshness, and accepted
  evidence. Council never browses or repairs upstream evidence.
- The PEI owner owns the preliminary underwrite, adjudication, authoritative
  model, and final paper.
- Council agents only challenge candidate assumptions using their sealed packet.
- The independent recomputation checks arithmetic after the owner model; it does
  not create a second investment conclusion.
- `support/council_run.json` is the sole Council authority root.

## Workflow

1. Build one packet per seat from the accepted evidence and the same candidate
   assumptions. Each packet includes only identity, cutoff, horizon, relevant
   evidence IDs, and instructions. Do not include a final model, fair value,
   action, position, or another seat's output.
2. Read [references/council-protocol.md](references/council-protocol.md). Spawn
   exactly three parallel leaf agents. They may inspect only their packet and
   its accepted local evidence, may not browse, and may not delegate.
3. Seal each memo with its exact packet hash. A memo challenges assumptions and
   states evidence, reasoning, decision impact, falsifier, and limitations. It
   may propose a Base value or range, but it does not calculate the final model
   or choose `Long`／`Short`／`Avoid`／`Pass`. Every seat tests what may be too
   conservative, too aggressive, or uncertain and states its strongest
   evidence-consistent market-right countercase; no seat is assigned a fixed
   Bull or Bear conclusion.
4. Return all three sealed memos to the same PEI owner. For every preliminary
   assumption, record `accept`／`conditional`／`reject`, the final Base/range,
   cited evidence, reason, and model input IDs.
5. If a memo identifies a missing input that can plausibly flip direction,
   model completeness, or promotion safety, stop and request at most two exact
   upstream inputs. Otherwise record the limitation and continue.
6. Calculate one authoritative owner model, perform one independent arithmetic
   recomputation, freeze fair value, and let the PEI owner update the final
   research paper. Base fair value is primary. Probability-weighted fair value
   is optional and may appear only when every probability has an explicit
   evidence or calibrated-judgment basis.
7. Save and validate `support/council_run.json`. Current formal schema v3 binds
   the preliminary underwrite, exactly three packets and memos, owner
   adjudication, final model specification, model commit time, FV-freeze
   receipt, and exact installed validator hash. It has no PM Chair receipt.

## Invariants

- Exactly three isolated agents run for each admitted current formal Council.
- First-round memos stay sealed until all three complete.
- `browsed` is `false`; `added_evidence_ids` is empty.
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
