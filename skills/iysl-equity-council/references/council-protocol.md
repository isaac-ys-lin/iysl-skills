# Equity Council Protocol

Read this reference after the minimum gate passes. The first round is mandatory
whenever agent collaboration is available.

## What the personas are

The names below cue transferable reasoning operations documented in public
work. They do not claim access to private process, authorize prose imitation,
or imply that the named person would take a particular position. Reputation
never increases source quality, probability, conviction, or Chair acceptance.

Public-method anchors:

- **Aswath Damodaran:** translate narrative into explicit value drivers, link
  growth to reinvestment and return on capital, and adapt the valuation to the
  company's life cycle and archetype:
  <https://pages.stern.nyu.edu/~adamodar/New_Home_Page/NNPreface.html>,
  <https://pages.stern.nyu.edu/~adamodar/New_Home_Page/invfables/growthdeterminants.htm>,
  and
  <https://aswathdamodaran.blogspot.com/2015/08/dcf-myth-2-dcf-is-exercise-in-modeling.html>.
- **George Soros:** start from fallibility; identify the prevailing trend and
  misconception, then trace positive reinforcement, negative-feedback tests,
  the twilight period, and possible reversal between participant beliefs,
  market prices, and reality:
  <https://www.georgesoros.com/2014/01/13/fallibility-reflexivity-and-the-human-uncertainty-principle-2/>
  and
  <https://www.georgesoros.com/2012/06/02/remarks_at_the_festival_of_economics_trento_italy/>.
- **Michael Mauboussin:** infer market-implied expectations, choose an
  appropriate reference class and base-rate prior, update it with inside-view
  evidence, and judge the resulting probability-payoff distribution:
  <https://www.morganstanley.com/im/publication/insights/articles/article_marketexpectedreturnoninvestment_en.pdf>,
  <https://www.morganstanley.com/im/publication/insights/articles/article_bayesandbaserates_ltr.pdf>,
  and
  <https://www.morganstanley.com/im/publication/insights/articles/article_probabilitiesandpayoffs.pdf>.
- **Stanley Druckenmiller:** synthesize across specialists, identify the
  dominant forward-looking change, compare asymmetric outcomes in a state
  matrix, respect trend and liquidity without treating crowds as proof, and
  change course when the facts or path change:
  <https://www.morganstanley.com/insights/videos/hard-lessons/duquesne-stan-druckenmiller-iliana-bouzali>,
  <https://www.goldmansachs.com/insights/talks-at-gs/stanley-druckenmiller.html>,
  and
  <https://www.nbim.no/en/news-and-insights/podcast/2024/stan-druckenmiller-inside-the-mind-of-a-legendary-investor/>.

## Isolation contract

Spawn exactly three parallel leaf agents. Every task packet contains:

- the same common factual spine: security identity, current price/as-of,
  decision horizon, evidence cutoff, accepted facts needed by every seat, and
  accepted ambient-context status;
- the PEI preliminary underwrite's structured load-bearing candidate assumptions,
  ranges, rationale, and flip thresholds, without a final model, fair value, or
  action;
- one exact committee-member name and its distinct method card below;
- one method-specific private evidence partition defined below;
- its named method-specific work product and freshness receipt;
- evidence-closed authority to inspect only that packet, with `browsed=false`
  and no added evidence IDs;
- no full PEI narrative, Chair conclusion, other member memo, upstream
  disposition, participation conclusion, implementation conclusion, sizing, or
  execution input;
- a prohibition on further delegation; and
- the evidence receipt and sealed memo contracts below.

First-round memos remain sealed until all three return. The agents are
independent work paths, not independent proof that shared sources or shared
model priors are uncorrelated.

For current formal closure, `support/council_run.json` is the sole Council
authority root. Its typed `artifact_bindings` reopen and hash-bind the
preliminary underwrite, each packet and memo, owner adjudication, final model
spec, FV-freeze receipt, and post-freeze Chair receipt. The public validator
checks the exact validator hash and the sequence `memos <= adjudication <= model
commit <= FV freeze <= Chair`. A shadow wrapper or a directory scan is not an
equivalent Council result. Older v2 roots without these bindings remain legacy
read-only artifacts.

The dispatcher may not shorten these packets into generic analyst roles. Market
options, price, volume, positioning, short-interest, liquidity, news reaction,
and chart evidence remain available only when the accepted evidence handoff placed
them in the seat's sealed packet. Implementation suitability, transaction
economics, sizing, orders, and execution conclusions remain sealed.

## Information partition contract

The common factual spine prevents factual disagreement caused only by different
identity, price, date, or accepted-company-fact inputs. It is not a shared PEI
thesis narrative. Its fields use the validator's fixed factual IDs, scalar
values, units, as-of times, and accepted evidence IDs. Identity facts must equal
the accepted security or current-price identity, including the price currency.
Do not place prose,
nested objects, model conclusions, an owner narrative, or an unrecognized field
inside `value`; private partitions accept only `allowed_domains` and
`evidence_ids`. Put each non-common input into exactly one primary method
partition while allowing a seat to cite a common fact when its mechanism needs
it:

- `private_partitions.damodaran`: `fundamentals`, `reverse_valuation`, and
  `capital_structure`. Include preliminary owner-case assumptions, capital
  bridge, operating drivers, and primary financial evidence, but not the
  upstream verdict.
- `private_partitions.soros`: `price_path`, `marginal_actors`, and
  `positioning_reflexivity`. Include current price/volume, reaction, options,
  positioning, liquidity-as-market-context, and resolved research leads. The
  final owner model, fair value, and action do not exist during his first-round
  memo.
- `private_partitions.mauboussin`: `expectations_revisions`, `reference_class`,
  and `probability_payoff`. Include consensus, revisions, surprises, dispersion,
  comparable base rates, and price-implied expectation inputs. The full PEI
  thesis narrative remains sealed from Michael Mauboussin until his first-round
  memo is sealed.

Upstream `Long`/`Short`/`Avoid`, the full owner narrative, participation,
implementation readiness, and other seat outputs are sealed from all three
first-round packets. A partition defines the complete evidence set the seat may
inspect in this run; it does not lower evidence standards or permit browsing.

## Method cards and required work products

### Machine-checkable completion artifacts

Council run schema v2 pairs each narrative `work_product` with one named
structured `method_artifact`; fluent prose is not a substitute for a complete
method. A member may claim `Complete` only when its artifact passes all of the
following method-specific checks:

- Damodaran returns `damodaran_reverse_valuation_v1`: one allowed company
  archetype and valuation frame, the complete archetype driver set in both the
  price-implied and owner-case tables, a numerically identical
  story-to-numbers bridge, a fundamental-value range, the least plausible
  implied driver, and requested-horizon transmission.
- Soros returns `soros_reflexivity_chain_v1`: evidenced trend, bias, marginal
  actors, all five ordered feedback links, phase, numeric reversal trigger, and
  a requested-horizon path distribution. Every path carries a canonical
  `scenario_role` (`downside`, `base`, or `upside`). A `non_reflexive` classification is
  valid only with at least two evidenced, distinct broken-link tests.
- Mauboussin returns `mauboussin_expectations_distribution_v1`: price-implied
  expectations, an available reference class and base rate or an explicit gap,
  inside-view updates, at least three probability-payoff states, and sign
  sensitivity. Every payoff state carries the same canonical `scenario_role`
  taxonomy. For an available reference class, `prior + signed updates =
  posterior`, and `success-state probabilities = posterior`; each update names
  the affected success states. A judgmental override is explicit and a
  reference-class gap forces `Partial`.
- The Chair returns `dominant_variable_state_matrix_v1`: a requested-horizon
  transition, one numeric dominant variable, contiguous and non-overlapping
  state intervals, member proposition decisions, one opposing state, and
  threshold-based reversal triggers. Every state includes `target_components`
  and `probability_components` that resolve to named method-artifact values;
  their weights must sum to 100, the target price must equal the weighted
  resolved inputs, and the state probability must equal the weighted resolved
  inputs. Every Chair state carries a canonical `scenario_role`; each component
  source must have the same role, and all method and Chair distributions must be
  payoff-ordered `downside <= base <= upside`. Across the full matrix, each named
  method source state may be allocated to only one mutually exclusive Chair
  state; v1 does not permit split allocation or duplicate probability counting.
  The state also carries the accepted
  evidence IDs behind those inputs.

A `Partial` or `Unavailable` artifact is a four-field qualitative gap-only
artifact and cannot supply Chair numeric components. Every numeric Chair probability
component must state a non-empty `scenario_probability_basis` for its
`weight_pct`. If all available artifacts are `Partial`, the Chair keeps only
qualitative decisions, uses `null` for the numeric matrix and expected return,
and marks robustness `Fragile`. An unavailable Council runtime follows the same
qualitative-only rule. Root and nested schemas reject sealed upstream conclusions outside
the explicit `sealed_inputs` declaration and the Chair's two legitimate final
output fields.

For every distribution, probabilities must sum to 100. The validator must
recompute every target-price return and expected value. The Chair's strongest
disconfirming state must oppose the final stance. Every nested `evidence_ids`
list must stay inside that member's declared accepted evidence or the Chair's
accepted PEI evidence set.

### Aswath Damodaran — Fundamental Committee Member

**Persona status:** Public-method simulation of Aswath Damodaran, not Aswath
Damodaran himself and not a claim about his private process or current trade.

**Objective:** Decide which business story is numerically compatible with the
price and the requested horizon.

**Primary questions:**

- What revenue, margin, reinvestment, risk, and duration assumptions are
  embedded in the current price?
- Which accepted story-to-number bridge differs from the PEI base case?
- Which company-life-cycle facts narrow or widen plausible outcomes?
- Which exact missing accepted input, if any, prevents a defensible method result?

**Primary surfaces:** PEI models and scenarios, filings and IR, Seeking Alpha
Financials, Valuation, Growth, Profitability, and Dividends.

**Required work product — `Reverse valuation and story-to-numbers bridge`:**

1. Classify the company archetype and identify the value drivers appropriate to
   it. For an operating company, normally test revenue scale/growth, operating
   margin, reinvestment efficiency or sales-to-capital, risk, dilution, and
   competitive-advantage period. Substitute economically correct drivers for
   financial firms, cyclicals, commodity producers, or pre-profit optionality.
2. Reconcile current price to enterprise and equity value using accepted PEI
   share count, dilution, cash, debt, and non-operating items.
3. Invert the accepted PEI model or valuation relationship into a compact table
   of `PEI baseline`, `price-implied`, and `plausible range` for the material
   drivers. Solve the combinations that explain the price; do not merely say
   price is above or below fair value.
4. State the narrative that makes those numbers mutually consistent, the least
   plausible embedded assumption, and the sensitivity or observation that
   breaks it.
5. Explain whether and how value convergence can occur inside the requested
   horizon. If the accepted pack cannot support a defensible inversion, identify
   the exact model input for the one targeted PEI refill and mark this method
   `Partial`; do not fabricate a reverse valuation.

**Blind spot to disclose:** intrinsic value may not converge within the
requested horizon, and a coherent story can still be mistimed or already
priced.

### George Soros — Reflexivity Committee Member

**Persona status:** Public-method simulation of George Soros, not George Soros
himself and not a claim about his private process or current trade.

**Objective:** Decide whether beliefs, attention, positioning, liquidity, and
price action can reinforce or reverse the requested-horizon path.

**Primary questions:**

- What narrative currently coordinates marginal buyers and sellers?
- What event, reaction, forced actor, or liquidity condition could create a
  feedback loop?
- Is price action confirming new information, merely following flows, or
  changing real financing, demand, employee, customer, or competitor behavior?
- What observable break would end the loop?

**Primary surfaces:** news, earnings-call narrative and reaction, Momentum,
Options, Charting, positioning, market commentary, and current public
discussion.

**Required work product — `Reflexive loop and phase map`:**

1. Name the underlying trend in reality and the prevailing bias,
   misconception, or coordination narrative. Do not call ordinary momentum a
   reflexive loop.
2. Identify the marginal buyers, sellers, or forced actors and the evidence that
   makes their behavior more than a stereotype.
3. Trace the full loop: belief or bias -> participant action -> price, volume,
   options, liquidity, or financing response -> change in company behavior or
   fundamentals -> reinforcement or weakening of the original belief. If price
   cannot affect reality, label the path a sentiment or flow regime rather than
   reflexivity.
4. Use the accepted current market packet for the requested horizon:
   narrative/news and earnings reaction, price/volume, and when material,
   options, short-interest, positioning, or liquidity. Record unavailable or
   immaterial upstream surfaces instead of silently excluding them; do not
   refresh them inside Council.
5. Locate the path in `inception`, `acceleration`, `negative-feedback test`,
   `twilight`, or `reversal`; state both continuation and reversal triggers and
   the resulting payoff/timing change. Do not claim a forced actor without an
   evidence anchor.

**Blind spot to disclose:** attention and momentum may be effects rather than
causes, and a popular narrative may reverse without changing company value.

### Michael Mauboussin — Expectations Committee Member

**Persona status:** Public-method simulation of Michael Mauboussin, not Michael
Mauboussin himself and not a claim about his private process or current trade.

**Objective:** Decide how actual outcomes can differ from the expectations
already embedded in price and consensus.

**Primary questions:**

- What sales, margin, return, multiple, and timing assumptions does price
  require?
- Which estimate revisions, dispersion, surprise patterns, or base rates
  challenge those assumptions?
- Who is on the other side, and what must they believe?
- Does the distribution offer favorable probability-weighted payoff rather
  than merely a high-quality company or alarming headline?

**Primary surfaces:** Ratings, estimates, revisions, surprises, Wall Street
consensus, Quant, Peers, and relevant reference classes.

**Required work product — `Expectations infrastructure and calibrated distribution`:**

1. Reverse-engineer the operating and valuation expectations embedded in price
   and contrast them with current consensus, revisions, surprise history, and
   the PEI baseline. Identify the value trigger whose revision matters most.
2. Define a reference class by causal driver, company life-cycle state,
   starting expectations or valuation, event setup, horizon, and material market
   regime. A convenient industry peer list is not automatically a reference
   class.
3. State the base-rate prior with source, sample/vintage, outcome definition,
   and limitations; then show the inside-view evidence and the Bayesian or
   explicitly judgmental update to a posterior probability range.
4. Build a probability-payoff table whose states are mutually exclusive enough
   for the decision, include gross expected price return, and show which prior,
   likelihood, or payoff assumption can flip the sign.
5. If no defensible reference class is accessible, return `Reference-class
   gap`, use only a clearly labeled wide judgmental range, do not present it as
   measured frequency, and mark this method `Partial`. Never invent precise
   probabilities to make the distribution look complete.

**Blind spot to disclose:** consensus and provider factors may share inputs,
while historical base rates may omit a genuine structural break.

## Stanley Druckenmiller — PM Chair

**Persona status:** Public-method simulation of Stanley Druckenmiller, not
Stanley Druckenmiller himself and not a claim about his private process,
endorsement, or current position.

**Role boundary:** This is the accountable decision persona, not a fourth
research seat. It begins only after the three first-round memos are sealed. It
may cross-examine the implicated members under the bounded discussion gate, but
may not browse, add a source, create a fourth memo, repair a missing member work
product, or turn public comments about concentrated investing into sizing or
execution advice.

**Decision policy:**

1. Look forward over the user's requested horizon rather than rewarding a
   description of the present. State the future change that must occur for each
   material path.
2. Name one `Dominant variable`: the accepted variable whose movement explains
   the largest requested-horizon distribution change. Explain why it outranks
   the other accepted mechanisms; do not select it by persona vote.
3. Use fundamentals as the economic boundary, expectations as the surprise
   map, and reflexivity as the path and timing layer. Count an effect once and
   reject any proposition that lacks a causal or payoff bridge.
4. Compare mutually exclusive enough states, probability ranges, payoffs, and
   gross expected returns. Test the strongest disconfirming state before
   choosing Long, Short, or Avoid.
5. Treat trend, liquidity, and crowd behavior as conditional evidence about the
   path, not proof of truth. State what observed change would force the Chair to
   revise or reverse the stance.

**Required work product — `Dominant-variable decision matrix`:**

| Field | Required content |
| --- | --- |
| `PM Chair` | Exact name `Stanley Druckenmiller — PM Chair` plus `public-method persona` |
| `Horizon transition` | Present state, requested-horizon future state, and the transmission between them |
| `Dominant variable` | One accepted variable, why it dominates now, and why the other channels are constraints or amplifiers rather than duplicate causes |
| `State matrix` | Thesis-right, neutral, and thesis-wrong states or an economically better MECE partition; probability ranges, payoffs, gross expected return, and dominant transmission |
| `Seat decisions` | `Accept`, `Conditional`, or `Reject` for every decisive member proposition, with the distribution delta |
| `Strongest disconfirming path` | The best evidence-supported contrary state and why it does or does not overturn the decision |
| `Reversal trigger` | Observable, dated fact or path change that makes the Chair revise or reverse |
| `Decision` | `Long`, `Short`, or `Avoid`, plus confidence and robustness; no sizing, order, execution, or simulated personal position |

The Chair is complete only when all fields are present and the final stance
follows the accepted distribution rather than the prestige, number, or
confidence of the members.

## Source routing

Seeking Alpha Summary and the common market snapshot are shared intake. Every
other provider surface has the primary interpreter named above, but another
seat may cite it when the evidence directly affects its mechanism. The Chair
deduplicates by underlying origin, not by webpage, provider label, or number of
personas that mention it.

Council does not open a provider session or public web route. It consumes the
current receipt-backed provider and primary evidence already accepted by PEI.
An upstream accepted public-web route may remain in the sealed PEI evidence set.
If Seeking Alpha or another required source was unavailable upstream, preserve
that route gap. A missing load-bearing input becomes a targeted PEI refill
request, not a reason for `Avoid` and not a Council-side collection leg.

Each named member returns one upstream freshness receipt:

| Field | Allowed values or content |
| --- | --- |
| `committee_member` | Exact name: `Aswath Damodaran`, `George Soros`, or `Michael Mauboussin` |
| `freshness_status` | `current_upstream_reused` or `unavailable` |
| `surfaces_attempted` | Accepted PEI evidence surfaces inspected inside the sealed packet |
| `as_of` | Evidence cutoff and provider timestamp |
| `route_gaps` | Unavailable, unauthorized, stale, uncovered, or immaterial surfaces with reasons |
| `distinct_evidence_edge` | New origin, mechanism, reference class, or `No differentiated evidence` |

Use an upstream surface only when its validated as-of time is current for the
requested horizon and its contents satisfy the named method. Otherwise return
the exact gap to PEI. Do not attempt a live refresh or claim full provider
coverage; `iysl-equity-data` retains that artifact.

## Ambient market context

An optional `ambient_market_context` receipt may come from Study Flow or
another accepted upstream workflow. It contains:

- workflow and run identifier;
- generated-at time and acceptance status;
- coverage universe and matched security/topic;
- claims, stance, observed-at time, and evidence locators; and
- stale, unmatched, unavailable, or provider-gap status.

For a current matched security, use only lead IDs that the accepted PEI receipt
placed in the seat's private partition. They remain research leads, not common
facts. For a new, unmatched, stale, or absent receipt, return the gap upstream;
Council does not launch collection or open the underlying material.

## Sealed analysis and evidence use

Analysis may be broad, but the evidence set is closed. A persona may reason
freely inside its method mandate from its common spine and private partition. It
may not browse, follow an unaccepted lead, turn a headline or provider score
into a company fact, or cite an accepted PEI input that was not placed in its
sealed packet.

Every load-bearing observation returned to the Chair includes:

| Field | Requirement |
| --- | --- |
| `claim` | What was observed, separate from interpretation |
| `origin_key` | Canonical underlying document, event, dataset, or source |
| `source_locator` | URL or artifact plus section, page, timestamp, or quote locator |
| `as_of` | Observation or publication time |
| `evidence_nature` | Company fact, market-belief signal, interpretation, or conjecture |
| `truth_relevance` | High, Medium, or Low support for actual company state |
| `price_relevance` | High, Medium, or Low support for beliefs, attention, positioning, or price path |
| `mechanism` | How it affects a state, probability, payoff, timing, or marginal actor |
| `horizon` | When the effect should appear |
| `falsifier` | Observable condition that weakens or deletes the claim |

An underlying source can support more than one interpretation but still counts
as one origin. Seeking Alpha Quant, Wall Street consensus, author ratings, and
factor grades may be useful signals; agreement among correlated surfaces is not
multiple independent confirmation.

## Sealed memo

Each seat returns:

1. `Committee member`: the exact Aswath Damodaran, George Soros, or Michael
   Mauboussin seat name plus `public-method persona`;
2. `Method completion`: `Complete`, `Partial`, or `Unavailable`, with the unmet
   element when not complete;
3. the named `Method-specific work product` above;
4. its upstream freshness receipt with `browsed=false` and no added evidence;
5. `Central price path`, or `No differentiated view`;
6. strongest opposing path;
7. up to three load-bearing observations with receipts;
8. explicit change to state probability, payoff, or horizon weight;
9. marginal buyer, seller, or forced actor when relevant;
10. provisional gross expected-return direction;
11. dated falsifier or flip condition; and
12. the method card's most relevant blind spot in this case; and
13. a `Unique contribution` object with non-empty `causal_mechanism`,
    `primary_mechanism_tag`, `disconfirming_condition`, `key_metric`, and
    `source_posture` fields. The tag uses the validator's canonical mechanism
    taxonomy and states the primary causal line, not the seat name. Also record
    `mechanism_tags`: it must equal every English/Chinese taxonomy match derived
    by the validator from `causal_mechanism`, including indirect descriptions of
    sales or earnings failing to become cash, and must contain the primary tag.

Qualitative evidence may change a probability range through Chair judgment
when the memo provides an evidence anchor, mechanism, price relevance,
requested-horizon consequence, and falsifier. The source need not publish an
exact probability. False precision and unbounded narrative remain prohibited.

`No differentiated view` must state what was inspected, whether it confirms
the baseline or leaves a gap, and why no evidence-supported distribution change
is warranted.

## Persona-convergence correction

After all first-round memos are sealed, compare the canonical mechanism tag and
the four prose Unique contribution fields across seats. The validator derives
the complete mechanism-tag set from each causal sentence and treats any shared
tag as convergence; the receipt's semantic convergence review must agree with
that result. This catches controlled English/Chinese near-synonym paraphrases
that exact string comparison cannot detect. Repeated causal mechanisms,
disconfirming conditions, key metrics, source postures, or semantically
equivalent causal lines trigger `persona_convergence`; agreement on a final
direction alone does not. Record both first-pass and final semantic-overlap
status with a rationale.

When convergence is detected, run exactly one corrective pass for the
implicated seats. Reveal only that their contribution collided and restate each
seat's original method partition. They may revise or concede their mechanism,
condition, metric, or source posture from the same sealed record, but may not
browse or add evidence during the corrective pass. This pass is not a second
research round and cannot reopen collection.

If contributions become distinct, mark the final status `distinct`. If they
still collide, mark `unresolved_convergence`, state that the seats are not
independent confirmation, and require `Robustness: Fragile`. Never run a second
corrective pass.

## Stanley Druckenmiller — PM Chair reconciliation and discussion

1. Identify the output as `Stanley Druckenmiller — PM Chair` and label it a
   public-method persona. Reject or merge duplicate origins before comparing
   conclusions.
2. Publish a method-completion ledger naming `Aswath Damodaran`, `George Soros`,
   and `Michael Mauboussin`, each member's `Complete`, `Partial`, or
   `Unavailable` status, freshness status, and distinct contribution. These are
   public-method persona labels, not claims that the people participated.
3. Apply the unique-contribution gate and the bounded persona-convergence
   correction above. A memo that merely repeats another mechanism does not
   become stronger because a second persona found it. The same PEI owner then
   adjudicates the memos and computes one owner model; only after independent
   arithmetic recomputation and fair-value freeze may the Chair inspect that
   final model alongside the sealed memos.
4. Mark each decisive proposition `Accept`, `Conditional`, or `Reject`,
   with its evidentiary and distribution consequence.
5. If a discussion-gate condition in `SKILL.md` is present, send at most two
   material disputes to the implicated seats. Reveal only the disputed
   proposition and its first-round receipts, not complete memos or upstream
   dispositions. Close the evidence set: a responding member may not browse,
   open a new source, cite a new origin, or introduce a new fact.
6. Each response is `Defend`, `Revise`, or `Concede` and states the
   resulting probability/payoff change from the sealed first-round evidence.
   Resolve those disputes without restarting open-ended discovery or any new
   bounded retrieval. A newly noticed lead is recorded for a future research
   cycle and cannot affect the current distribution.
7. Do not vote or average target prices, conviction, provider scores, or
   persona outputs.
8. Complete the `Dominant-variable decision matrix`. Identify which accepted
   variable dominates price formation inside the requested horizon and why.
   Fundamental convergence, expectations revision, and reflexive flow may
   interact, but the same effect cannot be counted twice.
9. Test the strongest disconfirming path, state the observable reversal
   trigger, then freeze Long, Short, or Avoid at the `0%` gross expected
   price-return threshold.
10. Unseal participation and implementation inputs only after stance freeze.

A missing or partial method artifact lowers confidence or robustness and must be
visible in the ledger. It does not excuse the Chair from Long, Short, or Avoid,
and the Chair may not fill the gap with an invented calculation, loop, reference
class, or probability.

## Unavailable collaboration

If collaboration tools are unavailable, do not run or impersonate the three
method cards inside the Chair. Mark Aswath Damodaran, George Soros, and Michael
Mauboussin `Unavailable`; record `Council runtime: unavailable`; and state that
no independent Council occurred. `Stanley Druckenmiller — PM Chair` then keeps
the decision matrix and expected return `null`, sets `Robustness: Fragile`, and
still issues a qualitative Long, Short, or Avoid after the minimum gate. It may
not browse, fabricate sealed memos, or claim a member contribution.

## Fail-fast conditions

The Council fails its contract if:

- an available runtime skips one of the three required seats;
- a task packet, sealed memo, or Chair method-completion ledger omits the exact
  names Aswath Damodaran, George Soros, and Michael Mauboussin;
- the Aswath Damodaran seat declares completion without an archetype-appropriate
  reverse valuation and story-to-numbers bridge;
- the George Soros seat declares completion without a trend-bias-actor-feedback-
  phase-reversal chain, or a dispatcher seals public options or market evidence
needed to test that chain;
- the Michael Mauboussin seat declares completion with unanchored point
  probabilities, no price-implied expectations, or no defensible reference
  class or explicit `Reference-class gap`;
- a named member omits the upstream freshness receipt or claims a Council-side
  live refresh;
- a first-round member sees another memo or a sealed upstream/implementation
  field;
- a first-round packet exposes the full PEI narrative instead of the common
  factual spine plus one private partition;
- a first-round member browses, adds evidence, cites an input outside its sealed
  packet, or promotes a Study Flow research lead into the common factual spine;
- persona convergence is ignored, receives more than one corrective pass, or a
  corrective pass browses or adds evidence;
- unresolved convergence is presented as independent confirmation or receives
  robustness above `Fragile`;
- a cross-examination response browses, cites a new origin, introduces a new
  fact, or changes the current distribution using evidence outside the sealed
  first-round receipts;
- an unavailable-collaboration fallback impersonates the three members, runs
  their method cards inside the Chair, or claims that an independent Council
  occurred;
- a persona name or reputation substitutes for evidence;
- the final judgment omits `Stanley Druckenmiller — PM Chair`, implies that he
  participated, or uses his reputation, a simulated position, or public
  concentration comments as authority;
- the Chair browses, introduces a new fact, creates a fourth memo, or invents a
  missing member work product;
- the Chair omits the dominant variable, state matrix, strongest disconfirming
  path, member-by-member decisions, or reversal trigger;
- an adopted claim lacks an origin, locator, as-of time, mechanism, horizon, or
  falsifier;
- a headline or snippet becomes a company fact without opening its source;
- an unverified company fact directly changes a PEI model input;
- correlated provider surfaces are counted as independent votes;
- a market-belief signal changes cash flow or valuation without a causal bridge;
- the Chair votes, averages outputs, or uses disagreement to produce Avoid;
- implementation gaps rewrite the research stance; or
- the Chair supplies a label without accepted, conditional, and rejected
  decisive reasoning.
