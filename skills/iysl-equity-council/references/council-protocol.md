# Council protocol

## Purpose

Use three genuinely separate reasoning paths to improve a PEI owner's candidate
assumptions before calculation. The agents challenge; the owner decides.

## Dispatch

Spawn exactly three parallel leaf agents. Give every agent only:

- its exact public-method seat name;
- the same identity, evidence cutoff, current price, and decision horizon;
- the preliminary underwrite's candidate assumptions;
- the evidence IDs relevant to its method; and
- authority to inspect the packet, accepted local evidence, and independently
  search relevant original sources under the project browser/Exa policy.

Every task must say: no self-admitted evidence, no other seat output, no final
model or action, and no further delegation. It must also require the seat to test
what may be too conservative, too aggressive, or uncertain and to state the
strongest evidence-consistent market-right countercase. If collaboration is
unavailable, return `BLOCKED`; one agent pretending to be three is not
independent challenge.

The packet instructions must also require each material challenge to trace its
accepted evidence through a source-to-economic bridge to a proposed Base or
range and an observable falsifier. A one-variable diagnostic may expose a
question, but cannot arbitrarily freeze the final central case: the seat must
say whether connected operating drivers should move together or why they should
not. This is part of the same first-round instruction, not another review.

## The three lenses

### Aswath Damodaran — Fundamental Committee Member

Test whether the business story maps coherently to revenue growth, margins,
reinvestment, cash conversion, capital structure, discount rate, terminal
economics, and reverse-valuation implications. Identify assumptions that are
unsupported, internally inconsistent, too conservative, or too aggressive.

### George Soros — Reflexivity Committee Member

Test whether expectations, marginal actors, financing conditions, narrative,
liquidity, and price feedback can change the path or timing of fundamentals.
Separate a durable operating effect from a temporary market loop. Do not turn a
market signal into source truth.

### Michael Mauboussin — Expectations Committee Member

Compare the proposed assumptions with expectations embedded in price,
consensus revisions, relevant base rates, competitive economics, and payoff
asymmetry. Use probabilities only when a defensible basis exists; otherwise
describe uncertainty and the observations that would resolve it.

The names describe public analytical traditions only. They do not increase the
quality of evidence and do not imply endorsement or private access.

## Packet contract

Before dispatch, the preliminary underwrite must disposition these six
load-bearing assumption families exactly once: revenue/orders/capex recognition;
product mix and margins; reinvestment and FCFF; capital structure and WACC;
duration/fade/terminal economics; and 12-month market expectations. Each family
is either `covered` by named candidate assumption IDs or `not_material` with an
explicit reason. Every candidate belongs to one family.

Preserve the original investment question and horizon in the existing candidate
rationale and packet instructions. For twelve-month market expectations, ask
whether the proposed operating basis, target-date pricing mechanism, capital /
distribution assumptions and probability reasoning can support that question.
An annual revenue guide alone is not this bridge. `covered` means the relevant
candidate relationships are available for challenge, not that the question is
answered. Unresolved relationships stay explicit in candidate rationale and
falsifiers; final prices, stance and owner model remain excluded from packets.

The PEI owner must reconcile every evidence-gated material Ask SA, opened
Analysis, and opened Transcript signal delivered by Equity Data. Record each
one under the affected candidate's `challenge_signal_dispositions` with its
signal and source IDs, evidence nature, finding, `adopt`／`reject`／`not_material`
disposition, accepted supporting evidence IDs, reason, and flip condition. Ask
SA is `provider_synthesis`; its source cannot support itself, and its supporting
evidence must include non-synthesis accepted evidence. A candidate uses an
empty list only when the Data handoff contains no eligible material signal for
that assumption. Every packet's root `evidence_ids` must cover the supporting
evidence of all included signals. Raw Ask SA does not enter a packet.

Each packet is JSON with only:

- `schema_version`
- `ticker`
- `security_id`
- `evidence_cutoff`
- `seat`
- `candidate_assumptions`
- `evidence_ids`
- `instructions`

The packet must not contain, even inside nested fields, a final fair value,
target price, research stance, action, position size, execution instruction,
final owner model, or another seat's memo.

## Memo contract

Each sealed memo contains:

- exact seat and `packet_sha256`;
- schema `council-sealed-memo-v3`, `sealed_at`, truthful boolean `browsed`, and
  `added_evidence_ids: []` (discovery is not evidence admission);
- `source_candidates`: zero or more discoveries, with globally unique
  `candidate_id`, original `url`, `source_locator`, `as_of` (ISO publication date or timestamp), `retrieved_at`,
  affected `assumption_ids`, `finding`, and `evidence_nature`;
- a concise `summary`;
- zero or more assumption `challenges`;
- the `strongest_countercase`; and
- explicit `limitations`.

Each challenge contains:

- `assumption_id`;
- `assessment`: `supported`, `too_conservative`, `too_aggressive`, or
  `uncertain`;
- optional `proposed_base` and `proposed_range`;
- starting-receipt `evidence_ids` and this seat's provisional `candidate_source_ids`;
- `reasoning`;
- `decision_impact`; and
- `falsifier`.

Check for material issues omitted from the preliminary model using the starting
evidence and independently found originals. Candidates remain provisional;
search snippets alone cannot substantiate a challenge. State the causal link, the decision it could change, and the
exact obtainable evidence that would resolve it in existing limitations or
challenges. Do not build a per-formula question inventory or require another
Council round merely because a catalogue field was not selected. Future
uncertainty calls for bounded assumptions and falsifiers, not exhaustive data.

A seat may say an assumption is supported. It must not manufacture a difference
to appear useful. It must not issue the final investment stance.

## Owner adjudication

After all three memos seal, Data checks material discoveries through the existing
PEI receipt path. The schema v4 root binds `council_input_pei_receipt` to the
unchanged initial packet evidence and `pei_input_receipt` to the final admitted
inputs. The same security's final cutoff cannot precede its initial cutoff.
This does not require another Council dispatch or a second evidence registry.

Use root authority_version 3 and `pei-council-adjudication-v3`. Its
`source_dispositions` maps each candidate exactly once to `candidate_id`,
`disposition` (`accepted`, `rejected`, `not_material`), admitted `evidence_ids`,
and `reason`. Only accepted candidates may name final-receipt evidence IDs;
rejected/not-material rows use an empty list. Data acceptance establishes source
identity and meaning; PEI still decides whether its claim changes an assumption.
The original memo may cite a candidate that is later rejected without rewriting
history. Each final assumption cites only final-receipt accepted evidence.

The same PEI owner adjudicates every preliminary assumption exactly once.
For each assumption, record:

- prior Base/range;
- final Base/range;
- `accept`, `conditional`, or `reject`;
- contributing Council seats;
- accepted evidence IDs;
- reason; and
- affected model input IDs.

In the existing decision reason, connect the accepted, conditional or rejected
assumption back to the original question: does it support a horizon conclusion,
or leave a specific relationship unresolved? The PEI owner then follows the
project formal workflow's investment-question completion check before writing;
sealing three memos or retaining a company guide does not itself answer it.

The adjudication is the final assumption authority. It is not a vote: repeated
claims from correlated evidence do not gain weight, and the owner may reject a
fluent challenge that is not supported.

## Stop rule

Do one targeted refill only for a remaining gap that can materially change the
judgment or break essential computation. Then retain a defensible estimate,
conditional scenarios, or an explicit inability to select a central value;
never fill uncertainty with an arbitrary haircut. Do not restart Council.
Check changed decision-critical calculations and their consistency with the
paper, then stop. Schema v3 historical runs retain their evidence-closed memo
and adjudication contracts; do not migrate or reseal their artifacts.

For v4 accepted source dispositions, each evidence ID must resolve to the same original URL, document/claim locator, publication date and evidence nature through the final PEI registry primary/public provenance. An unrelated accepted ID cannot stand in for a candidate. If Data corrects the candidate classification, reject that candidate as stated and explain the corrected evidence separately in the owner decision; do not relabel a sealed memo.

Use the Data taxonomy for candidates: opened public analyst articles are `corroborating_context` with `public_provenance`; label their estimates and inference in the finding and owner reason. They can influence the central assumption without becoming company facts. This discovery route uses original articles, not untraceable provider target summaries.
