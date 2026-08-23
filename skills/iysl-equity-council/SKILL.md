---
name: iysl-equity-council
description: Run three named equity method personas and a Stanley Druckenmiller PM Chair for Long, Short, or Avoid after a usable PEI pack.
compatibility: Requires Python 3 for the Council admission, information-partition, and judgment receipt validator.
---

# Equity Council

## Outcome

Own the final requested-horizon research judgment without rebuilding Public
Equity Investing research, models, or valuation. After the minimum gate passes,
run one three-seat Council whenever agent collaboration is available, then issue
exactly one `Long`, `Short`, or `Avoid` stance from the sign of gross expected
price return. Never fake an independent Council when that runtime is
unavailable. Treat fundamental value as one anchor while also testing
expectations, sentiment, positioning, and reflexive price paths.

The three seats are explicitly named `Aswath Damodaran — Fundamental Committee
Member`, `George Soros — Reflexivity Committee Member`, and `Michael Mauboussin
— Expectations Committee Member`. `Stanley Druckenmiller — PM Chair` is the
decision persona that reconciles their sealed work; it is not a fourth research
seat. These are public-method personas, not the actual people, private-process
claims, endorsements, simulated current positions, or evidentiary authority.
All three members and the Chair are evidence-closed for the run: they may use
only the accepted PEI baseline, common factual spine, and their sealed private
partition. They may not browse, add evidence, or repair an upstream gap inside
Council. The Chair remains accountable for every adopted claim and the final
distribution.

This skill is advisory only. It does not infer authorization, size a position,
place an order, or execute a trade.

## Activation boundary

Use this skill when explicitly invoked, or only when both conditions hold:

- a Public Equity Investing workflow has a minimally usable research pack; and
- the user requests a final directional investment judgment.

When both conditions hold, this is the mandatory decision gate for a requested
final `Long`, `Short`, or `Avoid` research judgment. It is not mandatory for
pure data collection, model construction, monitoring, or implementation-only
work.

Do not activate for raw company facts, first-pass evidence gathering, model or
valuation construction, earnings summary, scenario-only analysis, standalone
sizing or hedging, private-company work, or generic company research. Leave
those tasks with their existing owners.

## Public Equity Investing boundary

Prefer the installed `@Public Equity Investing` router and preserve its
single-lead-owner contract. Reuse an existing plugin artifact when available;
otherwise have the router select the narrowest lead skill and only the support
skills that lead assigns. Never fan out across every constituent skill.

Do not invoke `iysl-equity-data` directly from this skill. It remains the owner of
formal provider coverage, source resolution, and evidence handoff accepted by
the Public Equity Investing lead. Council members may identify an exact missing
input, but may not browse, create a competing coverage artifact, or repair the
gap. Return a targeted refill request to Public Equity Investing and start a new
Council run only after the updated PEI receipt is independently accepted.

The plugin lead retains ownership of the hero artifact. This skill returns the
canonical judgment block for that artifact; it does not take over HTML, DOCX,
XLSX, memo, model, scenario, evidence-inventory, or risk work.

## Minimum gate

Require all four inputs before issuing an investment stance:

1. valid security identity;
2. current price with as-of timestamp;
3. explicit decision horizon; and
4. at least one minimally usable Public Equity Investing research, valuation,
   or scenario handoff.

For a decision-ready run, also require a fingerprinted
`support/pei_input_receipt.json` validated against the installed PEI routing map
and routed lead skill. Any hard research gap blocks Council admission. A
`LIMITED` receipt may proceed with reduced confidence or robustness. A PEI
`BLOCKED` posture may proceed only when every hard gap is `portfolio` or
`implementation`; an implementation-only blocker does not block research
admission and remains sealed until participation and readiness assessment.

Before the gate, state the exact missing upstream inputs and stop the investment
judgment. This is an intake failure, not `Avoid`. After the gate, uncertainty
may lower confidence or robustness but may not create a fourth verdict.

Read [references/judgment-contract.md](references/judgment-contract.md) after
the gate passes.

## Workflow

1. Record the Public Equity Investing lead, accepted artifacts, as-of dates,
   decision relevance, source posture, and unresolved gaps in the internal
   upstream receipt. Validate Council research admission. Seal upstream
   verdicts, the full PEI narrative, participation, readiness, and execution
   inputs from Council members.
2. Prepare one common factual spine containing only security identity, price,
   horizon, evidence cutoff, and accepted factual fields needed by every seat.
   Encode each field as an allowlisted structured fact with a scalar value,
   unit, as-of time, and accepted evidence IDs; identity facts must bind to the
   accepted security or price identity (including currency). Arbitrary prose,
   nested values, model conclusions, and extra partition payload fields are
   forbidden.
   Build three non-overlapping private evidence partitions from the accepted
   PEI inputs: Damodaran receives fundamentals/reverse-valuation/capital-
   structure inputs; Soros receives price-path/marginal-actor/positioning-
   reflexivity inputs; Mauboussin receives expectations/revisions/reference-
   class/probability-payoff inputs. An accepted `ambient_market_context`
   receipt remains a discovery accelerator, not automatic proof.
3. Read [references/council-protocol.md](references/council-protocol.md) and,
   when agent collaboration is available, run its three isolated persona
   agents. Put the exact committee-member name, method card, method-specific
   work product, freshness receipt, common header, and evidence-closed authority
   to inspect only that sealed packet in each task packet. Do not let a dispatcher replace the
   named deliverable with a generic bull, bear, valuation, or risk memo, or hide
   a method card's permitted public market evidence. When collaboration is
   unavailable, use the protocol's explicit unavailable fallback; do not run
   the three research methods inside the Chair.
4. After first-round memos arrive, deduplicate common source origins. If a seat
   identifies a model- or sign-changing gap, stop the current Council admission
   and return at most two exact inputs in one targeted Public Equity Investing
   refill request. Do not browse or patch the live Council record. A refill, if
   completed, creates a new accepted PEI baseline and a new Council run; do not
   start a second refill loop.
5. Apply the method-completion and unique-contribution gates. Each seat must
   state a distinct causal mechanism, disconfirming condition, key metric, and
   source posture, plus one canonical `primary_mechanism_tag`. Perform an
   explicit semantic convergence review. Record every validator-derived
   `mechanism_tags` match from the causal text; the declared tags must equal the
   controlled English/Chinese semantic taxonomy, including indirect
   cash-conversion phrasing, and any overlap across seats triggers convergence.
   This prevents near-synonym paraphrases from
   masquerading as independent causal lines. If the first pass has
   `persona_convergence`, run exactly one
   bounded corrective pass over the same sealed inputs; no browsing or new
   evidence is allowed. If convergence remains, label it unresolved and cap
   robustness at `Fragile` rather than claiming independent confirmation. A
   member that does not deliver its named
   method artifact is `Partial` or `Unavailable`, even if its prose is
   plausible. Missing method completion lowers confidence or robustness; it
   does not create a fourth stance or permit the Chair to invent the missing
   analysis.
6. Build a dispute ledger. Open one bounded cross-examination for at most two
   disagreements that can change stance, horizon weight, or a material
   probability/payoff. Do not manufacture debate when no such disagreement
   exists.
7. Run the `Stanley Druckenmiller — PM Chair` decision contract. Give the Chair
   the full accepted PEI baseline only after first-round sealing, method
   completion, and unique-contribution checks. From that baseline and the
   sealed memos only, the Chair accepts, conditions, or rejects
   decisive propositions, identifies the one dominant variable and its
   price-formation mechanism for the requested horizon, constructs the required
   decision matrix, tests the strongest opposing path, states the reversal
   trigger, and freezes one research stance at the `0%` gross expected
   price-return threshold.
8. After the research stance freezes, use Public Equity Investing risk
   capabilities when participation or implementation evidence is needed.
   Borrow, options, liquidity, cost, carry, and execution may change
   participation or readiness; they may not rewrite the research stance.
9. Return the canonical judgment block to the lead artifact owner. Route
   monitoring, tracking, or memo work back to the appropriate plugin owner.
   Save the internal run as `support/council_run.json` from
   `templates/council-run.json` and validate it with
   `scripts/validate_council_run.py` before calling the Council complete.

## Council discussion gate

The three-seat first round is mandatory after every minimum-gate pass when agent
collaboration is available. Cross-examination is conditional on at least one
material dispute:

- a reasonable input range can flip gross expected-return sign;
- requested-horizon price dynamics conflict with long-duration valuation;
- a belief, positioning, or liquidity feedback loop materially changes the
  path or timing of convergence;
- optionality or an unconfirmed operating state supplies material value; or
- accepted evidence conflicts on direction, source interpretation, or horizon
  weight.

Complexity, importance, or ordinary uncertainty alone does not require a
second round.

## Invariants

- Positive gross expected price return is `Long`, negative is `Short`, and
  `Avoid` requires a genuinely balanced distribution at its stated precision
  with no supported directional asymmetry. Avoid is never a data-gap or
  disagreement label.
- A Long-only upside target, mandate return, transaction-cost hurdle, or
  implementation requirement may not become the research-direction threshold.
- `Stanley Druckenmiller — PM Chair` is always named in the canonical judgment.
  The label means a public-method decision persona, not participation by,
  endorsement from, private access to, or a current trade by Stanley
  Druckenmiller.
- The Chair is not a fourth agent, does not browse or create a fourth research
  memo, and may not invent missing member work. It never votes, averages
  targets, averages conviction, or chooses `Avoid` because members disagree.
- Public discussion of concentrated investing never authorizes the Chair to
  infer sizing, concentration, orders, execution, or a simulated personal
  position.
- Every minimum-gate pass with agent collaboration uses exactly the three named
  seats: Aswath Damodaran, George Soros, and Michael Mauboussin. Their names and
  public methods affect question generation, required work products, and
  interpretation, never source quality or evidentiary weight. Without that
  runtime, record the Council as unavailable rather than emulating the seats.
- Members may reason broadly within their mandate but may not search. Adopted
  claims must resolve to their sealed packet and pass the provenance,
  truth-relevance, price-relevance, mechanism, horizon, payoff, and falsifier
  controls in the references.
- Members may not see another member memo, upstream disposition,
  the full PEI narrative, participation, readiness, borrow suitability, cost,
  sizing, or execution fields before the first round closes, and may not
  delegate again. Public
  options, volume, price, short-interest, positioning, and liquidity evidence
  already accepted by PEI remains available when placed in the relevant sealed
  method partition; do not misclassify it as sealed implementation advice.
- Seeking Alpha ratings, Quant, Wall Street consensus, author opinion, and
  repeated coverage from one underlying origin are correlated signals, not
  independent votes.
- Missing implementation evidence cannot erase a supported direction.
- For a bounded batch, run one three-seat Council on the common batch header
  rather than spawning a separate Council for every candidate.
- Keep internal receipts and orchestration terms out of investor-facing output
  unless the user asks for them.
