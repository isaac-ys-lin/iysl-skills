# Council protocol

## Purpose

Use three separate reasoning paths to challenge a PEI owner's candidate
assumptions before calculation. Seats estimate blind; the owner decides after
the sealed memos arrive.

## Dispatch

Spawn exactly three parallel leaf agents in fresh contexts without inherited
owner conversation (for collaboration agents, use `fork_turns="none"`). Give
each seat only its public-method name, the common packet, and accepted local
evidence named by that packet. It
may independently search relevant original sources under the project
browser/Exa policy, but discoveries remain candidates for Data admission.

For a new search-required blind run, set `search_required: true` in each packet
before hashing or dispatch. First verify that the target seat session actually
has a permitted source channel: Codex in-app browser or the Exa search/fetch
app; Claude WebSearch/WebFetch for a Claude-hosted seat. An offline-only
`codex exec --ignore-user-config` seat is not a search-capable dispatch. Codex
CLI `--search` and shell HTTP clients are not substitutes under Equity's
source policy. If none of the permitted channels is available, stop this seat
before a memo is sealed and report the capability block to the owner.

Each task says: no self-admitted evidence, other-seat output, owner private
underwrite, root artifact, final model, stance, action, or further delegation.
The packet is the only Council artifact a seat receives. Before hashing the
underwrite, keep actual periods and units but remove embedded owner estimates:
`million fully diluted shares; WACC 9.3% [8.5%,11.5%]` becomes
`million fully diluted shares`, with WACC represented by its own candidate if
material. Clean owner estimates from rationale, rejected alternatives, flip
conditions, signal text, and instructions too; attributed source numbers may
remain. The validator rejects structured leaks; the owner checks free-text
meaning before dispatch. If collaboration is unavailable, return `BLOCKED`;
one agent cannot imitate three independent seats.

Each seat estimates every `covered` candidate exactly once. It traces accepted
evidence through an economic bridge to its estimate and observable falsifier.
A one-variable diagnostic may expose a question, but the seat states whether
connected operating drivers should move together or why they should not. This
is the single first round; do not add a seat or restart Council.

## The three lenses

### Aswath Damodaran — Fundamental Committee Member

Test the mapping from the business story to growth, margins, reinvestment, cash
conversion, capital structure, discount rate, terminal economics, and reverse
valuation.

### George Soros — Reflexivity Committee Member

Test whether expectations, marginal actors, financing, narrative, liquidity,
and price feedback can change the fundamental path or timing. Separate durable
operating effects from temporary market loops; market signals are not source
truth. Also provide the evidence-compatible most plausible repricing path that
makes the horizon price materially above the price-implied path, and the
qualitative cost of a missed entry without inventing a value.

### Michael Mauboussin — Expectations Committee Member

Compare the candidate with price-implied expectations, estimate revisions,
relevant base rates, competitive economics, and payoff asymmetry. Use
probabilities only with a defensible basis.

The names describe public analytical traditions only. They do not establish
evidence quality or imply endorsement or private access.

## Packet contract

The preliminary underwrite dispositions the six load-bearing families exactly
once: `revenue_orders_capex_recognition`, `product_mix_and_margins`,
`reinvestment_and_fcff`, `capital_structure_and_wacc`,
`duration_fade_and_terminal`, and `twelve_month_market_expectations`. Each
family is `covered` by named candidate IDs or `not_material` with an explicit
reason; every candidate belongs to one family. A `covered` family and its
candidates must agree exactly.

Before dispatch, hash the complete preliminary underwrite. Preserve its original
investment question and horizon in the blind candidate rationale and packet
instructions. For twelve-month expectations, challenge the operating basis,
target-date pricing mechanism, capital/distribution assumptions, and probability
reasoning that support that question; an annual revenue guide alone is not the
bridge. Each packet uses
`council-premodel-seat-packet-v4` and contains only:

- `schema_version`, `ticker`, `security_id`, `evidence_cutoff`, `seat`;
- `preliminary_underwrite_sha256` (digest only, never a path) and
  `dispatched_at`;
- `candidate_assumptions`, `evidence_ids`, and `instructions`.

New search-required packets add `search_required: true`. Absence of that field
preserves the already sealed v5 packet/memo contract; do not rewrite an old
packet to opt it in.

Each packet candidate contains exactly `assumption_id`, `family`, `period`,
`unit`, `evidence_ids`, `flip_condition`, `rationale`,
`rejected_alternative`, and `challenge_signal_dispositions`. It excludes
`proposed_base`, `proposed_range`, and any owner-private numerical proposal.
The PEI owner reconciles each evidence-gated material Ask SA, opened Analysis,
and opened Transcript signal under the affected candidate's
`challenge_signal_dispositions`, including its signal/source IDs, evidence
nature, finding, `adopt`/`reject`/`not_material` disposition, accepted support,
reason, and flip condition. The packet root evidence IDs cover all candidate
evidence and accepted support. Ask SA is `provider_synthesis`; it cannot
support itself and needs non-synthesis accepted support. An empty signal list
means no eligible material signal was delivered for that candidate.

Initial receipt admission does not make private artifacts seat-visible. Model
evidence IDs and IDs pointing to the bound underwrite, final model, adjudication,
or sealed memos (including copies with the same hash) cannot enter packet or
challenge evidence. Dispatch timestamps are no earlier than the initial cutoff
and no later than the earliest sealed memo.

The packet never contains a final fair value, target price, stance, action,
position size, execution instruction, final owner model, or another seat memo.

## Memo contract

Each sealed memo uses `council-sealed-memo-v4` and contains its exact `seat`,
`packet_sha256`, `sealed_at`, truthful `browsed`, `added_evidence_ids: []`,
`source_candidates`, concise `summary`, `challenges`, both strongest cases,
and `limitations`. `packet_sha256` binds the received packet. Every packet's
`dispatched_at` cannot exceed the earliest memo `sealed_at`.

Each source candidate has a globally unique `candidate_id`, original `url`,
`source_locator`, publication `as_of`, `retrieved_at`, affected
`assumption_ids`, `finding`, and `evidence_nature`. It is a discovery, never
admitted evidence.

Every memo has exactly one challenge for every packet candidate, with matching
`assumption_id`, `period`, and `unit`. A challenge contains
`estimation_status`, starting-receipt `evidence_ids`, provisional
`candidate_source_ids`, `reasoning`, `decision_impact`, and `falsifier`.
It has no `assessment` or self-declared direction.

For `estimated`, `proposed_base` is finite numeric and `proposed_range` is an ordered
finite numeric pair containing the Base, supported by at least one accepted
evidence ID or this seat's provisional source candidate; `not_estimable_reason` and
`missing_evidence` are null. For `not_estimable`, Base and range are null and
both `not_estimable_reason` and `missing_evidence` state the estimation obstacle
and the specific obtainable evidence that would resolve it. A
seat does not use `uncertain` as a challenge outcome.

With `search_required: true`, every challenge adds `source_checks` (an empty
list is allowed for `estimated`). Before `not_estimable`, search or fetch a
relevant public original or specific disclosure question. Each
`not_estimable` has at least one check with exactly `tool`, `query_or_url`,
`result`, and `still_insufficient_reason`, all nonempty. `tool` is one of
`codex-in-app-browser`, `mcp__codex_apps__exa_web_search_exa`,
`mcp__codex_apps__exa_web_fetch_exa`, `WebSearch`, or `WebFetch`; the last two
apply to Claude-hosted seats. Record a failed or blocked call as such in
`result`, and keep `browsed: false` when no source was successfully opened.
`source_candidates` remain separate provisional evidence. The validator
checks the fields and permitted channel names; the owner checks the host/tool
trace against the claimed calls because memo text cannot prove a tool ran.

`strongest_upside_case` and `strongest_downside_case` are each an object with
nonempty `mechanism` and `falsifier` strings, plus nonempty string lists
`joint_conditions` and `observable_triggers`. Soros's upside object also has
a nonempty qualitative `missed_entry_cost`; it may not fabricate a number.

## Owner adjudication

After all three memos seal, Data checks material discoveries through the
existing PEI receipt path. New Council roots use schema version 5 and
`artifact_bindings.authority_version` 4. The root binds the original
preliminary underwrite, all packets, memos, and adjudication by digest. Its
identity cutoff is the final `pei_input_receipt` cutoff: the root does not
repeat `evidence_cutoff` or bind a separate FV freeze receipt, and memo
`sealed_at` <= `adjudicated_at` <= `model_committed_at`. Sealed v5 runs that
still carry these fields or a decision label stay valid; a present root cutoff
must equal the final receipt cutoff. The adjudication uses
`pei-council-adjudication-v4` and repeats `preliminary_underwrite_sha256`;
packet hashes bind to that underwrite and memo hashes bind to their packets.
These hashes and timestamps make later changes detectable. Without external
trust they cannot prevent an owner who can rewrite the complete artifact set
from resealing it.

`source_dispositions` maps each discovered candidate exactly once to its
`candidate_id`, disposition (`accepted`, `rejected`, `not_material`), admitted
`evidence_ids`, and reason. Only accepted candidates name final-receipt
evidence; rejected and not-material rows use an empty list. Each final decision
uses only final-receipt accepted evidence. For accepted dispositions, every
evidence ID resolves through the final PEI registry to the same original URL,
locator, publication date, and evidence nature; an unrelated ID cannot replace
the candidate. A classification correction rejects the sealed candidate and is
explained separately in the owner decision.

The owner adjudicates every preliminary assumption exactly once. A decision
records the original `prior_base`/`prior_range`, final Base/range,
contributing seats, evidence IDs, reason, model input IDs, and
`range_comparisons`. `range_comparisons` maps every seat to exactly one of
`owner_below_range`, `owner_above_range`, `within_range`, or `not_estimable`.
The validator recomputes this map from the preliminary Base and the seat memo;
both range endpoints count as `within_range`. These are numeric comparisons,
not economic upside/downside labels: a higher cost estimate can reduce value.
The owner does not choose the comparison direction.

For a v5 run, a withdrawn assumption uses `final_base: null`,
`final_range: null`, and `model_input_ids: []`; no decision label is needed.
Its reason names the replacement calculation or remaining gap. The two final
value fields must be null together; a retained estimate keeps numeric
Base/range and nonempty model input IDs. Earlier v3/v4 contracts still require
numeric values and an `accept`/`conditional`/`reject` decision.

Each decision also has `retention_basis`: null, or an object with
`omitted_evidence_ids` (final accepted IDs) and `omitted_mechanism`. The
mechanism may be an empty string only when the evidence list is nonempty.
When two or more estimated seats place the owner initial Base outside their
ranges on the same side and the final Base equals the initial Base,
`retention_basis` names at least one omitted accepted evidence ID or a specific
omitted mechanism, and the decision reason explains why retention remains
proper. Changing only the final range does not remove this requirement.

Run `validate_council_run.py --compare-ranges --plugin-root <plugin-root>
--artifact-root <artifact-root> <run.json>` before adjudication. Its stdout is
JSON shaped `{assumption_id: {seat: comparison}}`; copy every comparison to the
matching `decision.range_comparisons`. It does not change sealed artifacts.
Then run the normal full validator separately.
The comparison command validates the root, receipts, underwrite, packets and
memos; final model/adjudication descriptors may still be placeholders.
It is not a completed-run verdict. Keep the output in the run and seal the
completed adjudication only after incorporating it.

The adjudication is final assumption authority, not a vote. Repeated claims
from correlated evidence do not gain weight. The owner then completes the
formal workflow's investment-question check before writing.

## Stop rule

Do one targeted refill only for a remaining gap that can materially change the
judgment or break essential computation. Retain a defensible estimate,
conditional scenario, or explicit inability to select a central value; do not
fill uncertainty with an arbitrary haircut. Check changed decision-critical
calculations and stop.

Historical v3 and v4 runs retain their original packet, memo, and adjudication
contracts. They are read-only: do not migrate, reseal, or apply this v5/v4
blind-round contract to them.

The v4 admission chain remains in force: `council_input_pei_receipt` binds the
initial packet evidence and `pei_input_receipt` the final admitted inputs. They
must identify the same security and the final cutoff cannot precede the initial
cutoff. Opened public analyst articles are `corroborating_context` with
`public_provenance`; identify their estimates and inference in the finding and
owner reason. They may influence a central assumption without becoming company
facts, and must be original articles rather than provider target summaries.
