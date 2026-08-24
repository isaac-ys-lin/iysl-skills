# Judgment Contract

Use this contract after the minimum gate in `SKILL.md` passes.

## Chair receipt, common factual spine, and private partitions

The Chair receipt records:

- security identity, current price/as-of, decision horizon, and evidence cutoff;
- Public Equity Investing facts, estimates, expectations, model outputs,
  valuation anchors, scenarios, catalysts, and falsifiers;
- source posture, material conflicts, staleness, and unresolved gaps;
- optional accepted `ambient_market_context` status and matching claims;
- persona evidence receipts and source-origin relationships; and
- the lead workflow's directional or actionability conclusion, sealed until
  after the Council research stance freezes.

Derive one common factual spine from this receipt. It contains security identity,
current price/as-of, horizon, cutoff, and accepted facts needed by all seats. It
excludes the full PEI thesis narrative and upstream Long, Short, Avoid,
watchlist, pass, wait, blocked, conviction, actionability, participation,
implementation readiness, borrow, cost, sizing, orders, and execution fields.
Members must not infer the omitted fields.

The spine is structured, not narrative: use only the validator's factual field
IDs with scalar values, units, as-of times, and accepted evidence IDs. Nested
values, prose thesis summaries, model conclusions, and unrecognized or extra
fields fail the receipt. Each private partition contains only its exact
`allowed_domains` and `evidence_ids`.

Then construct the three private partitions defined in
`council-protocol.md`. Damodaran receives accepted fundamentals, reverse-
valuation, and capital-structure inputs; Soros receives price-path, marginal-
actor, and positioning/reflexivity inputs; Mauboussin receives expectations,
revisions, reference-class, and probability/payoff inputs. Do not give all
three seats the complete upstream narrative merely because they share a factual
spine.

Do not silently upgrade screen-grade, illustrative, stale, conflicting, or
market-belief evidence into verified company facts.

## Internal upstream artifact receipt

Keep one hidden row per material upstream artifact:

| Field | Meaning |
| --- | --- |
| `workflow` | Public Equity Investing lead, support skill, or accepted ambient workflow |
| `artifact` | Stable file, handoff, run, or conversation reference |
| `as_of` | Evidence, model, or ambient-context timestamp |
| `decision_relevance` | State, probability, payoff, timing, or judgment affected |
| `posture` | Source-backed, model output, market-belief signal, illustrative, stale, or conflicting |
| `unresolved_gap` | Missing input that could change the decision |
| `upstream_disposition` | Sealed verdict or actionability label for post-stance suppression audit |

The receipt proves reuse and exposes gaps. It is not a reader-facing source
ledger and does not replace Public Equity Investing provenance.

## Evidence classes

- `Established company fact`: directly supported by an accepted PEI artifact
  or an opened primary source with a precise receipt before Council admission.
  If a seat identifies an exact model- or sign-changing evidence gap, the
  current Council run stops and may return at most two inputs in one targeted
  PEI refill request. Only a new independently accepted PEI receipt can
  establish the input and start a new Council run. An unaccepted lead may not
  change a model input or start another refill.
- `Market-belief signal`: observable evidence of attention, expectations,
  positioning, narrative, or behavior. It may have high price relevance while
  having low truth relevance about company fundamentals.
- `Supported inference`: a stated reasoning step anchored to established facts
  or identified market-belief signals.
- `Testable conjecture`: an unconfirmed future state admitted through every
  conjecture gate below.
- `Unsupported narrative`: an idea excluded from the distribution.

Score `truth_relevance` and `price_relevance` separately. A popular but
unverified narrative may change the timing or probability of a price path when
its prevalence, marginal actor, feedback mechanism, horizon, and falsifier are
observable. It may not directly change revenue, cash flow, margins, or intrinsic
value without a supported causal bridge.

## Source origin and correlation

Count the underlying event, document, dataset, or analyst work as the
`origin_key`. Syndicated articles, provider summaries, multiple pages
derived from one consensus dataset, and multiple personas citing the same
origin are not independent confirmation.

Seeking Alpha Quant, factor grades, Wall Street consensus, analyst targets,
author ratings, and price momentum may each carry bounded signal. Do not assign
zero weight by rule, vote across them, average them, or multiply confidence
without examining shared inputs and origin.

Headlines and search snippets remain research leads unless PEI opened and
accepted the underlying material before Council admission. When Seeking Alpha
is unavailable, an upstream accepted public-web route may be disclosed and
used; provider absence is not `Avoid`. Council does not open a replacement
route itself.

## Conjecture admissibility

A conjecture is admissible only when it states:

1. causal mechanism;
2. evidence anchor and source receipt;
3. reference class or why no useful base rate exists;
4. difference from priced-in expectations;
5. probability range rather than false precision;
6. within-horizon financial, valuation, or price-path consequence;
7. observable signal and expected timing; and
8. falsifier or deletion condition.

Missing causal mechanism, evidence anchor, or payoff linkage makes the claim an
unsupported narrative. Exclude it rather than assigning a token probability.

Qualitative or behavioral evidence can change a scenario probability through
explicit Chair judgment; the source does not need to publish a numeric
probability. The Chair must show the anchor, mechanism, horizon, and distribution
delta and must not present subjective ranges as measured frequencies.

## Distribution construction

Build one requested-horizon distribution without treating intrinsic value as
the sole path to return. Separate and then reconcile:

1. `Fundamental convergence`: changes in business states, cash flows, risk, or
   valuation anchors;
2. `Expectations revision`: outcomes relative to what price and consensus
   already imply; and
3. `Reflexive path`: beliefs, attention, positioning, liquidity, price action,
   and their feedback into behavior or real company conditions.

The channels may interact. Count a causal effect once, state which channel owns
it, and explain any transmission between channels. Long-duration DCF constrains
or anchors the distribution unless an explicit mechanism transmits it inside
the requested horizon.

## Named method-completion gate

Record the three public-method personas by name before Chair synthesis:

| Committee member | Completion requires |
| --- | --- |
| `Aswath Damodaran — Fundamental Committee Member` | Archetype-appropriate reverse valuation, price-to-equity bridge, price-implied drivers versus PEI baseline and plausible range, story-to-numbers consistency, least plausible assumption, and convergence path |
| `George Soros — Reflexivity Committee Member` | Current trend and bias, evidenced marginal actors, complete belief-action-market-reality feedback loop or an explicit non-reflexive flow regime, phase, continuation and reversal triggers, and the accepted requested-horizon market packet |
| `Michael Mauboussin — Expectations Committee Member` | Price-implied expectations, value trigger, defensible reference class and base-rate prior or explicit `Reference-class gap`, inside-view update, posterior range, probability-payoff table, and sign sensitivity |

Set each to `Complete`, `Partial`, or `Unavailable`. A generic valuation summary,
momentum description, or unsupported scenario probability does not satisfy the
named method. The exact names disclose which public method was simulated; they
do not imply participation, endorsement, private access, or evidentiary weight.
Each `Complete` member must also return the machine-checkable structured artifact
defined in `council-protocol.md`; prose quality cannot replace required drivers,
feedback links, reference-class treatment, probability states, evidence IDs, or
recomputed arithmetic. Each artifact exposes a unique `proposition_id`; Chair
seat decisions and state target components must resolve back to those IDs and
their evidence-backed numeric inputs. Soros paths, Mauboussin payoff states, and
Chair states must use canonical `downside` / `base` / `upside` roles ordered by
payoff; a Chair component may resolve only to a source carrying the same role.
The full Chair matrix may use each named method source state only once; it may
not duplicate one probability event across mutually exclusive states.
A numeric `Partial` artifact remains usable only after full-schema validation;
a gap-only artifact cannot contribute a target or probability.

Before Chair synthesis, require a canonical `primary_mechanism_tag`, then
compare it with each sealed memo's `causal_mechanism`,
`disconfirming_condition`, `key_metric`, and `source_posture`. Complete the
validator-derived `mechanism_tags` set and semantic convergence review to
detect controlled English/Chinese near-synonym restatements that evade literal
matching. Declared tags must exactly match every taxonomy pattern found in the
causal sentence. If any canonical tag, field, or semantic causal line collides
across seats, label `persona_convergence` and run exactly one same-evidence
corrective pass. Remaining collision is
`unresolved_convergence`: it is not independent confirmation and forces
`Robustness: Fragile`.

Then apply the separate `Stanley Druckenmiller — PM Chair` completion gate. The
Chair is a public-method decision persona, not a fourth research member, and
must return the `Dominant-variable decision matrix` defined in
`council-protocol.md`: requested-horizon transition, one dominant variable,
MECE state matrix, `Accept`/`Conditional`/`Reject` decisions for every decisive
member proposition, strongest disconfirming path, observable reversal trigger,
and Long/Short/Avoid with confidence and robustness. The Chair receives the full
accepted PEI baseline only after first-round sealing and the unique-contribution
gate. It may use only accepted PEI inputs and sealed member memos. It may not browse, add evidence,
simulate a personal position, infer sizing, or repair a partial member method.

Public options, price, volume, short-interest, positioning, liquidity, and
market-reaction evidence accepted by PEI may enter the George Soros sealed
partition before stance freeze when used to understand beliefs or feedback. Options suitability, borrow
availability, transaction cost, sizing, orders, and execution remain sealed
until participation and implementation assessment.

## Research direction and participation hurdle

Use `0%` gross expected price return as the research-direction threshold
before borrow, options, liquidity, cost, carry, or execution inputs:

- above zero produces `Long`;
- below zero produces `Short`; and
- `Avoid` is valid only when the distribution is balanced at its stated
  precision and no supported tail asymmetry makes either direction positive.

Do not invent precision to avoid a balanced result. A small non-zero expected
return remains directional; express weak evidence through `Confidence`,
sensitivity through `Robustness`, and unattractive economics through
`Participation` or `Implementation readiness`.

Every non-zero hurdle states its provenance and scope. A Long-candidate upside
target applies only to Long participation unless the accepted source defines
another use. Mandate returns, cost buffers, borrow, carry, and execution
economics are later participation or implementation hurdles; they never become
a symmetric Long/Short research hurdle.

## Precedence

Apply this order:

1. The minimum gate establishes whether an investment judgment may be issued.
2. The requested-horizon distribution reconciles fundamental convergence,
   expectations revision, and reflexive price paths.
3. Gross expected price-return sign determines the research stance at the
   `0%` threshold.
4. Evidence quality and source independence set `Confidence`.
5. Sensitivity to reasonable assumptions and Council-runtime limitations set
   `Robustness`.
6. Portfolio or mandate suitability and its sourced hurdle set
   `Participation`.
7. Borrow, options, liquidity, cost, carry, and execution evidence set
   `Implementation readiness`.

Later dimensions never overwrite an earlier research stance. Prohibitive
implementation economics can make participation `Stand aside` and readiness
`Blocked` while the research stance remains Long or Short.

## Canonical judgment block

Return every field after the minimum gate passes:

| Field | Allowed values or content |
| --- | --- |
| `Research stance` | `Long`, `Short`, or `Avoid` |
| `Decision horizon` | Explicit user-requested horizon |
| `Council method personas` | Name Aswath Damodaran, George Soros, and Michael Mauboussin; show `Complete`, `Partial`, or `Unavailable`, freshness status, and distinct method contribution; label them public-method personas |
| `PM Chair` | Exact name `Stanley Druckenmiller — PM Chair`; label it a public-method decision persona and report Chair completion without implying participation, endorsement, private access, or a current position |
| `Decisive judgment` | Accepted, conditional, and rejected propositions with reasons |
| `Dominant-variable decision matrix` | Requested-horizon transition, one dominant variable and its precedence, MECE states, probability ranges, payoffs, gross expected return, strongest disconfirming path, and observable reversal trigger |
| `Distribution` | Material states, probability ranges, payoffs, gross expected price return, dominant price-formation mechanism, and the `0%` direction threshold |
| `Confidence` | `High`, `Medium`, or `Low` |
| `Robustness` | `Robust`, `Conditional`, or `Fragile` |
| `Participation` | `Eligible`, `Conditional`, or `Stand aside` |
| `Implementation readiness` | `Ready`, `Conditional`, or `Blocked` |
| `Implementation blockers` | Specific borrow, options, liquidity, cost, carry, or execution gaps |
| `Falsifiers / flip conditions` | Observable, dated evidence that changes the stance |

`Avoid` is valid only for a genuinely balanced requested-horizon distribution.
Uncertainty, missing implementation data, Council disagreement, provider
unavailability, an unsourced hurdle, and absent authorization are not
alternative definitions.

Keep proposed participation advisory. Do not infer sizing, orders, execution,
or user authorization.
