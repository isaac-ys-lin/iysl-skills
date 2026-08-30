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
- authority to read only the packet and referenced accepted local evidence.

Every task must say: no browsing, no new evidence, no other seat output, no final
model or action, and no further delegation. It must also require the seat to test
what may be too conservative, too aggressive, or uncertain and to state the
strongest evidence-consistent market-right countercase. If collaboration is
unavailable, return `BLOCKED`; one agent pretending to be three is not
independent challenge.

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
- `sealed_at`, `browsed: false`, and `added_evidence_ids: []`;
- a concise `summary`;
- zero or more assumption `challenges`;
- the `strongest_countercase`; and
- explicit `limitations`.

Each challenge contains:

- `assumption_id`;
- `assessment`: `supported`, `too_conservative`, `too_aggressive`, or
  `uncertain`;
- optional `proposed_base` and `proposed_range`;
- accepted `evidence_ids`;
- `reasoning`;
- `decision_impact`; and
- `falsifier`.

A seat may say an assumption is supported. It must not manufacture a difference
to appear useful. It must not issue the final investment stance.

## Owner adjudication

After all three memos seal, the same PEI owner adjudicates every preliminary
assumption exactly once. For each assumption, record:

- prior Base/range;
- final Base/range;
- `accept`, `conditional`, or `reject`;
- contributing Council seats;
- accepted evidence IDs;
- reason; and
- affected model input IDs.

The adjudication is the final assumption authority. It is not a vote: repeated
claims from correlated evidence do not gain weight, and the owner may reject a
fluent challenge that is not supported.

## Stop rule

Request an upstream refill only when an identified gap can plausibly flip the
research direction, break model recomputation, or make promotion unsafe. Ask for
at most two exact inputs. Otherwise disclose the limitation and proceed.

Once the owner model is independently recomputed, source-linked, and consistent
with the paper under reasonable extreme scenarios, stop adding process.
