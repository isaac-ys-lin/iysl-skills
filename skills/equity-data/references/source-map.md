# Public Equity Investing Source Map

Optional source-selection notes. Read only when selecting sources for
standalone collection or resolving provider, provenance, or conflict details
not supplied by the embedded plugin route.

## Source Hierarchy

Use the source closest to the claim:

1. Filed, audited, executed, regulator-published, or exchange-published material.
2. Issuer releases, presentations, transcripts, and IR material.
3. Timestamped market-data and estimate providers.
4. Authorized internal research, models, and portfolio context.
5. News, forums, and social sources as leads or sentiment context.

For non-US, dual-listed, or ADR issuers, prefer the home regulator, home exchange, and issuer filing. A provider configuration is not proof of live access; verify the scoped route before relying on it.

Search results, snippets, cached previews, and AI summaries are discovery aids, not evidence for material financial, transaction, guidance, consensus, or target-price claims. Open the underlying source and record its direct locator before marking a claim verified.

## Provider And Public-Web Route

Use this order unless the owning workflow specifies a stronger route:

1. Retrieve the claim from the regulator, exchange, executed agreement, or issuer IR when it exists.
2. Use one timestamped provider snapshot for market data, consensus, ratings, targets, or standardized comparables. Prefer a callable licensed route; otherwise use an account route, export, screenshot, or excerpt.
3. Search the public web to discover missing primary documents and corroborating sources. Query the issuer/ticker plus the exact document, metric, period, and site or regulator; open the result before using it.
4. If only a weaker public aggregator is available, label it separately and preserve its provider, upstream data source when disclosed, as-of date, analyst count, definition, and limits.
5. Log unavailable, unauthorized, stale, and empty routes. Do not silently replace a failed premium route with public data under the same source ID.

## Default Evidence Stack And Sufficiency

Do not require multiple paid providers when one authorized provider plus primary
sources already supports the decision. For most issuer-specific workflows, use
the smallest stack that covers the required claim types:

1. **Primary verification layer.** Use regulator, exchange, issuer filings, IR,
   releases, presentations, and executed documents for reported actuals,
   guidance, capital structure, financing terms, dilution, transactions, and
   other load-bearing company facts.
2. **Provider layer.** Use one timestamped market-data and estimates provider
   for consensus, revisions, ratings, targets, standardized financials,
   comparables, positioning, and screening. When authorized Seeking Alpha
   Premium access is available and coverage is adequate, it may serve as the
   default paid provider for this layer; do not require an additional paid
   provider merely for redundancy.
3. **Derived/model layer.** Build transparent calculations from cited inputs and
   leave scenario assumptions, probability weights, fair value, and investor
   judgment to the owning Public Equity Investing workflow. Provider consensus
   is a calibration input, not a substitute for independent underwriting.
4. **Targeted escalation layer.** Add another provider, export, specialist data
   source, or user-supplied artifact only when a decision-critical gap remains
   or the added source materially improves definition, granularity, freshness,
   coverage, auditability, or workflow efficiency.

Treat the evidence pack as source-sufficient when every decision-critical input
is either:

- verified against an authoritative primary source;
- supported by a timestamped provider snapshot with its material definition and
  basis preserved;
- mechanically derived from cited inputs with the calculation visible to the
  owning workflow; or
- explicitly labeled as an unresolved gap, including the evidence that would
  close it.

Do not add a second provider solely to create apparent confirmation when the
providers may share upstream data or methodology. Add it when the difference is
itself decision-relevant, such as a different analyst universe, estimate
vintage, fiscal basis, listing, methodology, or forecast horizon.

### Claim-To-Source Defaults

| Claim or input | Default source | Escalate when |
|---|---|---|
| Reported financials, guidance, segment disclosure, capex, financing, dilution, share count | Filing, regulator/exchange, issuer IR | Definitions conflict, the disclosure is incomplete, or a model-ready normalization is required |
| Price, volume, market cap, short interest, other trading context | Exchange or timestamped authorized provider | The decisive input needs a different venue, currency, timezone, or higher-frequency basis |
| Revenue/EPS estimates, revisions, analyst ratings, target prices | One timestamped estimates provider; Seeking Alpha may be the default paid layer when authorized | Analyst-level, segment-level, longer-horizon, local-market, or methodology-specific detail is decision-critical |
| Management commentary | Opened full transcript or issuer event material | Attribution, wording, or event provenance remains uncertain; use formal issuer disclosure for reported figures and guidance |
| Comparable-company metrics | Timestamped provider snapshot plus validated peer set | Business-model comparability, metric definition, or fiscal alignment is weak |
| Scenario assumptions, probabilities, fair value, implied expectations | Owning workflow model using cited evidence | Never outsource the investor judgment merely because a provider publishes a target price or rating |
| Broker research, expert calls, proprietary channel checks | Authorized research source or user-supplied artifact | Use only when the workflow truly needs information not available from public or standard provider evidence |

### Data Completion Inside The Existing Workflow

This is a coverage aid, not a new workflow stage or a mandatory metric
checklist. At the existing first workflow step, select only the field groups
needed for the owning decision. Fill those groups through the existing bounded
Ask SA scan, targeted Seeking Alpha retrieval, primary-source verification, and
smallest-sufficient handoff.

| Field group | Ask SA discovery | Targeted provider retrieval | Primary verification or supplement |
|---|---|---|---|
| Issuer actuals and guidance | Identify the periods, segments, KPIs, guidance changes, and accounting issues that matter | Standardized income statement, balance sheet, cash flow, actual/estimate surprise, and historical trends | Filing/XBRL, earnings release, presentation, regulator or exchange disclosure for reported values, guidance, segment/KPI definitions, capex, cash, debt, and non-GAAP reconciliation |
| Capital structure and dilution | Surface financing, convertible, equity issuance, buyback, SBC, M&A, or balance-sheet developments | Shares outstanding, market cap, ownership or short-interest context when exposed | Period-end and weighted-average basic/diluted shares, options/RSUs, convertibles, warrants, ATM programs, private placements, buybacks, financing terms, and a mechanical fully diluted share bridge |
| Market and positioning context | Identify unusual price action, sentiment shifts, event setup, or crowded debates | Timestamped price and volume, 52-week range, short interest, beta, relevant RSI, price-versus-SMA, options/implied-move, and momentum fields | Exchange or venue data when price, listing, currency, close time, or event-window precision is decisive |
| Consensus and revisions | Identify material estimate divergence, recent upgrades/downgrades, target changes, and the expectation bar | Annual or quarterly revenue/EPS estimates, low/high where exposed, analyst count, revisions, surprise history, Wall Street rating, and target-price fields | Issuer guidance and reported actuals for calibration; preserve provider basis, fiscal period, currency, GAAP/normalized basis, horizon, and methodology limits |
| Valuation and peer context | Identify the valuation debate, rerating assumptions, and disputed peer choices | Forward and trailing multiples, including decision-relevant P/E, PEG, EV/revenue, EV/EBITDA, FCF yield, sector medians, growth/profitability metrics, and provider peer sets | Recompute decisive multiples from cited inputs and validate peer business models, fiscal alignment, capital intensity, and accounting definitions |
| Management commentary and catalysts | Surface the latest earnings-call insights, guidance drivers, investor-day claims, catalysts, and falsifiers as source leads | Opened transcript, event index, recent company news, press-release, filing, and article leads | Prefer formal issuer disclosure for reported figures and guidance; preserve speaker, event, publication date, event date, and direct source locator for attributed commentary |
| External debate and source leads | Request the strongest bull and bear arguments, recent articles, news, press releases, filing leads, and meaningful rating disagreement | SA Author research and other authorized interpretation, kept separate from Quant and Wall Street signals | Verify every load-bearing factual premise at the underlying filing, issuer document, regulator, exchange, or executed counterparty source |

Use the existing handoff fields rather than creating a parallel data schema.
Create one `claim_or_field` entry per material claim or compatible metric bundle.
Bundle fields only when they share the same source, vintage, fiscal basis,
definition, and verification status; otherwise keep them separate. Use the
existing `verification_status` to distinguish primary-verified facts,
timestamped provider snapshots, mechanical calculations from cited inputs, and
unresolved gaps. The owning workflow receives only the selected fields that can
change its conclusion, valuation inputs, catalyst path, or readiness assessment.

### Escalation Triggers For Additional Data Sources

Use an additional source only for a concrete gap. Common triggers include:

- analyst-by-analyst, segment, product, KPI, or multi-year estimate detail not
  exposed by the default provider;
- large-universe screening, standardized export, API access, or repeatable
  model-update workflows that make manual collection unreliable or inefficient;
- source-linked historical KPI schedules or formula-preserving model updates;
- local-market consensus, ownership, or security-specific data that the default
  provider does not cover adequately;
- original broker research, expert-call content, or other authorized
  institutional research needed to test a material variant view.

Route to the source category that closes the gap rather than prescribing a
subscription by default. General market/estimate platforms, source-linked model
data providers, and institutional research platforms are optional gap-fillers,
not prerequisites for a complete Public Equity Investing workflow.

For Taiwan-listed issuers, use MOPS, TWSE or TPEx, and issuer IR as the primary
sources for reported financials, monthly revenue, material information, capital
actions, and offering or convertible-bond terms. Use Seeking Alpha or another
provider only where its coverage adds useful consensus, valuation, market, or
cross-market context; do not force US-centric provider coverage where the home
market source is stronger.

### Seeking Alpha

Treat Seeking Alpha as a timestamped provider or aggregator, not a primary
issuer source. Record the upstream provider when disclosed; do not hard-code or
assume it. Standardized financials, estimates, ratings, and peer data may
differ from issuer-reported or other provider definitions, so preserve the
provider basis and reconcile load-bearing values when necessary.

Use account-only fields through an authorized account route, including Ask SA,
and retain the returned evidence artifact. Record `provider=Seeking Alpha`,
`upstream_provider` when disclosed, `access_mode=account_route`, and the
relevant page, field, and as-of date.

When the account route is available in the in-app browser, attempt it before
classifying Seeking Alpha Chat as unavailable. A `403` from direct HTTP,
programmatic retrieval, or a crawler is a failed retrieval leg, not evidence
that the browser account route or Chat failed. Record the direct-fetch status
separately (for example, `direct_http_403`) and do not bypass the restriction.

The delivery surface does not change the claim type. For example, a user-supplied screenshot of Wall Street revenue estimates is still `estimate_consensus`, not a user assumption; a screenshot of a Quant Rating is still `provider_proprietary_score`, not analyst consensus.

| Seeking Alpha area | Useful evidence | Evidence nature | Required treatment |
|---|---|---|---|
| Ask SA | Bounded search and synthesis of recent coverage, signals, and source leads | `provider_synthesis` | Use for recall and prioritization; verify load-bearing claims at the underlying source |
| Summary / market data | Price, volume, market cap, 52-week range, short interest, beta | `fact_provider_standardized` | Timestamp and timezone; prefer exchange data for decisive market inputs |
| Ratings | SA author, Wall Street, and Quant ratings | `analyst_interpretation`, `estimate_consensus`, `provider_proprietary_score` | Keep all three separate; retain lookback and analyst count |
| Financials | Standardized income statement, balance sheet, cash flow | `fact_provider_standardized` | Reconcile material values to filing/XBRL; preserve reclassification differences |
| Earnings | Actual/estimate surprise, annual and quarterly estimates, revisions, analyst counts | actuals as standardized facts; estimates as `estimate_consensus` | Retain GAAP/normalized basis, period, low/high, and provider as-of |
| Valuation / Growth / Profitability | Multiples, forward growth, margins, returns, sector medians | `derived_provider_metric` | Retain formulas/definitions where available; recompute decisive multiples from cited inputs |
| Momentum / Options | Returns, technicals, IV, volume, open interest, implied move | `market_positioning_context` | Treat as high-frequency context with strict cutoff; never as fundamental proof |
| Peers | Provider peer set and relative metrics | `provider_comparison` | Validate the peer universe and business-model comparability before downstream use |
| Articles / transcript or filing indexes | Research interpretation and document leads | `analyst_interpretation` or discovery | Do not reproduce article bodies or index summaries; follow links to the primary document. An opened full transcript may support attributed management commentary; prefer issuer disclosures for reported figures and guidance |

Seeking Alpha can materially strengthen consensus coherence, estimate
revisions, valuation cross-checks, and positioning context, but it cannot by
itself resolve undisclosed financing, dilution, purchase accounting, synergy,
capex, tax, or technical-execution gaps. Preserve those as unresolved gaps
until an authoritative primary source addresses them; the owning workflow
determines their effect on underwriting and participation readiness.

### Consensus And Target Integrity

- Keep each provider snapshot as a separate vintage. Never blend revenue from one provider, EBITDA from another, and targets from a third into a purported single consensus package.
- Record provider, upstream provider when disclosed, security/listing, currency, fiscal basis, as-of and retrieval times, analyst population, statistic, lookback, forecast horizon, low/high, and GAAP/normalized basis.
- Keep author ratings, Wall Street ratings, proprietary quant scores, and price targets in separate rows.
- Mark methodology as `method_unknown` when the provider does not expose it. Do not infer mean, median, or a 12-month horizon.
- When two providers disagree, preserve both and explain the likely universe/date/definition difference. Do not average them.

### Public-Web Search Protocol

- Search primary domains first: regulator/EDGAR, issuer IR, exchange, government procurement, and executed counterparties.
- Use news and aggregators to discover events, dates, broker actions, and missing documents; verify material claims at the closest available source.
- Open and cite the actual page or document. A search snippet, cached result, or generative summary cannot satisfy a required source.
- Record publication time, data as-of time, retrieval time, and timezone separately when material.
- If a primary source is not yet public, state what filing or disclosure would close the gap and continue with a clearly labeled proxy only when the owner permits it.

## Conflict And Inference

- Preserve conflicting values with their dates and definitions; do not average them away.
- Prefer mechanical `derived calculation` from cited inputs over an opaque estimate.
- Mark judgment-based proxies as inferred assumptions and show what direct source would replace them.
- Never infer proprietary consensus, broker-only implementation data, private portfolio context, or restricted article bodies from public metadata.
